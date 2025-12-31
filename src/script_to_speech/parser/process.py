"""Process screenplay files (PDF or TXT) to generate JSON chunks."""

import argparse
import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pathvalidate import sanitize_filename

from ..utils.file_system_utils import (
    PathSecurityValidator,
    create_output_folders,
    sanitize_name,
)
from ..utils.logging import get_screenplay_logger
from ..utils.optional_config_generation import generate_optional_config
from .analyze import analyze_chunks
from .constants import DEFAULT_LINES_TO_SCAN
from .screenplay_parser import ScreenplayParser
from .utils.logging_utils import setup_parser_logging
from .utils.text_utils import (
    extract_text_by_page,
    extract_text_preserving_whitespace,
    get_header_footer_line_indices,
)

logger = get_screenplay_logger("parser.process")


def _build_removal_metadata(pattern_counts: Dict[str, int]) -> Dict[str, Any]:
    """Build standard removal metadata dict.

    Args:
        pattern_counts: Dict mapping each pattern to its removal count

    Returns:
        Standard metadata dict with patterns_removed, total_removals, per_pattern_counts
    """
    return {
        "patterns_removed": list(pattern_counts.keys()),
        "total_removals": sum(pattern_counts.values()),
        "per_pattern_counts": pattern_counts,
    }


def _replace_pattern_with_spaces(text: str, pattern: str) -> Tuple[str, int]:
    """Replace all occurrences of pattern with equal-length spaces.

    Args:
        text: Input text to process
        pattern: String to replace with spaces

    Returns:
        Tuple of (modified_text, occurrence_count)
    """
    count = text.count(pattern)
    if count > 0:
        return text.replace(pattern, " " * len(pattern)), count
    return text, 0


def remove_strings_preserve_layout(
    text: str,
    patterns: List[str],
) -> Tuple[str, Dict[str, Any]]:
    """Replace patterns with equal-length spaces to preserve layout.

    This function replaces specified strings with an equal number of spaces,
    maintaining the monospace layout that is critical for screenplay parsing.

    Args:
        text: Input text to process
        patterns: List of strings to replace with spaces

    Returns:
        Tuple of (cleaned_text, metadata_dict) where metadata contains:
            - patterns_removed: List of patterns that were actually found and removed
            - total_removals: Total number of replacements made
            - per_pattern_counts: Dict mapping each pattern to its removal count
    """
    cleaned = text
    pattern_counts: Dict[str, int] = {}

    for pattern in patterns:
        if not pattern:  # Skip empty patterns
            continue
        cleaned, count = _replace_pattern_with_spaces(cleaned, pattern)
        if count > 0:
            pattern_counts[pattern] = count

    return cleaned, _build_removal_metadata(pattern_counts)


def remove_from_header_footer_positions(
    pdf_path: str,
    patterns: List[str],
    lines_to_scan: int = DEFAULT_LINES_TO_SCAN,
) -> Tuple[str, Dict[str, Any]]:
    """Remove patterns only from first/last N non-blank lines of each page.

    This function restricts pattern removal to header/footer positions,
    preventing accidental removal of patterns that appear in dialogue.

    Args:
        pdf_path: Path to the PDF file
        patterns: List of strings to replace with spaces
        lines_to_scan: Number of non-blank lines to scan from top/bottom of each page

    Returns:
        Tuple of (cleaned_text, metadata_dict) where metadata contains:
            - patterns_removed: List of patterns that were actually found and removed
            - total_removals: Total number of replacements made
            - per_pattern_counts: Dict mapping each pattern to its removal count
    """
    pages = extract_text_by_page(pdf_path)
    result_pages = []
    pattern_counts: Dict[str, int] = {}

    for page in pages:
        lines = page.text.split("\n")

        # Use shared utility to identify header/footer line indices
        header_indices, footer_indices = get_header_footer_line_indices(
            lines, lines_to_scan
        )
        target_indices = header_indices | footer_indices
        for i in target_indices:
            for pattern in patterns:
                if pattern:
                    lines[i], count = _replace_pattern_with_spaces(lines[i], pattern)
                    if count > 0:
                        pattern_counts[pattern] = pattern_counts.get(pattern, 0) + count

        result_pages.append("\n".join(lines))

    # Join pages with no separator (matching extract_text_preserving_whitespace)
    cleaned_text = "".join(result_pages)

    return cleaned_text, _build_removal_metadata(pattern_counts)


def _apply_string_removal(
    text: str,
    patterns: List[str],
    pdf_path: Optional[str],
    remove_lines: int,
    text_path: Path,
) -> Tuple[str, Dict[str, Any]]:
    """Apply string removal and write result to file.

    Args:
        text: Input text to process
        patterns: List of patterns to remove
        pdf_path: Path to PDF (for position-restricted removal), or None
        remove_lines: Lines to scan (0 for global replacement)
        text_path: Path to write cleaned text

    Returns:
        Tuple of (cleaned_text, removal_metadata)
    """
    if pdf_path and remove_lines > 0:
        cleaned, metadata = remove_from_header_footer_positions(
            pdf_path, patterns, remove_lines
        )
        logger.info(
            f"Removed {metadata['total_removals']} pattern occurrences "
            f"from header/footer positions ({remove_lines} lines each)"
        )
    else:
        cleaned, metadata = remove_strings_preserve_layout(text, patterns)
        logger.info(
            f"Removed {metadata['total_removals']} pattern occurrences "
            f"(global replacement)"
        )

    with open(text_path, "w", encoding="utf-8") as f:
        f.write(cleaned)
    logger.info(f"Updated text file with patterns removed: {text_path}")

    return cleaned, metadata


def process_screenplay(
    input_file: str,
    base_path: Optional[Path] = None,
    text_only: bool = False,
    strings_to_remove: Optional[List[str]] = None,
    remove_lines: int = DEFAULT_LINES_TO_SCAN,
) -> Dict[str, Any]:
    """Process a screenplay file (PDF or TXT) to generate text and JSON chunks.

    Args:
        input_file: Path to the input file (PDF or TXT)
        base_path: Base directory for all operations. If None, uses current working directory
        text_only: If True, only generate text file without JSON chunks
                  (only applies to PDF input)
        strings_to_remove: Optional list of strings to replace with spaces before parsing.
                          Each string is replaced with an equal number of spaces to
                          preserve the monospace layout. Use sts-detect-headers to
                          find header/footer patterns to remove.
        remove_lines: Number of lines from top/bottom of each page to apply removal to.
                     Default is DEFAULT_LINES_TO_SCAN. Use 0 for global replacement.
                     Only applies to PDF files; TXT files always use global replacement.

    Returns:
        Dictionary containing processing results with file paths and metadata.
        If strings_to_remove is provided, includes 'removal_metadata' with
        counts of patterns removed.

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
        # Track removal metadata and PDF path for position-restricted removal
        removal_metadata: Optional[Dict[str, Any]] = None
        pdf_dest: Optional[Path] = None

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

        # Handle TXT input
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

        # Apply string removal if requested (unified for all paths)
        if strings_to_remove:
            text, removal_metadata = _apply_string_removal(
                text,
                strings_to_remove,
                str(pdf_dest) if pdf_dest else None,
                remove_lines,
                text_path,
            )

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
                "removal_metadata": removal_metadata,
            }

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
            "removal_metadata": removal_metadata,
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
    parser.add_argument(
        "--remove",
        action="append",
        metavar="STRING",
        help="String to remove from text before parsing (can be used multiple times). "
        "Each string is replaced with equal-length spaces to preserve layout. "
        "Use sts-detect-headers to find header/footer patterns.",
    )
    parser.add_argument(
        "--remove-lines",
        type=int,
        default=DEFAULT_LINES_TO_SCAN,
        metavar="N",
        help=f"Lines to scan from top/bottom of each page for --remove (default: {DEFAULT_LINES_TO_SCAN}). "
        "Use 0 for global replacement. Only applies to PDF files.",
    )

    args = parser.parse_args()

    try:
        result = process_screenplay(
            args.input_file,
            None,
            args.text_only,
            strings_to_remove=args.remove,
            remove_lines=args.remove_lines,
        )
        # CLI just prints success message, structured data is used by API
        print(f"Processing completed successfully. Output in: {result['output_dir']}")
        if result.get("removal_metadata"):
            meta = result["removal_metadata"]
            print(
                f"Removed {meta['total_removals']} occurrences of "
                f"{len(meta['patterns_removed'])} pattern(s)"
            )
    except Exception as e:
        print(f"Error: {str(e)}")
        exit(1)


if __name__ == "__main__":
    main()
