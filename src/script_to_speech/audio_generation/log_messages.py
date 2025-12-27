"""Shared logging messages for audio generation pipeline.

Both CLI and GUI use these helpers for consistent log output.
"""

import logging
from enum import Enum
from pathlib import Path
from typing import Optional, Union


class PipelinePhase(str, Enum):
    """Pipeline phases for logging."""

    PLANNING = "planning"
    OVERRIDES = "overrides"
    SILENCE = "silence"
    FETCH = "fetch"
    RECHECK = "recheck"
    CONCAT = "concat"
    FINAL_REPORT = "final_report"


# Phase header messages
_PHASE_MESSAGES = {
    PipelinePhase.PLANNING: "Planning Audio Generation",
    PipelinePhase.OVERRIDES: "Applying Cache Overrides",
    PipelinePhase.SILENCE: "Checking for Silent Audio Files",
    PipelinePhase.FETCH: "Fetching any Non-Cached Audio Files",
    PipelinePhase.RECHECK: "Rechecking Cache Status",
    PipelinePhase.CONCAT: "Concatenating Audio",
    PipelinePhase.FINAL_REPORT: "Final Report",
}


def log_phase(logger: logging.Logger, phase: PipelinePhase) -> None:
    """Log a phase header.

    Args:
        logger: Logger instance
        phase: Pipeline phase to log
    """
    message = _PHASE_MESSAGES.get(phase, str(phase))
    logger.info(f"\n--- {message} ---")

    # Special case: FETCH phase includes privacy notice
    if phase == PipelinePhase.FETCH:
        logger.info(
            "⚠️  PRIVACY NOTICE: Audio generation relies on 3rd party services. "
            "See PRIVACY.md for more details"
        )


def log_completion(
    logger: logging.Logger,
    run_mode: str,
    log_file: Union[Path, str],
    cache_folder: Union[Path, str],
    output_file: Optional[Union[Path, str]] = None,
) -> None:
    """Log the completion summary.

    Args:
        logger: Logger instance
        run_mode: The run mode (e.g., "dry-run", "populate-cache", "generate-output")
        log_file: Path to the log file
        cache_folder: Path to the cache folder
        output_file: Path to the output file (optional, only for full generation)
    """
    logger.info(f"\n--- {run_mode.upper()} Mode Completed ---")
    logger.info(f"Log file: {log_file}")
    logger.info(f"Cache folder: {cache_folder}")
    if output_file:
        logger.info(f"Output file: {output_file}")
    logger.info("Script finished.\n")
