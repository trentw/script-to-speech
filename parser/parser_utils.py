import os
import shutil
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
import logging
from typing import Optional, Tuple, List
from text_processors.processor_manager import TextProcessorManager
from text_processors.utils import get_processor_configs

from utils.logging import setup_screenplay_logging, get_screenplay_logger
from .screenplay_parser import ScreenplayParser
import json


logger = get_screenplay_logger("parser.utils")


def extract_text_preserving_whitespace(pdf_path: str, output_file: str) -> str:
    """Extract text from PDF while preserving whitespace and normalizing characters."""
    import pdfplumber
    from unidecode import unidecode

    with pdfplumber.open(pdf_path) as pdf:
        text = ""
        for page in pdf.pages:
            # Extract text with layout preservation
            page_text = page.dedupe_chars().extract_text(
                x_tolerance=1,
                y_tolerance=1,
                layout=True
            )
            # Convert to ASCII representation while preserving whitespace
            page_text = unidecode(page_text)
            text += page_text

    # Write the normalized text to the output file
    with open(output_file, 'w', encoding='utf-8') as file:
        file.write(text)

    return text


def sanitize_name(name: str) -> str:
    """
    Sanitize a name for use in filenames and directories.

    Args:
        name: Original name

    Returns:
        Sanitized name with special characters removed and spaces replaced with underscores
    """
    # Remove or replace special characters
    # First, handle common punctuation and special characters
    sanitized = re.sub(r'[^\w\s-]', '', name)
    # Replace spaces and repeated dashes/underscores with single underscore
    sanitized = re.sub(r'[-\s]+', '_', sanitized)
    # Remove leading/trailing underscores
    sanitized = sanitized.strip('_')
    return sanitized


def get_project_root() -> Path:
    """
    Get the project root directory (where input, parser, etc. directories live).
    Assumes this script is in the parser directory.

    Returns:
        Path to project root directory
    """
    # Since this script is in the parser directory, go up one level
    return Path(__file__).resolve().parent.parent


def create_directory_structure() -> None:
    """Create the necessary directory structure relative to project root."""
    root = get_project_root()
    required_dirs = [
        root / 'input',
        root / 'parser' / 'logs'
    ]

    for dir_path in required_dirs:
        dir_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Ensured directory exists: {dir_path}")


def analyze_screenplay_chunks(json_path: str) -> None:
    """
    Analyze a screenplay chunks JSON file and output statistics.

    Args:
        json_path: Path to the JSON chunks file
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            chunks = json.load(f)
        analyze_chunks(chunks)
    except Exception as e:
        logger.error(
            f"Error analyzing screenplay chunks: {str(e)}", exc_info=True)
        raise


def analyze_chunks(chunks: list) -> None:
    """
    Analyze screenplay chunks and log statistics.

    Args:
        chunks: List of screenplay chunks
    """
    # Count chunk types
    chunk_type_counts = {}
    speaker_counts = {}
    speakers = set()

    for chunk in chunks:
        # Count chunk types
        chunk_type = chunk['type']
        chunk_type_counts[chunk_type] = chunk_type_counts.get(
            chunk_type, 0) + 1

        # Track speakers
        if chunk_type == 'dialog':
            # For dialog, use the specified speaker or default
            speaker = chunk.get('speaker', '') or '(default)'
        else:
            # For non-dialog chunks, always attribute to default
            speaker = '(default)'

        speakers.add(speaker)
        speaker_counts[speaker] = speaker_counts.get(speaker, 0) + 1

    # Log results
    logger.info("\n###########################")
    logger.info("### Screenplay Analysis ###")
    logger.info("###########################")

    # Chunk type counts
    logger.info("\nChunk Type Counts:")
    for chunk_type, count in sorted(chunk_type_counts.items()):
        logger.info(f"  {chunk_type}: {count}")

    # Speaker statistics
    logger.info(f"\nTotal Distinct Speakers:\n  {len(speakers)}")

    logger.info("\nSpeaker Line Counts:")
    for speaker, count in sorted(speaker_counts.items(), key=lambda x: (-x[1], x[0])):
        logger.info(f"  {speaker}: {count}")


def create_output_folders(screenplay_name: str, run_mode: str = "") -> Tuple[str, str]:
    """
    Create and return paths for output folders following the standard structure.

    Args:
        screenplay_name: Name of the screenplay
        run_mode: String indicating run mode for log file name prefix

    Returns:
        Tuple of (screenplay_directory, log_file)
    """
    root = get_project_root()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create screenplay directory in input folder
    screenplay_dir = root / 'input' / screenplay_name
    screenplay_dir.mkdir(parents=True, exist_ok=True)

    # Create log path
    mode_prefix = f"[{run_mode}]_" if run_mode else ""
    log_file = root / 'parser' / 'logs' / \
        f"{mode_prefix}{screenplay_name}_{timestamp}.log"

    return str(screenplay_dir), str(log_file)


def process_json_chunks(
    json_path: str,
    processor_configs: Optional[List[str]] = None,
    output_path: Optional[str] = None
) -> None:
    """
    Process an existing JSON chunks file through text processors.

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
        log_dir = Path('parser/logs')
        log_dir.mkdir(parents=True, exist_ok=True)
        # Get original and sanitized names
        original_name = Path(json_path).stem
        sanitized_name = sanitize_name(original_name)
        log_file = log_dir / \
            f"[process_chunks]_{sanitized_name}_{timestamp}.log"

        setup_screenplay_logging(
            str(log_file), file_level=logging.DEBUG, console_level=logging.INFO)
        logger.info(f"Starting processing of {json_path}")

        # Load JSON chunks
        with open(json_path, 'r', encoding='utf-8') as f:
            chunks = json.load(f)

        # Get processor configs
        generated_processor_configs = get_processor_configs(
            json_path, processor_configs)

        # Initialize text processor manager
        processor = TextProcessorManager(generated_processor_configs)
        logger.info(
            f"Text processor manager initialized with configs: {generated_processor_configs}")

        # Process chunks
        modified_chunks = processor.process_chunks(chunks)

        # Determine output path if not provided
        if not output_path:
            input_path = Path(json_path)
            base_name = input_path.stem
            root = get_project_root()

            # Create output structure
            output_dir = root / 'output' / base_name
            output_dir.mkdir(parents=True, exist_ok=True)

            output_path = output_dir / f"{base_name}-modified.json"

        # Save modified chunks
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(modified_chunks, f, ensure_ascii=False, indent=2)

        logger.info(f"Modified chunks saved to {output_path}")

        # Analyze the processed chunks
        analyze_chunks(modified_chunks)

    except Exception as e:
        logger.error(f"Error processing chunks: {str(e)}", exc_info=True)
        raise


def process_screenplay(
    input_file: str,
    output_dir: Optional[str] = None,
    text_only: bool = False
) -> None:
    """
    Process a screenplay file (PDF or TXT) to generate text and optionally JSON chunks.

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
    if file_ext not in ['.pdf', '.txt']:
        raise ValueError(
            f"Unsupported file type: {file_ext}. Only .pdf and .txt files are supported.")

    # Get original and sanitized names
    original_name = Path(input_file).stem
    sanitized_name = sanitize_name(original_name)

    # Create directory structure
    create_directory_structure()

    # Set up output folders and logging
    is_pdf = file_ext == '.pdf'
    run_mode = f"{'pdf' if is_pdf else 'text'}_{'text_only' if text_only else 'full_parse'}"
    screenplay_dir, log_file = create_output_folders(sanitized_name, run_mode)

    # Set up logging with DEBUG for file, INFO for console
    setup_screenplay_logging(
        log_file, file_level=logging.DEBUG, console_level=logging.INFO)
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
            if not os.path.exists(pdf_dest) or not os.path.samefile(input_file, pdf_dest):
                # Copy PDF to screenplay directory
                shutil.copy2(input_file, pdf_dest)
                logger.info(f"Copied PDF to {pdf_dest}")
            else:
                logger.info(f"Using existing PDF file: {pdf_dest}")

            # Extract text from PDF
            logger.info("Extracting text from PDF...")
            text = extract_text_preserving_whitespace(
                str(pdf_dest), str(text_path))
            logger.info(f"Text extracted and saved to {text_path}")

            # Stop here if text_only flag is set
            if text_only:
                logger.info("Text-only mode: skipping JSON generation")
                return

        # Handle TXT input (or continue from PDF)
        else:
            text_dest = Path(screenplay_dir) / f"{sanitized_name}.txt"

            # Copy text file if it's a different file
            if not os.path.exists(text_dest) or not os.path.samefile(input_file, text_dest):
                shutil.copy2(input_file, text_dest)
                logger.info(f"Copied text file to {text_dest}")
            else:
                logger.info(f"Using existing text file: {text_dest}")

            # Read text file
            logger.info("Reading text file...")
            with open(text_path, 'r', encoding='utf-8') as f:
                text = f.read()

        # Parse text to JSON chunks
        logger.info("Parsing text to JSON chunks...")
        parser = ScreenplayParser()
        chunks = parser.parse_screenplay(text)

        # Save JSON chunks
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)
        logger.info(f"JSON chunks saved to {json_path}")

        # Analyze the chunks
        analyze_chunks(chunks)

        logger.info("Processing completed successfully")

    except Exception as e:
        logger.error(f"Error processing screenplay: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description='Process and analyze screenplay files.')
    subparsers = parser.add_subparsers(dest='command', required=True)

    # Process command
    process_parser = subparsers.add_parser('process',
                                           help='Process screenplay files (PDF or TXT) to generate JSON chunks')
    process_parser.add_argument(
        'input_file', help='Path to input file (PDF or TXT)')
    process_parser.add_argument('--output-dir', help='Custom output directory')
    process_parser.add_argument('--text-only', action='store_true',
                                help='Only generate text file without JSON chunks (PDF only)')

    # Analyze command
    analyze_parser = subparsers.add_parser('analyze',
                                           help='Analyze an existing screenplay JSON chunks file')
    analyze_parser.add_argument('json_file', help='Path to JSON chunks file')

    # Process JSON command
    process_json_parser = subparsers.add_parser('process-json',
                                                help='Process existing JSON chunks through preprocessors and processors')
    process_json_parser.add_argument(
        'json_file', help='Path to JSON chunks file')
    process_json_parser.add_argument('--processor-configs', nargs='*',
                                     help='Path(s) to text (pre)processor configuration file(s). '
                                          'Multiple paths can be provided.')
    process_json_parser.add_argument('--output-path',
                                     help='Custom output path for modified chunks')

    args = parser.parse_args()

    try:
        if args.command == 'process':
            process_screenplay(
                args.input_file, args.output_dir, args.text_only)
        elif args.command == 'analyze':
            analyze_screenplay_chunks(args.json_file)
        elif args.command == 'process-json':
            process_json_chunks(
                args.json_file, args.processor_configs, args.output_path)
    except Exception as e:
        print(f"Error: {str(e)}")
        exit(1)
