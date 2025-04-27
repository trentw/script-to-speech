"""Analyze screenplay JSON chunks file."""

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from utils.logging import get_screenplay_logger

from .utils.file_utils import sanitize_name
from .utils.logging_utils import setup_parser_logging

logger = get_screenplay_logger("parser.analyze")


def analyze_chunks(chunks: list) -> None:
    """Analyze screenplay chunks and log statistics.

    Args:
        chunks: List of screenplay chunks
    """
    # Count chunk types
    chunk_type_counts: Dict[str, int] = {}
    speaker_counts: Dict[str, int] = {}
    speakers = set()

    for chunk in chunks:
        # Count chunk types
        chunk_type = chunk["type"]
        chunk_type_counts[chunk_type] = chunk_type_counts.get(chunk_type, 0) + 1

        # Track speakers
        if chunk_type == "dialog":
            # For dialog, use the specified speaker or default
            speaker = chunk.get("speaker", "") or "(default)"
        else:
            # For non-dialog chunks, always attribute to default
            speaker = "(default)"

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


def analyze_screenplay_chunks(json_path: str) -> None:
    """Analyze a screenplay chunks JSON file and output statistics.

    Args:
        json_path: Path to the JSON chunks file
    """
    # Set up logging
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = Path("parser/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    # Get original and sanitized names
    original_name = Path(json_path).stem
    sanitized_name = sanitize_name(original_name)
    log_file = log_dir / f"[analyze]_{sanitized_name}_{timestamp}.log"

    setup_parser_logging(
        str(log_file), file_level=logging.DEBUG, console_level=logging.INFO
    )

    try:
        logger.info(f"Analyzing screenplay chunks from {json_path}")
        with open(json_path, "r", encoding="utf-8") as f:
            chunks = json.load(f)
        analyze_chunks(chunks)
        logger.info("Analysis completed successfully")
    except Exception as e:
        logger.error(f"Error analyzing screenplay chunks: {str(e)}", exc_info=True)
        raise


def main() -> None:
    """Command-line entry point for analyzing screenplay chunks."""
    parser = argparse.ArgumentParser(description="Analyze screenplay JSON chunks file")
    parser.add_argument("json_file", help="Path to JSON chunks file")

    args = parser.parse_args()

    try:
        analyze_screenplay_chunks(args.json_file)
    except Exception as e:
        print(f"Error: {str(e)}")
        exit(1)


if __name__ == "__main__":
    main()
