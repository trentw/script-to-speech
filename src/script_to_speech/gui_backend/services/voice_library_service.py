"""Voice library integration service."""

import json
import logging
import re
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional

from ruamel.yaml import YAML

from script_to_speech.voice_library.voice_library import VoiceLibrary

from ..config import settings
from ..models import (
    LLMRunImportResponse,
    LLMRunVoiceData,
    SchemaPropertyDefinition,
    VoiceDescription,
    VoiceDetails,
    VoiceEntry,
    VoiceLibrarySchemaResponse,
    VoiceProperties,
    VoiceTags,
    VoiceUpdateRequest,
)

logger = logging.getLogger(__name__)


class VoiceLibraryService:
    """Service for voice library integration."""

    def __init__(self) -> None:
        """Initialize the voice library service."""
        self._voice_library = VoiceLibrary()
        self._voices_cache: Dict[str, List[VoiceEntry]] = {}
        self._load_voice_library()

    def _load_voice_library(self) -> None:
        """Load and cache voice library data."""
        try:
            # Get all available providers by scanning the voice library directory
            all_providers = self._get_available_providers_from_filesystem()

            for provider in all_providers:
                try:
                    voices = self._get_provider_voices(provider)
                    self._voices_cache[provider] = voices
                    logger.info(f"Loaded {len(voices)} voices for provider: {provider}")
                except Exception as e:
                    logger.warning(
                        f"Failed to load voices for provider {provider}: {e}"
                    )
                    self._voices_cache[provider] = []

        except Exception as e:
            logger.error(f"Failed to load voice library: {e}")

    def _get_available_providers_from_filesystem(self) -> List[str]:
        """Get available providers by scanning the voice library directory."""
        try:
            from script_to_speech.voice_library.constants import REPO_VOICE_LIBRARY_PATH

            providers = []
            if REPO_VOICE_LIBRARY_PATH.exists():
                for provider_dir in REPO_VOICE_LIBRARY_PATH.iterdir():
                    if (
                        provider_dir.is_dir()
                        and not provider_dir.name.startswith(".")
                        and not provider_dir.name.startswith("dummy_")
                    ):
                        # Check if directory has any .yaml files
                        yaml_files = list(provider_dir.glob("*.yaml"))
                        if yaml_files:
                            providers.append(provider_dir.name)

            return providers
        except Exception as e:
            logger.error(f"Failed to scan voice library directory: {e}")
            return []

    def _get_provider_voices(self, provider: str) -> List[VoiceEntry]:
        """Get all voices for a specific provider."""
        voices = []

        try:
            # Get voice IDs for the provider by loading voice data directly
            voice_ids = self._get_voice_ids_for_provider(provider)

            for voice_id in voice_ids:
                try:
                    voice_entry = self._create_voice_entry(provider, voice_id)
                    if voice_entry:
                        voices.append(voice_entry)
                except Exception as e:
                    logger.warning(
                        f"Failed to create voice entry for {provider}/{voice_id}: {e}"
                    )

        except Exception as e:
            logger.warning(f"Failed to get voice IDs for provider {provider}: {e}")

        return voices

    def _get_voice_ids_for_provider(self, provider: str) -> List[str]:
        """Get all voice IDs for a specific provider by directly reading voice library files."""
        try:
            # Load provider voices to get the voice data
            provider_voices = self._voice_library._load_provider_voices(provider)
            return list(provider_voices.keys())
        except Exception as e:
            logger.warning(f"Failed to get voice IDs for provider {provider}: {e}")
            return []

    def _create_voice_entry(self, provider: str, sts_id: str) -> Optional[VoiceEntry]:
        """Create a VoiceEntry from provider and sts_id."""
        try:
            # Get voice data by accessing the internal cache directly
            provider_voices = self._voice_library._load_provider_voices(provider)
            voice_data = provider_voices.get(sts_id)
            if not voice_data:
                return None

            # Extract configuration
            config = voice_data.get("config", {})

            # Extract voice properties
            voice_properties = None
            if "voice_properties" in voice_data:
                props_data = voice_data["voice_properties"]
                voice_properties = VoiceProperties(
                    accent=props_data.get("accent"),
                    gender=props_data.get("gender"),
                    age=props_data.get("age"),
                    authority=props_data.get("authority"),
                    energy=props_data.get("energy"),
                    pace=props_data.get("pace"),
                    performative=props_data.get("performative"),
                    pitch=props_data.get("pitch"),
                    quality=props_data.get("quality"),
                    range=props_data.get("range"),
                    special_vocal_characteristics=props_data.get(
                        "special_vocal_characteristics"
                    ),
                )

            # Extract description
            description = None
            if "description" in voice_data:
                desc_data = voice_data["description"]
                description = VoiceDescription(
                    provider_name=desc_data.get("provider_name"),
                    provider_description=desc_data.get("provider_description"),
                    provider_use_cases=desc_data.get("provider_use_cases"),
                    custom_description=desc_data.get("custom_description"),
                    perceived_age=desc_data.get("perceived_age"),
                )

            # Extract tags
            tags = None
            if "tags" in voice_data:
                tags_data = voice_data["tags"]
                tags = VoiceTags(
                    provider_use_cases=tags_data.get("provider_use_cases"),
                    custom_tags=tags_data.get("custom_tags"),
                    character_types=tags_data.get("character_types"),
                )

            # Extract preview URL
            preview_url = voice_data.get("preview_url")

            return VoiceEntry(
                sts_id=sts_id,
                provider=provider,
                config=config,
                voice_properties=voice_properties,
                description=description,
                tags=tags,
                preview_url=preview_url,
            )

        except Exception as e:
            logger.error(f"Failed to create voice entry for {provider}/{sts_id}: {e}")
            return None

    def get_available_providers(self) -> List[str]:
        """Get list of providers with voice library data."""
        return list(self._voices_cache.keys())

    def get_provider_voices(self, provider: str) -> List[VoiceEntry]:
        """Get all voices for a specific provider."""
        return self._voices_cache.get(provider, [])

    def get_voice_details(self, provider: str, sts_id: str) -> Optional[VoiceDetails]:
        """Get detailed information about a specific voice."""
        try:
            # Create basic voice entry
            voice_entry = self._create_voice_entry(provider, sts_id)
            if not voice_entry:
                return None

            # Get expanded configuration
            expanded_config = {}
            try:
                expanded_config = self._voice_library.expand_config(provider, sts_id)
            except Exception as e:
                logger.warning(f"Failed to expand config for {provider}/{sts_id}: {e}")
                expanded_config = voice_entry.config

            return VoiceDetails(
                sts_id=voice_entry.sts_id,
                provider=voice_entry.provider,
                config=voice_entry.config,
                voice_properties=voice_entry.voice_properties,
                description=voice_entry.description,
                tags=voice_entry.tags,
                preview_url=voice_entry.preview_url,
                expanded_config=expanded_config,
            )

        except Exception as e:
            logger.error(f"Failed to get voice details for {provider}/{sts_id}: {e}")
            return None

    def expand_sts_id(self, provider: str, sts_id: str) -> Dict[str, Any]:
        """Expand an sts_id to full provider configuration."""
        try:
            return self._voice_library.expand_config(provider, sts_id)
        except Exception as e:
            logger.error(f"Failed to expand sts_id {provider}/{sts_id}: {e}")
            return {}

    def search_voices(
        self,
        query: Optional[str] = None,
        provider: Optional[str] = None,
        gender: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> List[VoiceEntry]:
        """Search voices based on criteria."""
        all_voices = []

        # Get voices from specified provider or all providers
        if provider:
            if provider in self._voices_cache:
                all_voices = self._voices_cache[provider]
        else:
            for provider_voices in self._voices_cache.values():
                all_voices.extend(provider_voices)

        # Apply filters
        filtered_voices = all_voices

        if query:
            query_lower = query.lower()
            filtered_voices = [
                voice
                for voice in filtered_voices
                if (
                    query_lower in voice.sts_id.lower()
                    or (
                        voice.description
                        and voice.description.provider_name
                        and query_lower in voice.description.provider_name.lower()
                    )
                    or (
                        voice.description
                        and voice.description.custom_description
                        and query_lower in voice.description.custom_description.lower()
                    )
                )
            ]

        if gender:
            filtered_voices = [
                voice
                for voice in filtered_voices
                if (
                    voice.voice_properties
                    and voice.voice_properties.gender
                    and voice.voice_properties.gender.lower() == gender.lower()
                )
            ]

        if tags:
            filtered_voices = [
                voice
                for voice in filtered_voices
                if (
                    voice.tags
                    and voice.tags.custom_tags
                    and any(
                        tag.lower() in [t.lower() for t in voice.tags.custom_tags]
                        for tag in tags
                    )
                )
            ]

        return filtered_voices

    def get_voice_stats(self) -> Dict[str, Any]:
        """Get statistics about the voice library."""
        stats: Dict[str, Any] = {
            "total_voices": 0,
            "providers": {},
            "genders": {},
            "languages": set(),
        }

        for provider, voices in self._voices_cache.items():
            providers_dict = stats["providers"]
            providers_dict[provider] = len(voices)
            stats["total_voices"] = stats["total_voices"] + len(voices)

            for voice in voices:
                if voice.voice_properties and voice.voice_properties.gender:
                    gender = voice.voice_properties.gender
                    genders_dict = stats["genders"]
                    genders_dict[gender] = genders_dict.get(gender, 0) + 1

                if voice.voice_properties and voice.voice_properties.accent:
                    languages_set = stats["languages"]
                    languages_set.add(voice.voice_properties.accent)

        # Convert set to list for JSON serialization
        languages_set = stats["languages"]
        stats["languages"] = list(languages_set)

        return stats

    def get_schema(self) -> VoiceLibrarySchemaResponse:
        """Load voice library schema and return structured response."""
        from script_to_speech.voice_library.constants import REPO_VOICE_LIBRARY_PATH
        from script_to_speech.voice_library.schema_utils import load_schema_file

        schema_path = REPO_VOICE_LIBRARY_PATH / "voice_library_schema.yaml"
        schema_data = load_schema_file(schema_path, "Voice library schema")
        if not schema_data:
            raise ValueError(f"Failed to load schema from {schema_path}")

        voice_props = schema_data.get("voice_properties", {})
        properties: Dict[str, SchemaPropertyDefinition] = {}

        for prop_name, prop_def in voice_props.items():
            # Convert scale_points keys from float to string for JSON
            scale_points = None
            if "scale_points" in prop_def:
                scale_points = {str(k): v for k, v in prop_def["scale_points"].items()}

            properties[prop_name] = SchemaPropertyDefinition(
                description=prop_def.get("description", ""),
                type=prop_def.get("type", "range"),
                min=prop_def.get("min"),
                max=prop_def.get("max"),
                scale_points=scale_points,
                values=prop_def.get("values"),
            )

        return VoiceLibrarySchemaResponse(voice_properties=properties)

    def _find_yaml_file_for_voice(self, provider: str, sts_id: str) -> Optional[Path]:
        """Find the YAML file that contains a specific voice."""
        from script_to_speech.voice_library.constants import REPO_VOICE_LIBRARY_PATH

        provider_dir = REPO_VOICE_LIBRARY_PATH / provider
        if not provider_dir.exists():
            return None

        yaml_handler = YAML()
        yaml_handler.preserve_quotes = True

        for yaml_file in sorted(provider_dir.glob("*.yaml")):
            if yaml_file.name.startswith("provider_schema"):
                continue
            try:
                with open(yaml_file, "r") as f:
                    data = yaml_handler.load(f)
                if data and "voices" in data and sts_id in data["voices"]:
                    return yaml_file
            except Exception:
                continue

        return None

    def _validate_voice_properties(self, props: Dict[str, Any]) -> None:
        """Validate voice property values against the schema.

        Raises ValueError if any value is out of range or not a valid enum member.
        """
        schema = self.get_schema()
        for key, value in props.items():
            prop_def = schema.voice_properties.get(key)
            if not prop_def:
                continue  # Unknown property — skip (schema may be newer than code)

            if prop_def.type == "range" and isinstance(value, (int, float)):
                min_val = prop_def.min if prop_def.min is not None else 0.0
                max_val = prop_def.max if prop_def.max is not None else 1.0
                if not (min_val <= value <= max_val):
                    raise ValueError(
                        f"Property '{key}' value {value} is outside range "
                        f"[{min_val}, {max_val}]"
                    )

            elif prop_def.type == "enum" and isinstance(value, str) and value:
                if prop_def.values and value not in prop_def.values:
                    raise ValueError(
                        f"Property '{key}' value '{value}' is not a valid option. "
                        f"Allowed: {prop_def.values}"
                    )

    def update_voice(
        self, provider: str, sts_id: str, updates: VoiceUpdateRequest
    ) -> VoiceEntry:
        """Update a voice's properties, description, or tags in the YAML file."""
        yaml_path = self._find_yaml_file_for_voice(provider, sts_id)
        if not yaml_path:
            raise ValueError(f"Voice {provider}/{sts_id} not found in any YAML file")

        # Validate property values against schema before writing
        if updates.voice_properties is not None:
            props_to_validate = updates.voice_properties.model_dump(exclude_none=True)
            self._validate_voice_properties(props_to_validate)

        yaml_handler = YAML()
        yaml_handler.preserve_quotes = True
        yaml_handler.width = 4096

        with open(yaml_path, "r") as f:
            data = yaml_handler.load(f)

        voice_data = data["voices"][sts_id]

        # Deep-merge voice_properties updates
        if updates.voice_properties is not None:
            if "voice_properties" not in voice_data:
                voice_data["voice_properties"] = {}
            # exclude_none=True: intentional — the frontend omits fields it doesn't
            # want to change. To clear a value, the frontend sends an empty string
            # or the schema's default. This avoids needing a separate "fields to clear" list.
            props = updates.voice_properties.model_dump(exclude_none=True)
            for key, value in props.items():
                voice_data["voice_properties"][key] = value

        # Deep-merge description updates
        if updates.description is not None:
            if "description" not in voice_data:
                voice_data["description"] = {}
            desc = updates.description.model_dump(exclude_none=True)
            for key, value in desc.items():
                voice_data["description"][key] = value

        # Deep-merge tags updates
        if updates.tags is not None:
            if "tags" not in voice_data:
                voice_data["tags"] = {}
            tags = updates.tags.model_dump(exclude_none=True)
            for key, value in tags.items():
                voice_data["tags"][key] = value

        # Write back
        with open(yaml_path, "w") as f:
            yaml_handler.dump(data, f)

        # Flush caches so subsequent reads reflect disk state
        self._reload_provider(provider)

        # Return updated voice entry
        voice_entry = self._create_voice_entry(provider, sts_id)
        if not voice_entry:
            raise ValueError(f"Failed to read back updated voice {provider}/{sts_id}")
        return voice_entry

    def _reload_provider(self, provider: str) -> None:
        """Flush caches for a provider after writes."""
        self._voice_library.invalidate_cache(provider)

        # Rebuild our service cache for this provider
        try:
            voices = self._get_provider_voices(provider)
            self._voices_cache[provider] = voices
            logger.info(f"Reloaded {len(voices)} voices for provider: {provider}")
        except Exception as e:
            logger.error(f"Failed to reload provider {provider}: {e}")

    def list_llm_runs(self) -> List[Dict[str, str]]:
        """List available LLM labeler run directories from output/."""
        output_dir = settings.WORKSPACE_DIR / "output"
        if not output_dir.exists():
            return []

        runs = []
        for d in sorted(output_dir.iterdir(), reverse=True):
            if not d.is_dir():
                continue
            if not d.name.startswith("llm_labeler_"):
                continue
            consensus_dir = d / "consensus" / "final"
            if not consensus_dir.exists():
                continue

            # Extract provider and timestamp from name
            match = re.match(r"llm_labeler_(.+?)_(\d{8}_\d{6})$", d.name)
            provider = match.group(1) if match else d.name
            timestamp = match.group(2) if match else ""

            # Count voices
            voice_count = len(list(consensus_dir.glob("*.json")))

            runs.append(
                {
                    "name": d.name,
                    "path": f"output/{d.name}",
                    "provider": provider,
                    "timestamp": timestamp,
                    "voice_count": str(voice_count),
                }
            )

        return runs

    def load_llm_run(self, run_dir: str) -> LLMRunImportResponse:
        """Parse an LLM voice labeler output directory."""
        run_path = Path(run_dir)
        if not run_path.is_absolute():
            # Resolve relative to project root
            run_path = settings.WORKSPACE_DIR / run_path

        if not run_path.exists():
            raise ValueError(f"Run directory not found: {run_path}")

        consensus_dir = run_path / "consensus" / "final"
        audio_dir = run_path / "audio"

        if not consensus_dir.exists():
            raise ValueError(f"No consensus/final/ directory found in {run_path}")

        # Extract provider from directory name pattern: llm_labeler_{provider}_{timestamp}
        dir_name = run_path.name
        match = re.match(r"llm_labeler_(.+?)_\d{8}_\d{6}$", dir_name)
        if match:
            provider = match.group(1)
        else:
            # Fallback: try test_ prefix or just use directory name
            match = re.match(r"test_labeler_(.+)$", dir_name)
            provider = match.group(1) if match else dir_name

        # Read all JSON files from consensus/final/
        voices: Dict[str, LLMRunVoiceData] = {}
        for json_file in sorted(consensus_dir.glob("*.json")):
            try:
                with open(json_file, "r") as f:
                    voice_consensus = json.load(f)
                sts_id = json_file.stem
                voices[sts_id] = LLMRunVoiceData(
                    result=voice_consensus.get("result", {}),
                    flags=voice_consensus.get("flags", []),
                )
            except Exception as e:
                logger.warning(f"Failed to parse {json_file}: {e}")

        return LLMRunImportResponse(
            provider=provider,
            voices=voices,
            audio_dir=str(audio_dir) if audio_dir.exists() else "",
        )


# Global instance
voice_library_service = VoiceLibraryService()
