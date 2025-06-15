import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ruamel.yaml import YAML
from ruamel.yaml.constructor import DuplicateKeyError

from ..text_processors.processor_manager import TextProcessorManager
from ..text_processors.utils import get_text_processor_configs
from ..utils.dialogue_stats_utils import SpeakerStats, get_speaker_statistics
from ..utils.logging import get_screenplay_logger
from .tts_provider_manager import TTSProviderManager

logger = get_screenplay_logger("utils.processor")


class ProviderStatistics:
    """Statistics for a single TTS provider."""

    def __init__(self, provider_name: str):
        self.provider_name = provider_name
        self.voice_count = 0
        self.total_lines = 0
        self.total_characters = 0


class VoiceDuplicateInfo:
    """Information about duplicate voice configurations."""

    def __init__(self, voice_config_key: str, voice_config: dict):
        self.voice_config_key = voice_config_key  # Serialized config for uniqueness
        self.voice_config = voice_config  # The actual config dict
        self.characters: List[str] = []  # List of character names using this config
        self.character_stats: Dict[str, SpeakerStats] = (
            {}
        )  # Statistics for each character


class VoiceConfigStatistics:
    """Complete statistics for voice configuration analysis."""

    def __init__(self) -> None:
        self.provider_stats: Dict[str, ProviderStatistics] = {}
        self.voice_duplicates: Dict[str, List[VoiceDuplicateInfo]] = (
            {}
        )  # Grouped by provider


def _serialize_voice_config(voice_config: dict) -> str:
    """
    Create a unique key for voice configuration based on all properties except speaker name.

    Args:
        voice_config: The voice configuration dictionary

    Returns:
        str: A serialized key representing the unique voice configuration
    """
    import json

    # Create a copy without the speaker-specific fields
    config_copy = {k: v for k, v in voice_config.items() if k not in ["speaker"]}

    # Sort keys for consistent serialization
    return json.dumps(config_copy, sort_keys=True)


def _get_provider_statistics(
    voice_config_data: dict, speaker_stats: dict
) -> Dict[str, ProviderStatistics]:
    """
    Calculate provider-specific statistics.

    Args:
        voice_config_data: The loaded voice configuration YAML data
        speaker_stats: Dictionary of speaker statistics from dialogue analysis

    Returns:
        Dict[str, ProviderStatistics]: Statistics grouped by provider
    """
    provider_stats = {}

    for speaker, config in voice_config_data.items():
        if not isinstance(config, dict):
            continue

        provider_name = config.get("provider")
        if not provider_name:
            continue

        # Initialize provider stats if not exists
        if provider_name not in provider_stats:
            provider_stats[provider_name] = ProviderStatistics(provider_name)

        provider_stat = provider_stats[provider_name]
        provider_stat.voice_count += 1

        # Add speaker statistics if available
        if speaker in speaker_stats:
            speaker_data = speaker_stats[speaker]
            provider_stat.total_lines += speaker_data.line_count
            provider_stat.total_characters += speaker_data.total_characters

    return provider_stats


def _get_voice_duplicate_analysis(
    voice_config_data: dict, speaker_stats: Dict[str, SpeakerStats]
) -> Dict[str, List[VoiceDuplicateInfo]]:
    """
    Analyze voice configurations for duplicates, grouped by provider.

    Args:
        voice_config_data: The loaded voice configuration YAML data
        speaker_stats: Dictionary of speaker statistics from dialogue analysis

    Returns:
        Dict[str, List[VoiceDuplicateInfo]]: Duplicate analysis grouped by provider
    """
    # Track voice configs by provider
    provider_voice_configs: Dict[str, Dict[str, VoiceDuplicateInfo]] = {}

    for speaker, config in voice_config_data.items():
        if not isinstance(config, dict):
            continue

        provider_name = config.get("provider")
        if not provider_name:
            continue

        # Initialize provider tracking if not exists
        if provider_name not in provider_voice_configs:
            provider_voice_configs[provider_name] = {}

        # Generate unique key for this voice configuration
        voice_key = _serialize_voice_config(config)

        # Track this voice configuration
        if voice_key not in provider_voice_configs[provider_name]:
            provider_voice_configs[provider_name][voice_key] = VoiceDuplicateInfo(
                voice_key, config
            )

        # Add this character to the voice configuration
        provider_voice_configs[provider_name][voice_key].characters.append(speaker)

        # Add character statistics if available
        if speaker in speaker_stats:
            provider_voice_configs[provider_name][voice_key].character_stats[
                speaker
            ] = speaker_stats[speaker]

    # Filter to only include duplicates (configs used by multiple characters)
    duplicates_by_provider = {}
    for provider_name, voice_configs in provider_voice_configs.items():
        duplicates = [
            duplicate_info
            for duplicate_info in voice_configs.values()
            if len(duplicate_info.characters) > 1
        ]
        if duplicates:
            duplicates_by_provider[provider_name] = duplicates

    return duplicates_by_provider


def generate_voice_config_statistics(
    processed_chunks: List[dict], voice_config_data: dict
) -> VoiceConfigStatistics:
    """
    Generate comprehensive statistics for voice configuration analysis.

    Args:
        processed_chunks: List of processed dialogue chunks
        voice_config_data: The loaded voice configuration YAML data

    Returns:
        VoiceConfigStatistics: Complete statistics object
    """
    # Get speaker statistics from dialogue analysis
    speaker_stats = get_speaker_statistics(processed_chunks)

    # Generate provider statistics
    provider_stats = _get_provider_statistics(voice_config_data, speaker_stats)

    # Generate voice duplicate analysis
    voice_duplicates = _get_voice_duplicate_analysis(voice_config_data, speaker_stats)

    # Create and populate the statistics object
    stats = VoiceConfigStatistics()
    stats.provider_stats = provider_stats
    stats.voice_duplicates = voice_duplicates

    return stats


def _format_statistics_report(stats: VoiceConfigStatistics) -> str:
    """
    Format the statistics into a human-readable report.

    Args:
        stats: The statistics object to format

    Returns:
        str: Formatted statistics report
    """
    lines = []

    # Provider Statistics Section
    lines.append("\n" + "=" * 60)
    lines.append("VOICE CONFIGURATION STATISTICS")
    lines.append("=" * 60)

    if stats.provider_stats:
        lines.append("\nProvider Statistics:")
        lines.append("-" * 30)

        for provider_name, provider_stat in sorted(stats.provider_stats.items()):
            lines.append(f"  {provider_name}:")
            lines.append(f"    • Voices: {provider_stat.voice_count}")
            lines.append(f"    • Total lines: {provider_stat.total_lines}")
            lines.append(f"    • Total characters: {provider_stat.total_characters}")
    else:
        lines.append("\nNo provider statistics available.")

    # Voice Duplicate Analysis Section
    lines.append("\nVoice Duplicate Analysis:")
    lines.append("-" * 30)

    if stats.voice_duplicates:
        for provider_name, duplicates in sorted(stats.voice_duplicates.items()):
            lines.append(f"\n  {provider_name}:")
            for i, duplicate_info in enumerate(duplicates, 1):
                # Show the voice configuration (excluding provider since it's obvious)
                config_display = {
                    k: v
                    for k, v in duplicate_info.voice_config.items()
                    if k != "provider"
                }
                lines.append(f"    Duplicate #{i}: {config_display}")
                lines.append("      Characters using this voice:")

                # Add character statistics for each character using this duplicate voice
                for character in sorted(duplicate_info.characters):
                    # Get character statistics
                    char_stats = duplicate_info.character_stats.get(character)
                    if char_stats:
                        lines.append(
                            f"        • {character}: {char_stats.line_count} lines, "
                            f"{char_stats.total_characters} characters, "
                            f"longest dialogue: {char_stats.longest_dialogue} characters"
                        )
                    else:
                        lines.append(
                            f"        • {character}: (no statistics available)"
                        )
    else:
        lines.append("  ✓ No duplicate voice configurations found.")

    return "\n".join(lines)


def _handle_yaml_operation(
    input_json_path: Path,
    text_processor_configs: Optional[List[Path]] = None,
    provider: Optional[str] = None,
    existing_yaml_path: Optional[Path] = None,
    include_optional_fields: bool = False,
) -> Path:
    """
    Common functionality for YAML generation and population operations.

    Args:
        input_json_path: Path to the input JSON chunks file
        text_processor_configs: Optional list of Paths to processing configuration files
        provider: Optional provider name for generation
        existing_yaml_path: Optional Path to existing YAML to populate

    Returns:
        Path: Path to the generated/populated YAML file
    """
    try:
        # Load and process chunks
        with open(input_json_path, "r", encoding="utf-8") as f:
            chunks = json.load(f)

        # Get processor configs
        generated_text_processor_configs = get_text_processor_configs(
            input_json_path, text_processor_configs
        )
        processor = TextProcessorManager(generated_text_processor_configs)
        processed_chunks = processor.process_chunks(chunks)

        tts_manager = TTSProviderManager(config_data={}, overall_provider=provider)

        # Determine output path and operation
        yaml_output: Path
        if existing_yaml_path:
            # Populate existing YAML
            input_dir = existing_yaml_path.parent
            base_name = existing_yaml_path.stem
            yaml_output = input_dir / f"{base_name}_populated.yaml"

            tts_manager.update_yaml_with_provider_fields_preserving_comments(
                existing_yaml_path,
                yaml_output,
                processed_chunks,
                include_optional_fields,
            )
            logger.info(f"Generated populated YAML configuration: {yaml_output}")
        else:
            # Generate new YAML
            input_dir = input_json_path.parent
            base_name = input_json_path.stem
            yaml_output = input_dir / f"{base_name}_voice_config.yaml"

            tts_manager.generate_yaml_config(
                processed_chunks, yaml_output, provider, include_optional_fields
            )
            logger.info(f"Generated YAML configuration template: {yaml_output}")

        return yaml_output

    except Exception as e:
        operation = "populating" if existing_yaml_path else "generating"
        logger.error(f"Error {operation} YAML configuration: {e}")
        raise


def generate_yaml_config(
    input_json_path: Path,
    processing_configs: Optional[List[Path]] = None,
    provider: Optional[str] = None,
    include_optional_fields: bool = False,
) -> Path:
    """
    Generate a YAML voice configuration template from input JSON chunks.

    Args:
        input_json_path: Path to the input JSON chunks file
        processing_configs: Optional list of Paths to processing configuration files.
                          If not provided, uses default config and any matching chunk config
        provider: Optional provider name to use for generation

    Returns:
        Path: Path to the generated YAML configuration file
    """
    return _handle_yaml_operation(
        input_json_path, processing_configs, provider, None, include_optional_fields
    )


def populate_multi_provider_yaml(
    input_json_path: Path,
    voice_config_yaml_path: Path,
    processing_configs: Optional[List[Path]] = None,
    include_optional_fields: bool = False,
) -> Path:
    """
    Populate provider-specific fields in an existing YAML configuration.

    Args:
        input_json_path: Path to the input JSON chunks file
        voice_config_yaml_path: Path to the YAML configuration to populate
        processing_configs: Optional list of Paths to processing configuration files.
                          If not provided, uses default config and any matching chunk config

    Returns:
        Path: Path to the populated YAML configuration file
    """
    return _handle_yaml_operation(
        input_json_path,
        processing_configs,
        None,
        voice_config_yaml_path,
        include_optional_fields,
    )


def main() -> None:

    sys.argv[0] = "sts-tts-provider-yaml"
    return run_cli()


def run_cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate and populate YAML voice configurations."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Common argument for both commands
    processing_config_arg = "--processing-config"
    processing_config_help = "Optional paths to processing configuration files. Multiple paths can be provided."

    # Generate YAML command
    generate_parser = subparsers.add_parser(
        "generate", help="Generate a YAML voice configuration template"
    )
    generate_parser.add_argument("input_json", help="Path to input JSON chunks file")
    generate_parser.add_argument(
        "--tts-provider", help="Optional TTS provider name for generation"
    )
    generate_parser.add_argument(
        processing_config_arg, nargs="*", help=processing_config_help
    )
    generate_parser.add_argument(
        "--include-optional-fields",
        action="store_true",
        help="Include optional fields in the generated configuration",
    )

    # Populate multi-provider YAML command
    populate_parser = subparsers.add_parser(
        "populate", help="Populate provider-specific fields in existing YAML"
    )
    populate_parser.add_argument("input_json", help="Path to input JSON chunks file")
    populate_parser.add_argument(
        "voice_config", help="Path to YAML configuration to populate"
    )
    populate_parser.add_argument(
        processing_config_arg, nargs="*", help=processing_config_help
    )
    populate_parser.add_argument(
        "--include-optional-fields",
        action="store_true",
        help="Include optional fields in the populated configuration",
    )

    validate_parser = subparsers.add_parser(
        "validate", help="Validate YAML voice config against script"
    )
    validate_parser.add_argument("input_json", help="Path to input JSON chunks file")
    validate_parser.add_argument("voice_config", help="Path to YAML configuration file")
    validate_parser.add_argument(
        processing_config_arg, nargs="*", help=processing_config_help
    )
    validate_parser.add_argument(
        "--strict", action="store_true", help="Validate provider fields"
    )

    args = parser.parse_args()

    # Convert args to Path objects
    input_json_path_obj = Path(args.input_json)
    processing_configs_paths = (
        [Path(p) for p in getattr(args, "processing_config", [])]
        if getattr(args, "processing_config", None)
        else None
    )
    try:
        if args.command == "generate":
            output_path = generate_yaml_config(
                input_json_path_obj,
                processing_configs_paths,
                args.tts_provider,
                args.include_optional_fields,
            )
            print(f"Generated YAML configuration: {output_path}")
        elif args.command == "populate":
            voice_config_path_obj = Path(args.voice_config)
            output_path = populate_multi_provider_yaml(
                input_json_path_obj,
                voice_config_path_obj,
                processing_configs_paths,
                args.include_optional_fields,
            )
            print(f"Generated populated YAML: {output_path}")
        elif args.command == "validate":
            (
                missing_speakers,
                extra_speakers,
                duplicate_speakers,
                invalid_configs,
                statistics,
            ) = validate_yaml_config(
                input_json_path_obj,
                Path(args.voice_config),
                processing_configs_paths,
                args.strict,
            )
            _print_validation_report(
                missing_speakers,
                extra_speakers,
                duplicate_speakers,
                invalid_configs,
                statistics,
            )

            # Exit with error code if any issues were found
            has_issues = any(
                [missing_speakers, extra_speakers, duplicate_speakers, invalid_configs]
            )
            sys.exit(1 if has_issues else 0)
    except Exception as e:
        print(f"Error: {str(e)}")
        exit(1)


def _load_processed_chunks(
    input_json_path: Path, text_processor_configs: Optional[List[Path]]
) -> List[dict]:
    """Load and process chunks from JSON using text processors (DRY helper)."""
    with open(input_json_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    generated_text_processor_configs = get_text_processor_configs(
        input_json_path, text_processor_configs
    )
    processor = TextProcessorManager(generated_text_processor_configs)
    processed_chunks = processor.process_chunks(chunks)
    return processed_chunks


def validate_yaml_config(
    input_json_path: Path,
    voice_config_yaml_path: Path,
    processing_configs: Optional[List[Path]] = None,
    strict: bool = False,
) -> Tuple[List[str], List[str], List[str], dict, VoiceConfigStatistics]:
    """
    Validate that all voices in the script are present in the YAML, no extras, and no duplicates.
    Optionally, validate provider fields for each voice (strict mode).

    Args:
        input_json_path: Path to the input JSON chunks file
        voice_config_yaml_path: Path to the YAML configuration file to validate
        processing_configs: Optional list of processing configuration files
        strict: If True, validate provider-specific fields for each voice

    Returns:
        Tuple of (missing_speakers, extra_speakers, duplicate_speakers, invalid_configs, statistics)
        - missing_speakers: List of speakers in script but not in YAML
        - extra_speakers: List of speakers in YAML but not in script
        - duplicate_speakers: List of speakers with duplicate keys in YAML
        - invalid_configs: Dict mapping speaker names to validation error messages
        - statistics: VoiceConfigStatistics object with comprehensive analysis
    """
    logger.info("=" * 60)
    logger.info("Starting YAML configuration validation")
    logger.info("=" * 60)

    # Extract speakers from processed script chunks
    logger.info("Processing script chunks and extracting speakers...")
    processed_chunks = _load_processed_chunks(input_json_path, processing_configs)
    speakers_in_script = set()

    for chunk in processed_chunks:
        if chunk.get("type") == "dialogue":
            speaker = chunk.get("speaker")
            speakers_in_script.add(speaker if speaker else "default")
        else:
            speakers_in_script.add("default")

    # Load YAML configuration and detect duplicate keys
    logger.info("Loading and validating YAML configuration...")
    yaml_loader = YAML(typ="safe")
    yaml_loader.allow_duplicate_keys = False
    duplicate_speakers: list[str] = []
    yaml_data = None

    try:
        with open(voice_config_yaml_path, "r", encoding="utf-8") as f:
            yaml_data = yaml_loader.load(f)
    except DuplicateKeyError as e:
        # When DuplicateKeyError occurs, we need to manually parse the file to find ALL duplicates
        # since the YAML parser stops at the first duplicate
        duplicate_speakers = []

        # First, extract the duplicate key from the current error
        error_msg = str(e)
        import re

        duplicate_key_match = re.search(r'found duplicate key "([^"]+)"', error_msg)
        if duplicate_key_match:
            duplicate_speakers.append(duplicate_key_match.group(1))

        # Now manually parse the file to find all duplicates
        with open(voice_config_yaml_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        seen_keys = set()
        for line_num, line in enumerate(lines, 1):
            # Look for YAML key patterns at the root level (no leading spaces for top-level keys)
            stripped = line.strip()
            if (
                stripped
                and not stripped.startswith("#")
                and ":" in stripped
                and not line.startswith(" ")
            ):
                # Extract the key part (before the first colon)
                key = stripped.split(":")[0].strip()
                # Remove quotes if present
                key = key.strip("'\"")
                if key and key in seen_keys:
                    if key not in duplicate_speakers:
                        duplicate_speakers.append(key)
                elif key:
                    seen_keys.add(key)

        # Attempt to load YAML again with duplicates allowed to continue validation
        yaml_loader.allow_duplicate_keys = True
        with open(voice_config_yaml_path, "r", encoding="utf-8") as f:
            yaml_data = yaml_loader.load(f)

    if not isinstance(yaml_data, dict):
        raise ValueError(
            "YAML config must be a mapping of speakers to voice configurations."
        )

    speakers_in_yaml = set(yaml_data.keys())

    # Compare speaker sets to find missing and extra speakers
    missing_speakers = sorted(speakers_in_script - speakers_in_yaml)
    extra_speakers = sorted(speakers_in_yaml - speakers_in_script)

    # Strict mode: validate provider-specific configuration fields
    invalid_configs = {}
    if strict:
        from .tts_provider_manager import TTSProviderManager

        for speaker, config in yaml_data.items():
            if not isinstance(config, dict):
                invalid_configs[speaker] = "Configuration must be a mapping/dictionary"
                continue

            provider_name = config.get("provider")
            if not provider_name:
                invalid_configs[speaker] = "Missing required 'provider' field"
                continue

            try:
                provider_class = TTSProviderManager._get_provider_class(provider_name)
                provider_class.validate_speaker_config(config)
            except Exception as validation_error:
                invalid_configs[speaker] = str(validation_error)

    # Generate voice configuration statistics
    logger.info("Generating voice configuration statistics...")
    statistics = generate_voice_config_statistics(processed_chunks, yaml_data)

    return (
        missing_speakers,
        extra_speakers,
        duplicate_speakers,
        invalid_configs,
        statistics,
    )


# CLI integration
def _print_validation_report(
    missing_speakers: list[str],
    extra_speakers: list[str],
    duplicate_speakers: list[str],
    invalid_configs: dict[str, str],
    statistics: VoiceConfigStatistics,
) -> None:
    """Print a formatted validation report showing any issues found."""

    # Always show voice statistics at the beginning
    statistics_report = _format_statistics_report(statistics)
    print(statistics_report)

    print()
    print("=" * 60)
    print("VALIDATION RESULTS")
    print("=" * 60)

    has_issues = any(
        [missing_speakers, extra_speakers, duplicate_speakers, invalid_configs]
    )

    if not has_issues:
        print("✓ Validation successful: no issues found.")
    else:
        print("⚠ Validation completed with issues:")

    if missing_speakers:
        print(f"  • Missing speaker(s) in YAML: {', '.join(missing_speakers)}")

    if extra_speakers:
        print(f"  • Extra speaker(s) in YAML: {', '.join(extra_speakers)}")

    if duplicate_speakers:
        print(f"  • Duplicate speaker(s) in YAML: {', '.join(duplicate_speakers)}")

    if invalid_configs:
        print(f"  • Invalid configuration for {len(invalid_configs)} speaker(s):")
        for speaker, error_message in invalid_configs.items():
            print(f"      {speaker}: {error_message}")
