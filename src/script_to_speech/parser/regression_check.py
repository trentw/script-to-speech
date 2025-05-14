"""
Regression checker for screenplay parser.

This tool compares the chunks produced by the current parser with chunks from an existing JSON file.
It helps identify changes in parsing behavior that might affect existing functionality.
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..utils.file_system_utils import create_output_folders
from ..utils.logging import get_screenplay_logger
from .screenplay_parser import ScreenplayParser
from .utils.logging_utils import setup_parser_logging

logger = get_screenplay_logger("parser.regression_check")


def setup_logging(input_file_name: str) -> str:
    """Set up logging for the regression checker.

    Args:
        input_file_name: Name of the input file

    Returns:
        Path to the log file
    """
    # Use the unified create_output_folders function
    _, _, _, log_file = create_output_folders(
        input_file_name, run_mode="regressioncheck"
    )

    setup_parser_logging(
        str(log_file), file_level=logging.DEBUG, console_level=logging.INFO
    )

    return str(log_file)


def load_json_chunks(file_path: str) -> List[Dict[str, Any]]:
    """Load chunks from a JSON file.

    Args:
        file_path: Path to the JSON file

    Returns:
        List of chunks
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            result: List[Dict[str, Any]] = json.load(f)
            return result
    except Exception as e:
        logger.error(f"Error loading JSON file: {str(e)}")
        raise


def get_chunk_snippet(chunk: Dict[str, Any], max_length: int = 30) -> str:
    """Get a text snippet from a chunk for identification.

    Args:
        chunk: The chunk to extract text from
        max_length: Maximum length of the snippet

    Returns:
        A short text snippet
    """
    text = chunk.get("text", "")
    if not text:
        text = chunk.get("raw_text", "")[:max_length]

    # Truncate if needed and add ellipsis
    if len(text) > max_length:
        result: str = f"{text[:max_length]}..."
        return result
    return str(text)


def get_first_line(chunk: Dict[str, Any]) -> str:
    """Get the first line of raw_text from a chunk.

    Args:
        chunk: The chunk to extract the first line from

    Returns:
        The first line of raw_text
    """
    raw_text: str = chunk.get("raw_text", "")
    lines = raw_text.split("\n")
    result: str = lines[0] if lines else ""
    return result


def compare_chunks(chunk1: Dict[str, Any], chunk2: Dict[str, Any]) -> List[str]:
    """Compare two chunks and return a list of differences.

    Args:
        chunk1: First chunk
        chunk2: Second chunk

    Returns:
        List of differences
    """
    differences = []

    if chunk1["type"] != chunk2["type"]:
        differences.append(f"Type: {chunk1['type']} -> {chunk2['type']}")

    if chunk1["speaker"] != chunk2["speaker"]:
        differences.append(f"Speaker: {chunk1['speaker']} -> {chunk2['speaker']}")

    if chunk1["text"] != chunk2["text"]:
        differences.append(f"Text differs")

    return differences


def find_chunk_with_line(chunks: List[Dict[str, Any]], line: str) -> int:
    """Find a chunk that contains the given line in its raw_text.

    Args:
        chunks: List of chunks to search
        line: Line to search for

    Returns:
        Index of the chunk containing the line, or -1 if not found
    """
    for i, chunk in enumerate(chunks):
        raw_text = chunk.get("raw_text", "")
        if line in raw_text:
            return i
    return -1


def process_chunks(
    input_chunks: List[Dict[str, Any]], parser: ScreenplayParser
) -> List[Dict[str, Any]]:
    """Process input chunks and generate parser chunks.

    Args:
        input_chunks: Input chunks from JSON file
        parser: ScreenplayParser instance

    Returns:
        List of parser-generated chunks
    """
    logger.info("Processing chunks using incremental parsing...")

    # Reset parser state
    parser.reset_parser_state()

    # Initialize arrays
    parser_chunks = []

    # Process each input chunk
    for i, input_chunk in enumerate(input_chunks):
        logger.debug(f"Processing input chunk #{i+1}: {get_chunk_snippet(input_chunk)}")

        # Get raw text from chunk
        raw_text = input_chunk.get("raw_text", "")

        # Special case: Add a blank line at the end of dual_dialogue chunks as this gets removed in parsing
        if input_chunk.get("type") == "dual_dialogue":
            raw_text += "\n"
            logger.debug("Added blank line to dual_dialogue chunk")

        lines = raw_text.split("\n")

        # Process lines
        currently_parsing_chunk = True
        for line in lines:
            # Process line
            completed_chunks = parser.process_line(line)

            # Add completed chunks to parser array
            parser_chunks.extend(completed_chunks)

            # Update currently_parsing_chunk flag
            if completed_chunks:
                currently_parsing_chunk = False

        # If we're still parsing a chunk, try adding empty lines
        if currently_parsing_chunk:
            logger.debug(
                "Still parsing chunk after processing all lines, adding empty lines..."
            )
            empty_line_count = 0
            while currently_parsing_chunk and empty_line_count < 5:
                completed_chunks = parser.process_line("")
                parser_chunks.extend(completed_chunks)

                if completed_chunks:
                    currently_parsing_chunk = False

                empty_line_count += 1

    # Get any final chunk
    final_chunk = parser.get_final_chunk()
    parser_chunks.extend(final_chunk)

    logger.info(f"Generated {len(parser_chunks)} chunks using incremental parsing")

    return parser_chunks


def analyze_chunks(
    input_chunks: List[Dict[str, Any]], parser_chunks: List[Dict[str, Any]]
) -> None:
    """Compare and analyze chunks.

    Args:
        input_chunks: Input chunks from JSON file
        parser_chunks: Chunks generated by parser
    """
    logger.info("\n===== INDIVIDUAL CHUNK COMPARISON =====")
    logger.info("(Format: Original -> Parser)\n")

    # Make copies of the arrays to avoid modifying the originals
    input_compare = input_chunks.copy()
    parser_compare = parser_chunks.copy()

    # Track missing and additional chunks
    missing_chunks = []
    additional_chunks = []

    # Compare chunks
    while parser_compare and input_compare:
        # Get the first line of the first parser chunk
        parser_chunk = parser_compare[0]
        parser_first_line = get_first_line(parser_chunk)

        # Check if this line is in the first input chunk
        input_chunk = input_compare[0]
        input_first_line = get_first_line(input_chunk)

        if parser_first_line in input_chunk["raw_text"]:
            # Lines match, compare chunks
            differences = compare_chunks(input_chunk, parser_chunk)

            if differences:
                logger.info(
                    f'Chunk with text "{get_chunk_snippet(input_chunk)}" has differences:'
                )
                for diff in differences:
                    logger.info(f"  {diff}")

                logger.debug("Input chunk:")
                logger.debug(f"  Type: {input_chunk['type']}")
                logger.debug(f"  Speaker: {input_chunk['speaker']}")
                logger.debug(f"  Text: {input_chunk['text']}")

                logger.debug("Parser chunk:")
                logger.debug(f"  Type: {parser_chunk['type']}")
                logger.debug(f"  Speaker: {parser_chunk['speaker']}")
                logger.debug(f"  Text: {parser_chunk['text']}")

            # Remove both chunks
            input_compare.pop(0)
            parser_compare.pop(0)
        else:
            # Check if the line is in any input chunk
            chunk_index = find_chunk_with_line(input_compare, parser_first_line)

            if chunk_index > 0:
                # Parser is missing chunks
                for i in range(chunk_index):
                    missing_chunk = input_compare.pop(0)
                    missing_chunks.append(missing_chunk)
            else:
                # Parser has additional chunks
                additional_chunk = parser_compare.pop(0)
                additional_chunks.append(additional_chunk)

    # Handle any remaining chunks
    missing_chunks.extend(input_compare)
    additional_chunks.extend(parser_compare)

    # Log missing chunks
    if missing_chunks:
        logger.info(
            f"\nInput has {len(missing_chunks)} chunks that the current parser doesn't generate:"
        )
        for i, chunk in enumerate(missing_chunks):
            snippet = get_chunk_snippet(chunk)
            logger.info(
                f"  Missing chunk #{i+1} (\"{snippet}\"), type: {chunk['type']}"
            )

    # Log additional chunks
    if additional_chunks:
        logger.info(
            f"\nCurrent parser generates {len(additional_chunks)} chunks not in the input:"
        )
        for i, chunk in enumerate(additional_chunks):
            snippet = get_chunk_snippet(chunk)
            logger.info(
                f"  Additional chunk #{i+1} (\"{snippet}\"), type: {chunk['type']}"
            )


def compare_chunks_by_type(
    original_chunks: List[Dict[str, Any]], parsed_chunks: List[Dict[str, Any]]
) -> Dict[str, Dict[str, int]]:
    """Compare chunk types between original and newly parsed chunks.

    Args:
        original_chunks: Original chunks from input file
        parsed_chunks: Chunks generated by current parser

    Returns:
        Dictionary with counts for each chunk type
    """
    # Count chunk types
    original_type_counts: Dict[str, int] = {}
    parsed_type_counts: Dict[str, int] = {}

    for chunk in original_chunks:
        chunk_type = chunk["type"]
        original_type_counts[chunk_type] = original_type_counts.get(chunk_type, 0) + 1

    for chunk in parsed_chunks:
        chunk_type = chunk["type"]
        parsed_type_counts[chunk_type] = parsed_type_counts.get(chunk_type, 0) + 1

    # Get all unique types
    all_types = set(original_type_counts.keys()) | set(parsed_type_counts.keys())

    comparison = {}
    for chunk_type in sorted(all_types):
        original_count = original_type_counts.get(chunk_type, 0)
        parsed_count = parsed_type_counts.get(chunk_type, 0)
        diff = parsed_count - original_count

        comparison[chunk_type] = {
            "original": original_count,
            "parsed": parsed_count,
            "diff": diff,
        }

    return comparison


def log_chunk_comparison(comparison: Dict[str, Dict[str, int]]) -> None:
    """Log the chunk type comparison.

    Args:
        comparison: Chunk type comparison dictionary
    """
    logger.info("\n===== CHUNK TYPE COMPARISON =====\n")
    logger.info(f"{'Type':<30} {'Original':<10} {'Parser':<10} {'Difference':<10}")
    logger.info("-" * 60)

    total_original = 0
    total_parsed = 0

    for chunk_type, counts in comparison.items():
        original_count = counts["original"]
        parsed_count = counts["parsed"]
        diff = counts["diff"]

        total_original += original_count
        total_parsed += parsed_count

        diff_str = f"{diff:+d}" if diff != 0 else "0"
        logger.info(
            f"{chunk_type:<30} {original_count:<10d} {parsed_count:<10d} {diff_str:<10}"
        )

    # Log totals
    total_diff = total_parsed - total_original
    logger.info("-" * 60)
    logger.info(
        f"{'TOTAL':<30} {total_original:<10d} {total_parsed:<10d} {total_diff:+d}"
    )


def run_regression_check(input_file: str, debug: bool = False) -> None:
    """Run regression check on input file.

    Args:
        input_file: Path to input JSON file with chunks
        debug: Enable debug logging
    """
    # Setup logging
    log_file = setup_logging(input_file)
    if debug:
        logging.getLogger("parser").setLevel(logging.DEBUG)

    logger.info(f"Starting regression check on {input_file}")
    logger.info(f"Log file: {log_file}")

    try:
        # Load input chunks
        input_chunks = load_json_chunks(input_file)
        logger.info(f"Loaded {len(input_chunks)} chunks from {input_file}")

        # Initialize parser
        parser = ScreenplayParser()

        # Process chunks
        parser_chunks = process_chunks(input_chunks, parser)

        # Compare chunk types
        logger.info("Comparing chunk types...")
        type_comparison = compare_chunks_by_type(input_chunks, parser_chunks)
        log_chunk_comparison(type_comparison)

        # Compare and analyze chunks
        logger.info("Comparing individual chunks...")
        analyze_chunks(input_chunks, parser_chunks)

        # Final summary
        logger.info("\n===== REGRESSION CHECK SUMMARY =====\n")
        type_diffs = sum(
            1 for counts in type_comparison.values() if counts["diff"] != 0
        )

        if type_diffs == 0 and len(input_chunks) == len(parser_chunks):
            logger.info("✅ No significant differences in chunk counts")
        else:
            logger.info(f"❌ Found differences in {type_diffs} chunk types")

        # Save parser chunks for reference
        output_dir = Path(input_file).parent
        output_file = (
            output_dir / f"{Path(input_file).stem}_regression_checker_parsed.json"
        )

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(parser_chunks, f, indent=2)

        logger.info(f"Saved parser chunks to {output_file}")

    except Exception as e:
        logger.error(f"Error during regression check: {str(e)}", exc_info=True)
        sys.exit(1)


def main() -> None:
    """Command-line entry point for regression checking."""
    parser = argparse.ArgumentParser(
        description="Check for regressions in screenplay parser by comparing with existing JSON chunks"
    )

    parser.add_argument("input_file", help="Path to input JSON chunk file")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    run_regression_check(args.input_file, args.debug)


if __name__ == "__main__":
    main()
