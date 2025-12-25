"""Analyze screenplay JSON chunks file."""

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from ..utils.file_system_utils import create_output_folders
from ..utils.logging import get_screenplay_logger
from .utils.logging_utils import setup_parser_logging

logger = get_screenplay_logger("parser.analyze")


def analyze_chunks(chunks: list, log_results: bool = True) -> Dict[str, Any]:
    """Analyze screenplay chunks and optionally log statistics.

    Args:
        chunks: List of screenplay chunks
        log_results: Whether to log the results (default: True)

    Returns:
        Dictionary containing analysis results with the following structure:
        {
            "chunk_type_counts": {"dialogue": 100, "action": 50, ...},
            "speaker_counts": {"ALICE": 25, "BOB": 30, ...},
            "total_distinct_speakers": 5,
            "speakers": ["ALICE", "BOB", ...],
            "total_chunks": 150
        }
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
        if chunk_type == "dialogue":
            # For dialogue, use the specified speaker or default
            speaker = chunk.get("speaker", "") or "(default)"
        else:
            # For non-dialogue chunks, always attribute to default
            speaker = "(default)"

        speakers.add(speaker)
        speaker_counts[speaker] = speaker_counts.get(speaker, 0) + 1

    # Prepare results
    results = {
        "chunk_type_counts": dict(sorted(chunk_type_counts.items())),
        "speaker_counts": dict(
            sorted(speaker_counts.items(), key=lambda x: (-x[1], x[0]))
        ),
        "total_distinct_speakers": len(speakers),
        "speakers": sorted(list(speakers)),
        "total_chunks": len(chunks),
    }

    # Log results if requested
    if log_results:
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
        for speaker, count in sorted(
            speaker_counts.items(), key=lambda x: (-x[1], x[0])
        ):
            logger.info(f"  {speaker}: {count}")

    return results


def analyze_screenplay_chunks(
    json_path: str, log_results: bool = True
) -> Dict[str, Any]:
    """Analyze a screenplay chunks JSON file and output statistics.

    Args:
        json_path: Path to the JSON chunks file
        log_results: Whether to log the results (default: True)

    Returns:
        Dictionary containing analysis results
    """

    # Use the unified create_output_folders function
    _, _, _, log_file = create_output_folders(str(json_path), run_mode="analyze")

    setup_parser_logging(
        str(log_file), file_level=logging.DEBUG, console_level=logging.INFO
    )

    try:
        logger.info(f"Analyzing screenplay chunks from {json_path}")
        with open(json_path, "r", encoding="utf-8") as f:
            chunks = json.load(f)
        results = analyze_chunks(chunks, log_results=log_results)
        logger.info("Analysis completed successfully")
        return results
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
