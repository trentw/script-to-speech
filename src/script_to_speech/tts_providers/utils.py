import json
import logging
from pathlib import Path
from typing import List, Optional, Tuple

from ..text_processors.processor_manager import TextProcessorManager
from ..text_processors.utils import get_processor_configs
from ..utils.logging import get_screenplay_logger
from .tts_provider_manager import TTSProviderManager

logger = get_screenplay_logger("utils.processor")


def _handle_yaml_operation(
    input_json_path: Path,
    processor_configs: Optional[List[Path]] = None,
    provider: Optional[str] = None,
    existing_yaml_path: Optional[Path] = None,
    include_optional_fields: bool = False,
) -> Path:
    """
    Common functionality for YAML generation and population operations.

    Args:
        input_json_path: Path to the input JSON chunks file
        processor_configs: Optional list of Paths to processing configuration files
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
        generated_processor_configs = get_processor_configs(
            input_json_path, processor_configs
        )
        processor = TextProcessorManager(generated_processor_configs)
        processed_chunks = processor.process_chunks(chunks)

        tts_manager = TTSProviderManager(
            config_path=Path(""), overall_provider=provider
        )

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


if __name__ == "__main__":
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
        "--provider", help="Optional provider name for generation"
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

    args = parser.parse_args()

    # Convert args to Path objects
    input_json_path_obj = Path(args.input_json)
    processing_configs_paths = (
        [Path(p) for p in args.processing_config] if args.processing_config else None
    )

    try:
        if args.command == "generate":
            output_path = generate_yaml_config(
                input_json_path_obj,
                processing_configs_paths,
                args.provider,
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

    except Exception as e:
        print(f"Error: {str(e)}")
        exit(1)
