import importlib
import json
import os
import threading
from collections import defaultdict
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union

import yaml
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

from script_to_speech.utils.env_utils import load_environment_variables

from ..voice_library.voice_library import VoiceLibrary
from .base.exceptions import TTSError, VoiceNotFoundError
from .base.stateful_tts_provider import StatefulTTSProviderBase
from .base.stateless_tts_provider import StatelessTTSProviderBase


class TTSProviderManager:
    """Manages TTS providers and handles audio generation delegation."""

    def __init__(
        self,
        config_data: Dict[str, Any],
        overall_provider: Optional[str] = None,
        dummy_tts_provider_override: bool = False,
    ):
        """
        Initialize the TTS Manager.

        Args:
            config_data: Dictionary containing TTS provider configuration
            overall_provider: Optional provider to use when provider isn't specified in config
            dummy_tts_provider_override: If True, override all TTS providers with dummy TTS providers
        """
        # Load environment variables from .env file if it exists
        # Ensures API keys for TTS providers are available before any provider is initialized
        load_environment_variables()

        self._config_data = config_data
        self._overall_provider = overall_provider
        self._dummy_tts_provider_override = dummy_tts_provider_override
        self._provider_refs: Dict[
            str, Type[Union[StatelessTTSProviderBase, StatefulTTSProviderBase]]
        ] = {}
        self._speaker_providers: Dict[str, str] = {}
        self._speaker_configs_map: Dict[str, Dict[str, Any]] = {}
        self._provider_clients: Dict[str, Any] = {}
        self._voice_library = VoiceLibrary()
        self._is_initialized = False

        # Dictionaries for thread-safe lazy loading
        self._stateful_instances: Dict[str, StatefulTTSProviderBase] = {}
        self._client_locks: Dict[str, threading.Lock] = defaultdict(threading.Lock)
        self._instance_locks: Dict[str, threading.Lock] = defaultdict(threading.Lock)

    def _ensure_initialized(self) -> None:
        """Ensure config is loaded and providers are initialized."""
        if not self._is_initialized:
            self._load_config(self._config_data)
            self._is_initialized = True

    @classmethod
    def _get_provider_class(
        cls, provider_name: str
    ) -> Type[Union[StatelessTTSProviderBase, StatefulTTSProviderBase]]:
        """
        Dynamically import and return the provider class based on provider name.

        Args:
            provider_name: Name of the provider to load

        Returns:
            TTSProvider class

        Raises:
            ValueError: If provider cannot be found or loaded
        """
        try:
            # Import the provider module based on directory name
            module = importlib.import_module(
                f"script_to_speech.tts_providers.{provider_name}.tts_provider"
            )

            # Get the provider class
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(
                        attr, (StatelessTTSProviderBase, StatefulTTSProviderBase)
                    )
                    and attr not in (StatelessTTSProviderBase, StatefulTTSProviderBase)
                    and attr.get_provider_identifier() == provider_name
                ):
                    return attr

            raise ValueError(
                f"No valid provider class found in {provider_name} "
                f"(ensure the class implements TTSProvider and "
                f"get_provider_identifier() returns '{provider_name}')"
            )

        except ImportError as e:
            raise ValueError(
                f"Provider '{provider_name}' not found: {e}\n"
                f"Ensure the provider directory exists and contains tts_provider.py"
            )

    def _load_config(self, config_data: Dict[str, Any]) -> None:
        """
        Load and validate provider configuration from a dictionary.

        Args:
            config_data: Dictionary containing TTS provider configuration

        Raises:
            ValueError: If configuration is invalid or providers cannot be initialized
        """
        if not isinstance(config_data, dict):
            raise ValueError(
                "Invalid configuration data: root must be a mapping (dictionary)"
            )

        config = config_data  # Use the provided dictionary directly

        # Store speaker configs and determine required providers
        required_providers = set()
        self._speaker_configs_map.clear()
        self._speaker_providers.clear()

        if not config:  # Check if the provided dictionary is empty
            raise ValueError("Voice configuration data is empty.")

        for speaker, speaker_config in config.items():
            if not isinstance(speaker_config, dict):
                raise ValueError(
                    f"Configuration for speaker '{speaker}' must be a mapping (dictionary), not {type(speaker_config)}"
                )

            # Get provider from config or use overall provider
            provider_name = speaker_config.get("provider")
            if not provider_name and self._overall_provider is not None:
                provider_name = self._overall_provider
                # Add overall provider to speaker config if missing
                speaker_config["provider"] = provider_name
            elif not provider_name:
                raise ValueError(
                    f"No provider specified for speaker '{speaker}' and no overall provider set"
                )

            # Check for sts_id and expand config if present
            if "sts_id" in speaker_config:
                sts_id = speaker_config.pop("sts_id")  # Remove sts_id from config

                # Get expansion from voice library
                expanded_config = self._voice_library.expand_config(
                    provider_name, sts_id
                )

                # Merge: expanded config first, then user overrides
                final_config = {**expanded_config, **speaker_config}
                speaker_config.clear()
                speaker_config.update(final_config)

            # Validate speaker config using the provider's static method
            try:
                provider_class = self._get_provider_class(provider_name)
                provider_class.validate_speaker_config(speaker_config)
            except (ValueError, TypeError) as e:
                raise ValueError(
                    f"Invalid configuration for speaker '{speaker}' using provider '{provider_name}': {e}"
                )

            # If dummy TTS provider override is enabled, prepare to swap providers
            original_provider_name = provider_name
            if self._dummy_tts_provider_override:
                # Determine if the original provider is stateful or stateless
                provider_class = self._get_provider_class(original_provider_name)
                if issubclass(provider_class, StatefulTTSProviderBase):
                    provider_name = "dummy_stateful"
                else:
                    provider_name = "dummy_stateless"

                # Add dummy_id if it doesn't exist
                self._add_dummy_id_to_config(speaker, speaker_config, provider_class)

                # Update the provider in the speaker config
                speaker_config["provider"] = provider_name

                # Re-validate with the new dummy TTS provider
                dummy_provider_class = self._get_provider_class(provider_name)
                dummy_provider_class.validate_speaker_config(speaker_config)

            # Store validated config and provider mapping
            self._speaker_configs_map[speaker] = speaker_config
            self._speaker_providers[speaker] = provider_name
            required_providers.add(provider_name)

        # Store provider classes for lazy instantiation
        for provider_name in required_providers:
            provider_class = self._get_provider_class(provider_name)
            self._provider_refs[provider_name] = provider_class

    def _add_dummy_id_to_config(
        self,
        speaker: str,
        speaker_config: Dict[str, Any],
        original_provider_class: Type,
    ) -> None:
        """
        Add a dummy_id to the speaker config if it doesn't exist.

        Uses the first required field from the original provider as the dummy_id value.

        Args:
            speaker_config: The speaker configuration to modify
            original_provider_class: The original provider class
        """
        # Skip if dummy_id already exists
        if "dummy_id" in speaker_config:
            return

        # Get the required fields from the original provider
        required_fields = original_provider_class.get_required_fields()

        # Find the first required field that's not 'provider'
        dummy_id_value = None
        for field in required_fields:
            if field != "provider" and field in speaker_config:
                dummy_id_value = speaker_config[field]
                break

        # If we didn't get a value from required fields, fall back to the speaker name
        if not dummy_id_value:
            dummy_id_value = speaker

        # If we found a value, add it as dummy_id
        if dummy_id_value is not None:
            speaker_config["dummy_id"] = str(dummy_id_value)

    def get_provider_for_speaker(self, speaker: str) -> str:
        """
        Get the provider name for a given speaker.

        Args:
            speaker: The speaker to look up

        Returns:
            str: Name of the provider handling this speaker

        Raises:
            ValueError: If no provider is assigned to the speaker
        """
        self._ensure_initialized()

        if not speaker:
            speaker = "default"

        if speaker not in self._speaker_providers:
            raise ValueError(f"No provider assigned for speaker '{speaker}'")

        return self._speaker_providers[speaker]

    @classmethod
    def get_available_providers(cls) -> List[str]:
        """Get list of available provider names."""
        providers = []
        provider_dir = Path(__file__).parent

        for item in provider_dir.iterdir():
            if item.is_dir() and item.name not in [
                "base",
                "__pycache__",
                "dummy_common",
            ]:
                try:
                    # Try to load the provider to verify it's valid
                    cls._get_provider_class(item.name)
                    providers.append(item.name)
                except ValueError:
                    continue

        return providers

    ####
    # TTS Provider pass-through methods
    ###

    def generate_audio(self, speaker: Optional[str], text: str) -> bytes:
        """
        Generate audio using the appropriate provider.
        None or empty speaker values are treated as requests for the 'default' speaker.

        Args:
            speaker: The speaker to use, or None/empty for default speaker
            text: The text to convert to speech

        Returns:
            bytes: The generated audio data

        Raises:
            ValueError: If no provider is found for the speaker
        """
        self._ensure_initialized()

        if not speaker:
            speaker = "default"

        provider_name = self.get_provider_for_speaker(speaker)
        provider_class = self._provider_refs[provider_name]
        speaker_config = self._speaker_configs_map[speaker]

        # Lazy instantiation of client with thread safety
        client = self._provider_clients.get(provider_name)
        if not client:
            with self._client_locks[provider_name]:
                # Double-check after acquiring lock
                client = self._provider_clients.get(provider_name)
                if not client:
                    client = provider_class.instantiate_client()
                    self._provider_clients[provider_name] = client

        # Handling based on provider type (stateful vs stateless)
        if issubclass(provider_class, StatefulTTSProviderBase):
            # Lazy instantiation of stateful provider with thread safety
            instance = self._stateful_instances.get(provider_name)
            if not instance:
                with self._instance_locks[provider_name]:
                    # Double-check after acquiring lock
                    instance = self._stateful_instances.get(provider_name)
                    if not instance:
                        instance = provider_class()
                        self._stateful_instances[provider_name] = instance

            # Use the instance to generate audio
            return instance.generate_audio(client, speaker_config, text)
        else:
            # For stateless providers, call the class method directly
            return provider_class.generate_audio(client, speaker_config, text)

    def get_speaker_identifier(self, speaker: Optional[str]) -> str:
        """
        Get speaker identifier from appropriate provider.
        None or empty speaker values are treated as requests for the 'default' speaker.

        Args:
            speaker: The speaker to get identifier for, or None/empty for default speaker

        Returns:
            str: Speaker identifier from the appropriate provider
        """
        self._ensure_initialized()

        if not speaker:
            speaker = "default"

        provider_name = self.get_provider_for_speaker(speaker)
        provider_class = self._provider_refs[provider_name]
        speaker_config = self._speaker_configs_map[speaker]

        return provider_class.get_speaker_identifier(speaker_config)

    def get_provider_identifier(self, speaker: Optional[str]) -> str:
        """
        Get provider identifier for the provider handling this speaker.
        None or empty speaker values are treated as requests for the 'default' speaker.

        Args:
            speaker: The speaker to look up provider for, or None/empty for default speaker

        Returns:
            str: Provider identifier from the appropriate provider
        """
        self._ensure_initialized()

        if not speaker:
            speaker = "default"

        provider_name = self.get_provider_for_speaker(speaker)
        provider_class = self._provider_refs[provider_name]

        return provider_class.get_provider_identifier()

    def get_max_provider_download_threads(self, provider_name: str) -> int:
        """
        Get the max number of concurrent download threads for a provider.

        Args:
            provider_name: The name of the provider to get concurrency limit for

        Returns:
            int: The recommended number of concurrent threads for this provider

        Raises:
            ValueError: If the provider is not found
        """
        self._ensure_initialized()

        if provider_name not in self._provider_refs:
            raise ValueError(f"Provider '{provider_name}' not found")

        provider_class = self._provider_refs[provider_name]
        return provider_class.get_max_download_threads()

    def get_speaker_configuration(self, speaker: Optional[str]) -> Dict[str, Any]:
        """
        Get speaker configuration from appropriate provider.
        None or empty speaker values are treated as requests for the 'default' speaker.

        Args:
            speaker: The speaker to get configuration for, or None/empty for default speaker

        Returns:
            Dict[str, Any]: Configuration parameters from the appropriate provider
        """
        self._ensure_initialized()

        if not speaker:
            speaker = "default"

        if speaker not in self._speaker_configs_map:
            raise VoiceNotFoundError(
                f"No configuration found for speaker '{speaker}'"
            )  # Use specific error
        return self._speaker_configs_map[speaker]

    ####
    # Voice Configuration YAML generation
    ####

    def _analyze_speakers(self, dialogues: List[Dict]) -> Dict[str, int]:
        """
        Analyze list of dialogue chunks to count speaker lines.
        'default' speaker is used for chunks with no speaker attribute.
        Returns counts with 'default' first, followed by other speakers sorted by frequency.
        """
        from collections import Counter
        from typing import Counter as TypedCounter

        counts: TypedCounter[str] = Counter()
        default_count = 0

        for dialogue in dialogues:
            if dialogue["type"] == "dialogue":
                speaker = dialogue.get("speaker")
                if speaker:
                    counts[speaker] += 1
                else:
                    default_count += 1
            else:
                # Non-dialogue chunks use default speaker
                default_count += 1

        # Create ordered dict with default first
        result = {"default": default_count}

        # Add other speakers sorted by count (descending) then name
        for speaker, count in sorted(counts.items(), key=lambda x: (-x[1], x[0])):
            result[speaker] = count

        return result

    def generate_yaml_config(
        self,
        dialogues: List[Dict],
        output_path: Path,
        provider_name: Optional[str] = None,
        include_optional_fields: bool = False,
    ) -> None:
        """
        Generate initial YAML configuration template for TTS providers.

        Args:
            dialogues: List of dialogue chunks
            output_path: Where to save the YAML template
            provider_name: Optional specific provider to generate for
        """
        from ruamel.yaml.comments import CommentedMap

        yaml = YAML()
        yaml.indent(mapping=2, sequence=4, offset=2)
        yaml.width = 4096

        # Get speaker statistics
        speaker_counts = self._analyze_speakers(dialogues)

        # Build base content structure
        content = CommentedMap()

        # Set document start comment (instructions)
        if provider_name:
            provider_class = self._get_provider_class(provider_name)
            content.yaml_set_start_comment(
                f"{provider_class.get_yaml_instructions()}\n"
            )
        else:
            content.yaml_set_start_comment(
                "Voice configuration for speakers\n"
                "Each speaker requires:\n"
                "  provider: The TTS provider to use\n"
                "  Additional provider-specific configuration fields\n"
                "  Optional fields can be included at the root level\n\n"
            )

        # Add sections with proper spacing
        for speaker, count in speaker_counts.items():
            speaker_config = CommentedMap()
            if provider_name:
                provider_class = self._get_provider_class(provider_name)
                speaker_config["provider"] = provider_name
                for field in provider_class.get_required_fields():
                    speaker_config[field] = None
                if include_optional_fields:
                    for field in provider_class.get_optional_fields():
                        speaker_config[field] = None
            else:
                speaker_config["provider"] = None

            # Add the speaker with line count comment and spacing
            content[speaker] = speaker_config

            # Calculate character statistics
            total_chars = sum(
                len(str(dialogue.get("text", "")))
                for dialogue in dialogues
                if (
                    dialogue.get("speaker") == speaker
                    or (not dialogue.get("speaker") and speaker == "default")
                )
            )
            longest_dialogue = max(
                (
                    len(str(dialogue.get("text", "")))
                    for dialogue in dialogues
                    if (
                        dialogue.get("speaker") == speaker
                        or (not dialogue.get("speaker") and speaker == "default")
                    )
                ),
                default=0,
            )

            # Special comment for default speaker
            if speaker == "default":
                comment = (
                    f"\ndefault: {count} lines - Used for all non-dialogue pieces "
                    "(scene descriptions, scene headings, etc.)\n"
                    f"Total characters: {total_chars}, Longest dialogue: {longest_dialogue} characters"
                )
            else:
                comment = f"\n{speaker}: {count} lines\nTotal characters: {total_chars}, Longest dialogue: {longest_dialogue} characters"

            content.yaml_set_comment_before_after_key(
                speaker, before=comment, after="\n"
            )

        # Write to file
        self._write_yaml(content, output_path)

    def update_yaml_with_provider_fields(
        self,
        yaml_path: Path,
        output_path: Path,
        dialogues: List[Dict],
        include_optional_fields: bool = False,
    ) -> None:
        """
        Update YAML with provider-specific fields, grouped by provider.

        Args:
            yaml_path: Path to existing YAML file
            output_path: Where to save the updated YAML
            dialogues: List of dialogue chunks
        """
        # Load existing YAML to get provider assignments
        yaml = YAML()
        with open(yaml_path, "r") as f:
            yaml_content = yaml.load(f)

        if not isinstance(yaml_content, dict):
            raise ValueError("Invalid YAML format: root must be a mapping")

        # Group speakers by provider
        provider_groups = defaultdict(list)
        for speaker, config in yaml_content.items():
            if not isinstance(config, dict):
                raise ValueError(
                    f"Configuration for speaker '{speaker}' must be a mapping, not {type(config)}"
                )

            if "provider" not in config:
                raise ValueError(
                    f"Speaker '{speaker}' is missing the required 'provider' field"
                )

            provider = config["provider"]
            if not provider or provider == "None":
                raise ValueError(
                    f"Speaker '{speaker}' has an empty or None provider. Please specify a valid provider "
                    f"(e.g., 'elevenlabs', 'openai', etc.) in the voice configuration YAML."
                )
            provider_groups[config["provider"]].append(speaker)

        # Get speaker statistics for line counts
        speaker_counts = self._analyze_speakers(dialogues)

        # Build new content
        content = CommentedMap()
        first_provider = True

        # Process each provider group
        for provider, speakers in provider_groups.items():
            provider_class = self._get_provider_class(provider)

            # Add provider instructions
            if first_provider:
                content.yaml_set_start_comment(provider_class.get_yaml_instructions())
                first_provider = False
            else:
                # Add a blank line and instructions before next provider's speakers
                next_speaker = speakers[0]
                # Remove comment marks from instructions to avoid double-commenting
                instructions = provider_class.get_yaml_instructions().replace("# ", "")
                content.yaml_set_comment_before_after_key(
                    next_speaker, before=f"\n{instructions}\n"
                )

            # Sort speakers by line count within this provider group
            speakers.sort(key=lambda s: (-speaker_counts.get(s, 0), s))

            # Add speakers for this provider
            for speaker in speakers:
                speaker_config = CommentedMap()
                speaker_config["provider"] = provider

                # Add provider-specific fields
                for field in provider_class.get_required_fields():
                    if field != "provider":
                        speaker_config[field] = None
                if include_optional_fields:
                    for field in provider_class.get_optional_fields():
                        speaker_config[field] = None

                # Add speaker with line count and spacing
                content[speaker] = speaker_config
                count = speaker_counts.get(speaker, 0)

                # Calculate character statistics
                total_chars = sum(
                    len(str(dialogue.get("text", "")))
                    for dialogue in dialogues
                    if (
                        dialogue.get("speaker") == speaker
                        or (not dialogue.get("speaker") and speaker == "default")
                    )
                )
                longest_dialogue = max(
                    (
                        len(str(dialogue.get("text", "")))
                        for dialogue in dialogues
                        if (
                            dialogue.get("speaker") == speaker
                            or (not dialogue.get("speaker") and speaker == "default")
                        )
                    ),
                    default=0,
                )

                # Special comment for default speaker
                if speaker == "default":
                    comment = (
                        f"\ndefault: {count} lines - Used for all non-dialogue pieces "
                        "(scene descriptions, scene headings, etc.)\n"
                        f"Total characters: {total_chars}, Longest dialogue: {longest_dialogue} characters"
                    )
                else:
                    comment = f"\n{speaker}: {count} lines\nTotal characters: {total_chars}, Longest dialogue: {longest_dialogue} characters"

                content.yaml_set_comment_before_after_key(
                    speaker, before=comment, after="\n"
                )

        self._write_yaml(content, output_path)

    def _write_yaml(self, content: CommentedMap, output_path: Path) -> None:
        """Write YAML content to file with consistent formatting."""
        yaml = YAML()
        yaml.indent(mapping=2, sequence=4, offset=2)
        yaml.width = 4096

        with open(output_path, "w") as f:
            yaml.dump(content, f)

    def update_yaml_with_provider_fields_preserving_comments(
        self,
        yaml_path: Path,
        output_path: Path,
        dialogues: List[Dict],
        include_optional_fields: bool = False,
    ) -> None:
        """
        Update YAML with provider-specific fields while preserving comments and existing field values.
        Maintains the original structure and ordering within provider groups.

        Args:
            yaml_path: Path to existing YAML file
            output_path: Where to save the updated YAML
            dialogues: List of dialogue chunks (not used in this version, kept for interface compatibility)
        """
        # Read the entire file
        with open(yaml_path, "r") as f:
            content = f.read()

        # Split content into chunks based on blank lines
        # Each chunk includes all content (comments + yaml) until the next blank line
        chunks = []
        current_chunk = []

        for line in content.split("\n"):
            if line.strip():  # Non-empty line
                current_chunk.append(line)
            elif current_chunk:  # Empty line and we have content
                chunks.append("\n".join(current_chunk))
                current_chunk = []

        # Add the final chunk if it exists
        if current_chunk:
            chunks.append("\n".join(current_chunk))

        # Filter out chunks that don't contain YAML (e.g., header comments)
        speaker_chunks = []
        for chunk in chunks:
            # Look for lines that could be YAML (not starting with #)
            has_yaml = any(
                line.strip() and not line.strip().startswith("#")
                for line in chunk.split("\n")
            )
            if has_yaml:
                speaker_chunks.append(chunk)

        # Group chunks by provider
        provider_chunks: Dict[str, List[str]] = {}
        yaml = YAML()

        for chunk in speaker_chunks:
            # Find all lines that could be YAML (not comments)
            yaml_lines = [
                line
                for line in chunk.split("\n")
                if line.strip() and not line.strip().startswith("#")
            ]

            # Try to parse the YAML portion
            try:
                # Join potential YAML lines and parse
                yaml_text = "\n".join(yaml_lines)
                config = yaml.load(yaml_text)

                if not isinstance(config, dict):
                    raise ValueError(f"Invalid YAML structure in chunk: {chunk}")

                # Check for multiple root-level keys (indicates missing blank line between speakers)
                if len(config) > 1:
                    speaker_names = list(config.keys())
                    raise ValueError(
                        f"Multiple speakers found in single chunk - missing blank line between speaker chunks?\n"
                        f"Speakers: {', '.join(speaker_names)}\n"
                        f"Chunk:\n{chunk}"
                    )

                first_key = next(iter(config))
                if not isinstance(config[first_key], dict):
                    raise ValueError(f"Invalid YAML structure for speaker {first_key}")

                provider = config[first_key].get("provider")
                if not provider:
                    raise ValueError(f"No provider specified for speaker {first_key}")

                # Verify provider is valid
                if provider not in self.get_available_providers():
                    raise ValueError(
                        f"Invalid provider '{provider}' for speaker {first_key}. "
                        f"Valid providers are: {', '.join(self.get_available_providers())}"
                    )

                provider_chunks.setdefault(provider, []).append(chunk)

            except Exception as e:
                raise ValueError(
                    f"Error processing YAML chunk:\n{chunk}\n\nError: {str(e)}"
                )

        # Build the new content with provider instructions and missing fields
        new_content = []
        first_provider = True

        for provider, chunks in provider_chunks.items():
            provider_class = self._get_provider_class(provider)
            required_fields = provider_class.get_required_fields()

            # Add provider instructions
            if first_provider:
                new_content.append(provider_class.get_yaml_instructions())
                first_provider = False
            else:
                # Add a blank line and instructions before next provider's chunks
                instructions = provider_class.get_yaml_instructions()
                new_content.append(f"\n{instructions}")

            # Process each chunk in this provider group
            for chunk in chunks:
                # Split into lines for processing
                lines = chunk.split("\n")
                yaml_lines = []
                comment_lines = []

                # Separate YAML from comments while preserving order
                for line in lines:
                    if line.strip().startswith("#"):
                        comment_lines.append(line)
                    elif line.strip():
                        yaml_lines.append(line)

                # Parse the YAML content
                yaml_text = "\n".join(yaml_lines)
                config = yaml.load(yaml_text)
                speaker = next(iter(config))
                speaker_config = config[speaker]

                # Add any missing required fields
                for field in required_fields:
                    if field != "provider" and field not in speaker_config:
                        speaker_config[field] = None

                # Add optional fields if requested
                if include_optional_fields:
                    for field in provider_class.get_optional_fields():
                        if field not in speaker_config:
                            speaker_config[field] = None

                # Reconstruct the chunk with added fields
                yaml_str = StringIO()
                yaml.dump({speaker: speaker_config}, yaml_str)
                new_yaml = yaml_str.getvalue().strip()

                # Reconstruct the full chunk with comments and YAML
                reconstructed_chunk = []
                reconstructed_chunk.extend(comment_lines)
                reconstructed_chunk.append(new_yaml)

                new_content.append("\n".join(reconstructed_chunk))
                new_content.append("")  # Add blank line between chunks

        # Write the final content
        with open(output_path, "w") as f:
            f.write("\n".join(new_content))
