import os
import yaml
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
import importlib
from collections import defaultdict
from typing import Dict, Optional, Type, Any, List
import json
from io import StringIO

from .base.tts_provider import TTSProvider


class TTSProviderManager:
    """Manages TTS providers and handles audio generation delegation."""

    def __init__(self, config_path: str, overall_provider: Optional[str] = None):
        """
        Initialize the TTS Manager.

        Args:
            config_path: Path to YAML configuration file
            overall_provider: Optional provider to use when provider isn't specified in config
        """
        self._config_path = config_path
        self._overall_provider = overall_provider
        self._providers: Dict[str, TTSProvider] = {}
        self._speaker_providers: Dict[str, str] = {}
        self._is_initialized = False

    def _ensure_initialized(self) -> None:
        """Ensure config is loaded and providers are initialized."""
        if not self._is_initialized:
            self._load_config(self._config_path)
            self._is_initialized = True

    @classmethod
    def _get_provider_class(cls, provider_name: str) -> Type[TTSProvider]:
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
                f"tts_providers.{provider_name}.tts_provider"
            )

            # Get the provider class
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, TTSProvider)
                    and attr != TTSProvider
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

    def _load_config(self, config_path: str) -> None:
        """
        Load and validate provider configuration.

        Args:
            config_path: Path to YAML configuration file

        Raises:
            ValueError: If configuration is invalid or providers cannot be initialized
        """
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        # Group speakers by provider
        provider_configs: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(dict)

        for speaker, speaker_config in config.items():
            # Get provider from config or use overall provider
            provider_name = speaker_config.get("provider")
            if not provider_name and self._overall_provider is not None:
                provider_name = self._overall_provider
            elif not provider_name:
                raise ValueError(
                    f"No provider specified for speaker '{speaker}' and no overall provider set"
                )

            # Store speaker config for this provider
            provider_configs[provider_name][speaker] = speaker_config
            self._speaker_providers[speaker] = provider_name

        # Initialize providers with their configs
        for provider_name, speaker_configs in provider_configs.items():
            if provider_name not in self._providers:
                provider_class = self._get_provider_class(provider_name)
                provider = provider_class()
                provider.initialize(speaker_configs)
                self._providers[provider_name] = provider

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
        provider_dir = os.path.dirname(__file__)

        for item in os.listdir(provider_dir):
            dir_path = os.path.join(provider_dir, item)
            if os.path.isdir(dir_path) and item not in ["base", "__pycache__"]:
                try:
                    # Try to load the provider to verify it's valid
                    cls._get_provider_class(item)
                    providers.append(item)
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
        return self._providers[provider_name].generate_audio(speaker, text)

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
        return self._providers[provider_name].get_speaker_identifier(speaker)

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
        return self._providers[provider_name].get_provider_identifier()

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

        provider_name = self.get_provider_for_speaker(speaker)
        return self._providers[provider_name].get_speaker_configuration(speaker)

    ####
    # Voice Configuration YAML generation
    ####

    def _analyze_speakers(self, dialogues: List[Dict]) -> Dict[str, int]:
        """
        Analyze list of dialog chunks to count speaker lines.
        'default' speaker is used for chunks with no speaker attribute.
        Returns counts with 'default' first, followed by other speakers sorted by frequency.
        """
        from collections import Counter

        counts = Counter()
        default_count = 0

        for dialogue in dialogues:
            if dialogue["type"] == "dialog":
                speaker = dialogue.get("speaker")
                if speaker:
                    counts[speaker] += 1
                else:
                    default_count += 1
            else:
                # Non-dialog chunks use default speaker
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
        output_path: str,
        provider_name: Optional[str] = None,
        include_optional_fields: bool = False,
    ) -> None:
        """
        Generate initial YAML configuration template for TTS providers.

        Args:
            dialogues: List of dialog chunks
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
            longest_dialog = max(
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
                    f"Total characters: {total_chars}, Longest dialog: {longest_dialog} characters"
                )
            else:
                comment = f"\n{speaker}: {count} lines\nTotal characters: {total_chars}, Longest dialog: {longest_dialog} characters"

            content.yaml_set_comment_before_after_key(
                speaker, before=comment, after="\n"
            )

        # Write to file
        self._write_yaml(content, output_path)

    def update_yaml_with_provider_fields(
        self,
        yaml_path: str,
        output_path: str,
        dialogues: List[Dict],
        include_optional_fields: bool = False,
    ) -> None:
        """
        Update YAML with provider-specific fields, grouped by provider.

        Args:
            yaml_path: Path to existing YAML file
            output_path: Where to save the updated YAML
            dialogues: List of dialog chunks
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
                longest_dialog = max(
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
                        f"Total characters: {total_chars}, Longest dialog: {longest_dialog} characters"
                    )
                else:
                    comment = f"\n{speaker}: {count} lines\nTotal characters: {total_chars}, Longest dialog: {longest_dialog} characters"

                content.yaml_set_comment_before_after_key(
                    speaker, before=comment, after="\n"
                )

        self._write_yaml(content, output_path)

    def _write_yaml(self, content: CommentedMap, output_path: str) -> None:
        """Write YAML content to file with consistent formatting."""
        yaml = YAML()
        yaml.indent(mapping=2, sequence=4, offset=2)
        yaml.width = 4096

        with open(output_path, "w") as f:
            yaml.dump(content, f)

    def update_yaml_with_provider_fields_preserving_comments(
        self,
        yaml_path: str,
        output_path: str,
        dialogues: List[Dict],
        include_optional_fields: bool = False,
    ) -> None:
        """
        Update YAML with provider-specific fields while preserving comments and existing field values.
        Maintains the original structure and ordering within provider groups.

        Args:
            yaml_path: Path to existing YAML file
            output_path: Where to save the updated YAML
            dialogues: List of dialog chunks (not used in this version, kept for interface compatibility)
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
        provider_chunks = {}
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
