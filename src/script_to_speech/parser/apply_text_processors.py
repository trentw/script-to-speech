"""Apply text processors to screenplay JSON chunks."""

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from ..text_processors.processor_manager import TextProcessorManager
from ..text_processors.utils import get_text_processor_configs
from ..utils.file_system_utils import create_output_folders
from ..utils.logging import get_screenplay_logger
from .analyze import analyze_chunks
from .utils.logging_utils import setup_parser_logging

logger = get_screenplay_logger("parser.apply_text_processors")


def apply_text_processors(
    json_path: Path,
    text_processor_configs: Optional[List[Path]] = None,
    output_path: Optional[Path] = None,
) -> None:
    """Process an existing JSON chunks file through text processors.

    Args:
        json_path: Path to input JSON chunks file
        text_processor_configs: Optional list of Paths to processor configuration files.
                         If not provided, uses DEFAULT_PROCESSING_CONFIG from text_processors.utils and
                         [file name]_text_processor_config.yaml if it exists
        output_path: Optional Path for output file. If not provided, will use
                    output/[json_name]/[json_name]-text-processed.json
    """
    try:

        # Get original name
        original_name = json_path.stem

        # Use the unified create_output_folders function
        main_output_folder, _, _, log_file = create_output_folders(
            str(json_path), run_mode="apply_processors"
        )

        setup_parser_logging(
            str(log_file), file_level=logging.DEBUG, console_level=logging.INFO
        )
        logger.info(f"Starting processing of {json_path}")

        # Load JSON chunks
        with open(json_path, "r", encoding="utf-8") as f:
            chunks = json.load(f)

        # Get processor configs
        generated_text_processor_configs = get_text_processor_configs(
            json_path, text_processor_configs
        )

        # Initialize text processor manager
        processor = TextProcessorManager(generated_text_processor_configs)
        logger.info(
            f"Text processor manager initialized with configs: {[str(p) for p in generated_text_processor_configs]}"  # Log as strings
        )

        # Process chunks
        modified_chunks = processor.process_chunks(chunks)

        # Determine output path if not provided
        output_path_resolved: Path
        if not output_path:
            # Use the main output folder from create_output_folders
            output_path_resolved = (
                main_output_folder / f"{original_name}-text-processed.json"
            )
        else:
            output_path_resolved = output_path

        # Save modified chunks
        with open(output_path_resolved, "w", encoding="utf-8") as f:
            json.dump(modified_chunks, f, ensure_ascii=False, indent=2)

        logger.info(f"Modified chunks saved to {output_path_resolved}")

        # Analyze the processed chunks
        analyze_chunks(modified_chunks)

    except Exception as e:
        logger.error(f"Error processing chunks: {str(e)}", exc_info=True)
        raise


def main() -> None:
    """Command-line entry point for applying text processors to JSON chunks."""
    parser = argparse.ArgumentParser(
        description="Apply text processors to screenplay JSON chunks"
    )
    parser.add_argument("json_file", help="Path to JSON chunks file")
    parser.add_argument(
        "--text-processor-configs",
        nargs="*",
        help="Path(s) to text (pre)processor configuration file(s). "
        "Multiple paths can be provided.",
    )
    parser.add_argument("--output-path", help="Custom output path for modified chunks")

    args = parser.parse_args()

    # Convert args to Path objects before calling
    json_file_path = Path(args.json_file)
    text_processor_configs_paths = (
        [Path(p) for p in args.text_processor_configs]
        if args.text_processor_configs
        else None
    )
    output_path_obj = Path(args.output_path) if args.output_path else None

    try:
        apply_text_processors(
            json_file_path, text_processor_configs_paths, output_path_obj
        )
    except Exception as e:
        print(f"Error: {str(e)}")
        exit(1)


if __name__ == "__main__":
    main()
