"""Process screenplay files (PDF or TXT) to generate JSON chunks."""

import argparse
import json
import logging
import os
import shutil
from pathlib import Path
from typing import Optional

from ..utils.logging import get_screenplay_logger
from ..utils.optional_config_generation import generate_optional_config

from .screenplay_parser import ScreenplayParser
from .utils.file_utils import (
    create_directory_structure,
    create_output_folders,
    get_project_root,
    sanitize_name,
)
from .utils.logging_utils import setup_parser_logging
from .utils.text_utils import extract_text_preserving_whitespace

logger = get_screenplay_logger("parser.process")


def process_screenplay(
    input_file: str, output_dir: Optional[str] = None, text_only: bool = False
) -> None:
    """Process a screenplay file (PDF or TXT) to generate text and JSON chunks.

    Args:
        input_file: Path to the input file (PDF or TXT)
        output_dir: Optional custom output directory
        text_only: If True, only generate text file without JSON chunks
                  (only applies to PDF input)

    Raises:
        ValueError: If input file type is not supported
        FileNotFoundError: If input file doesn't exist
    """
    # Check if file exists
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input file not found: {input_file}")

    # Get file extension and validate
    file_ext = Path(input_file).suffix.lower()
    if file_ext not in [".pdf", ".txt"]:
        raise ValueError(
            f"Unsupported file type: {file_ext}. Only .pdf and .txt files are supported."
        )

    # Get original and sanitized names
    original_name = Path(input_file).stem
    sanitized_name = sanitize_name(original_name)

    # Create directory structure
    create_directory_structure()

    # Set up output folders and logging
    is_pdf = file_ext == ".pdf"
    run_mode = (
        f"{'pdf' if is_pdf else 'text'}_{'text_only' if text_only else 'full_parse'}"
    )
    screenplay_dir, log_file = create_output_folders(sanitized_name, run_mode)

    # Set up logging with DEBUG for file, INFO for console
    setup_parser_logging(log_file, file_level=logging.DEBUG, console_level=logging.INFO)
    logger.info(f"Starting processing of {input_file}")
    logger.info(f"Sanitized name: {sanitized_name}")

    try:
        # Define output paths
        text_path = Path(screenplay_dir) / f"{sanitized_name}.txt"
        json_path = Path(screenplay_dir) / f"{sanitized_name}.json"

        # Handle PDF input
        if is_pdf:
            pdf_dest = Path(screenplay_dir) / f"{sanitized_name}.pdf"

            # Check if source and destination are different files
            if not os.path.exists(pdf_dest) or not os.path.samefile(
                input_file, pdf_dest
            ):
                # Copy PDF to screenplay directory
                shutil.copy2(input_file, pdf_dest)
                logger.info(f"Copied PDF to {pdf_dest}")
            else:
                logger.info(f"Using existing PDF file: {pdf_dest}")

            # Extract text from PDF
            logger.info("Extracting text from PDF...")
            text = extract_text_preserving_whitespace(str(pdf_dest), str(text_path))
            logger.info(f"Text extracted and saved to {text_path}")

            # Stop here if text_only flag is set
            if text_only:
                logger.info("Text-only mode: skipping JSON generation")
                return

        # Handle TXT input (or continue from PDF)
        else:
            text_dest = Path(screenplay_dir) / f"{sanitized_name}.txt"

            # Copy text file if it's a different file
            if not os.path.exists(text_dest) or not os.path.samefile(
                input_file, text_dest
            ):
                shutil.copy2(input_file, text_dest)
                logger.info(f"Copied text file to {text_dest}")
            else:
                logger.info(f"Using existing text file: {text_dest}")

            # Read text file
            logger.info("Reading text file...")
            with open(text_path, "r", encoding="utf-8") as f:
                text = f.read()

        # Parse text to JSON chunks
        logger.info("Parsing text to JSON chunks...")
        parser = ScreenplayParser()
        chunks = parser.parse_screenplay(text)

        # Save JSON chunks
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)
        logger.info(f"JSON chunks saved to {json_path}")

        # Generate the optional config file
        config_path = generate_optional_config(str(json_path))
        logger.info(f"Optional configuration file: {config_path}")

        logger.info("Processing completed successfully")

    except Exception as e:
        logger.error(f"Error processing screenplay: {str(e)}", exc_info=True)
        raise


def main() -> None:
    """Command-line entry point for processing screenplay files."""
    parser = argparse.ArgumentParser(
        description="Process screenplay files (PDF or TXT) to generate JSON chunks"
    )
    parser.add_argument("input_file", help="Path to input file (PDF or TXT)")
    parser.add_argument("--output-dir", help="Custom output directory")
    parser.add_argument(
        "--text-only",
        action="store_true",
        help="Only generate text file without JSON chunks (PDF only)",
    )

    args = parser.parse_args()

    try:
        process_screenplay(args.input_file, args.output_dir, args.text_only)
    except Exception as e:
        print(f"Error: {str(e)}")
        exit(1)


if __name__ == "__main__":
    main()
