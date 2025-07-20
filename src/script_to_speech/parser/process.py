"""Process screenplay files (PDF or TXT) to generate JSON chunks."""

import argparse
import json
import logging
import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional

from pathvalidate import sanitize_filename

from ..utils.file_system_utils import (
    create_output_folders,
    sanitize_name,
    PathSecurityValidator,
)
from ..utils.logging import get_screenplay_logger
from ..utils.optional_config_generation import generate_optional_config
from .analyze import analyze_chunks
from .screenplay_parser import ScreenplayParser
from .utils.logging_utils import setup_parser_logging
from .utils.text_utils import extract_text_preserving_whitespace

logger = get_screenplay_logger("parser.process")


def process_screenplay(
    input_file: str, base_path: Optional[Path] = None, text_only: bool = False
) -> Dict[str, Any]:
    """Process a screenplay file (PDF or TXT) to generate text and JSON chunks.

    Args:
        input_file: Path to the input file (PDF or TXT)
        base_path: Base directory for all operations. If None, uses current working directory
        text_only: If True, only generate text file without JSON chunks
                  (only applies to PDF input)

    Returns:
        Dictionary containing processing results with file paths and metadata

    Raises:
        ValueError: If input file type is not supported
        FileNotFoundError: If input file doesn't exist
    """
    # Auto-detect base path if not provided (backward compatibility)
    if base_path is None:
        base_path = Path.cwd().resolve()

    # Initialize security validator
    validator = PathSecurityValidator(base_path)

    # Check if file exists
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input file not found: {input_file}")

    # Get file extension and validate
    file_ext = Path(input_file).suffix.lower()
    if file_ext not in [".pdf", ".txt"]:
        raise ValueError(
            f"Unsupported file type: {file_ext}. Only .pdf and .txt files are supported."
        )

    # Get original and sanitized names using pathvalidate
    original_name = Path(input_file).stem
    sanitized_name = sanitize_filename(original_name)

    # Set up output folders and logging
    is_pdf = file_ext == ".pdf"
    run_mode = (
        f"{'pdf' if is_pdf else 'text'}_{'text_only' if text_only else 'full_parse'}"
    )

    # Use the unified create_output_folders function with base_path
    main_output_folder, cache_folder, logs_folder, log_file = create_output_folders(
        input_file, run_mode, base_path=base_path
    )

    # Create screenplay directory in input folder using security validator
    screenplay_dir = validator.validate_and_join("input", sanitized_name)
    screenplay_dir.mkdir(parents=True, exist_ok=True)

    # Set up logging with DEBUG for file, INFO for console
    setup_parser_logging(
        str(log_file), file_level=logging.DEBUG, console_level=logging.INFO
    )
    logger.info(f"Starting processing of {input_file}")
    logger.info(f"Sanitized name: {sanitized_name}")

    try:
        # Define output paths using security validator
        text_path = validator.validate_and_join(
            "input", sanitized_name, f"{sanitized_name}.txt"
        )
        json_path = validator.validate_and_join(
            "input", sanitized_name, f"{sanitized_name}.json"
        )

        # Handle PDF input
        if is_pdf:
            pdf_dest = validator.validate_and_join(
                "input", sanitized_name, f"{sanitized_name}.pdf"
            )

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
                return {
                    "status": "success",
                    "output_dir": str(screenplay_dir),
                    "files": {
                        "original": str(Path(input_file).resolve()),
                        "text": str(text_path) if text_path.exists() else None,
                        "json": None,
                        "config": None,
                    },
                    "screenplay_name": sanitized_name,
                    "text_only": True,
                    "analysis": None,
                }

        # Handle TXT input (or continue from PDF)
        else:
            text_dest = validator.validate_and_join(
                "input", sanitized_name, f"{sanitized_name}.txt"
            )

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

        # Analyze the chunks for metadata
        analysis = analyze_chunks(chunks, log_results=False)

        logger.info("Processing completed successfully")

        # Return structured data
        return {
            "status": "success",
            "output_dir": str(screenplay_dir),
            "files": {
                "original": str(Path(input_file).resolve()),
                "text": str(text_path) if text_path.exists() else None,
                "json": str(json_path) if json_path.exists() else None,
                "config": str(Path(config_path)) if config_path else None,
            },
            "screenplay_name": sanitized_name,
            "text_only": False,
            "analysis": analysis,
        }

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
        result = process_screenplay(args.input_file, None, args.text_only)
        # CLI just prints success message, structured data is used by API
        print(f"Processing completed successfully. Output in: {result['output_dir']}")
    except Exception as e:
        print(f"Error: {str(e)}")
        exit(1)


if __name__ == "__main__":
    main()
