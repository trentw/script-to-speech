import json
import logging
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from ruamel.yaml import YAML
from ruamel.yaml.constructor import DuplicateKeyError

from ..text_processors.processor_manager import TextProcessorManager
from ..text_processors.utils import get_text_processor_configs
from ..utils.logging import get_screenplay_logger
from .tts_provider_manager import TTSProviderManager

logger = get_screenplay_logger("utils.processor")


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
            missing_speakers, extra_speakers, duplicate_speakers, invalid_configs = (
                validate_yaml_config(
                    input_json_path_obj,
                    Path(args.voice_config),
                    processing_configs_paths,
                    args.strict,
                )
            )
            _print_validation_report(
                missing_speakers, extra_speakers, duplicate_speakers, invalid_configs
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
) -> Tuple[List[str], List[str], List[str], dict]:
    """
    Validate that all voices in the script are present in the YAML, no extras, and no duplicates.
    Optionally, validate provider fields for each voice (strict mode).

    Args:
        input_json_path: Path to the input JSON chunks file
        voice_config_yaml_path: Path to the YAML configuration file to validate
        processing_configs: Optional list of processing configuration files
        strict: If True, validate provider-specific fields for each voice

    Returns:
        Tuple of (missing_speakers, extra_speakers, duplicate_speakers, invalid_configs)
        - missing_speakers: List of speakers in script but not in YAML
        - extra_speakers: List of speakers in YAML but not in script
        - duplicate_speakers: List of speakers with duplicate keys in YAML
        - invalid_configs: Dict mapping speaker names to validation error messages
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

    return missing_speakers, extra_speakers, duplicate_speakers, invalid_configs


# CLI integration
def _print_validation_report(
    missing_speakers: list[str],
    extra_speakers: list[str],
    duplicate_speakers: list[str],
    invalid_configs: dict[str, str],
) -> None:
    """Print a formatted validation report showing any issues found."""
    print()
    print("=" * 60)
    print("VALIDATION RESULTS")
    print("=" * 60)

    has_issues = any(
        [missing_speakers, extra_speakers, duplicate_speakers, invalid_configs]
    )

    if not has_issues:
        print("✓ Validation successful: no issues found.")
        return

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
