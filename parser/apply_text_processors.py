"""Apply text processors to screenplay JSON chunks."""

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from text_processors.processor_manager import TextProcessorManager
from text_processors.utils import get_processor_configs
from utils.logging import get_screenplay_logger

from .analyze import analyze_chunks
from .utils.file_utils import get_project_root, sanitize_name
from .utils.logging_utils import setup_parser_logging

logger = get_screenplay_logger("parser.apply_text_processors")


def apply_text_processors(
    json_path: str,
    processor_configs: Optional[List[str]] = None,
    output_path: Optional[str] = None,
) -> None:
    """Process an existing JSON chunks file through text processors.

    Args:
        json_path: Path to input JSON chunks file
        processor_configs: Optional path to processor configuration files.
                         If not provided, uses DEFAULT_PROCESSING_CONFIG from text_processors.utils and
                         [file name]_processor_config.yaml if it exists
        output_path: Optional path for output file. If not provided, will use
                    output/[json_name]/[json_name]-modified.json
    """
    try:
        # Set up logging
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_dir = Path("parser/logs")
        log_dir.mkdir(parents=True, exist_ok=True)

        # Get original and sanitized names
        original_name = Path(json_path).stem
        sanitized_name = sanitize_name(original_name)
        log_file = log_dir / f"[apply_processors]_{sanitized_name}_{timestamp}.log"

        setup_parser_logging(
            str(log_file), file_level=logging.DEBUG, console_level=logging.INFO
        )
        logger.info(f"Starting processing of {json_path}")

        # Load JSON chunks
        with open(json_path, "r", encoding="utf-8") as f:
            chunks = json.load(f)

        # Get processor configs
        generated_processor_configs = get_processor_configs(
            json_path, processor_configs
        )

        # Initialize text processor manager
        processor = TextProcessorManager(generated_processor_configs)
        logger.info(
            f"Text processor manager initialized with configs: {generated_processor_configs}"
        )

        # Process chunks
        modified_chunks = processor.process_chunks(chunks)

        # Determine output path if not provided
        if not output_path:
            input_path = Path(json_path)
            base_name = input_path.stem
            root = get_project_root()

            # Create output structure
            output_dir = root / "output" / base_name
            output_dir.mkdir(parents=True, exist_ok=True)

            output_path = output_dir / f"{base_name}-modified.json"

        # Save modified chunks
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(modified_chunks, f, ensure_ascii=False, indent=2)

        logger.info(f"Modified chunks saved to {output_path}")

        # Analyze the processed chunks
        analyze_chunks(modified_chunks)

    except Exception as e:
        logger.error(f"Error processing chunks: {str(e)}", exc_info=True)
        raise


def main():
    """Command-line entry point for applying text processors to JSON chunks."""
    parser = argparse.ArgumentParser(
        description="Apply text processors to screenplay JSON chunks"
    )
    parser.add_argument("json_file", help="Path to JSON chunks file")
    parser.add_argument(
        "--processor-configs",
        nargs="*",
        help="Path(s) to text (pre)processor configuration file(s). "
        "Multiple paths can be provided.",
    )
    parser.add_argument("--output-path", help="Custom output path for modified chunks")

    args = parser.parse_args()

    try:
        apply_text_processors(args.json_file, args.processor_configs, args.output_path)
    except Exception as e:
        print(f"Error: {str(e)}")
        exit(1)


if __name__ == "__main__":
    main()
