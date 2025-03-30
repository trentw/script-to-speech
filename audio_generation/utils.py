import io
import json
import logging
import os
import traceback
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from pydub import AudioSegment

from utils.logging import get_screenplay_logger

# Get logger for this module
logger = get_screenplay_logger("audio_generation.utils")


def check_audio_level(audio_data: bytes) -> Optional[float]:
    """Check audio data for silence level."""
    try:
        if not audio_data:
            return None

        audio_segment = AudioSegment.from_mp3(io.BytesIO(audio_data))
        return audio_segment.max_dBFS
    except Exception as e:
        # Log the error but don't raise, allow calling function to decide how to handle None
        logger.error(f"Error analyzing audio level: {e}")
        return None


def concatenate_audio_clips(
    audio_clips: List[AudioSegment], output_file: str, gap_duration_ms: int = 0
) -> None:
    """
    Concatenate audio clips using pydub with detailed progress tracking and optional gap.

    Args:
        audio_clips: List of AudioSegment objects
        output_file: Path for the output audio file
        gap_duration_ms: Duration of silence (in ms) to add between clips
    """
    logger.info(f"\nStarting audio concatenation of {len(audio_clips)} clips")
    if gap_duration_ms > 0:
        logger.info(f"Adding {gap_duration_ms}ms gap between clips.")

    total_duration = 0
    for i, clip in enumerate(audio_clips):
        duration_ms = len(clip)
        total_duration += duration_ms
        logger.info(f"Clip {i}: Duration = {duration_ms}ms ({duration_ms/1000:.2f}s)")

    # Add duration for gaps
    total_gap_duration = (
        gap_duration_ms * (len(audio_clips) - 1) if len(audio_clips) > 1 else 0
    )
    total_duration += total_gap_duration

    logger.info(
        f"\nTotal estimated duration (including gaps): {total_duration}ms ({total_duration/1000:.2f}s)"
    )

    try:
        logger.info("\nStarting clip concatenation...")
        final_audio = AudioSegment.empty()
        gap_segment = (
            AudioSegment.silent(duration=gap_duration_ms)
            if gap_duration_ms > 0
            else None
        )

        for i, clip in enumerate(audio_clips, 1):
            logger.info(f"Adding clip {i}/{len(audio_clips)} (duration: {len(clip)}ms)")
            final_audio += clip
            if gap_segment and i < len(
                audio_clips
            ):  # Add gap after clip, except for the last one
                final_audio += gap_segment
            logger.debug(f"Current total duration: {len(final_audio)}ms")

        logger.info(
            f"\nExporting final audio (duration: {len(final_audio)}ms) to: {output_file}"
        )
        final_audio.export(output_file, format="mp3")
        logger.info("Audio export completed")

        # Verify the output file
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            logger.info(f"Output file size: {file_size / 1024 / 1024:.2f}MB")

            # Try to load the output file as a sanity check
            try:
                verify_audio = AudioSegment.from_mp3(output_file)
                logger.info(
                    f"Output file verification successful. Duration: {len(verify_audio)}ms"
                )
                # Compare duration as a basic check
                if (
                    abs(len(final_audio) - len(verify_audio)) > 50
                ):  # Allow small tolerance
                    logger.warning(
                        f"Verified duration ({len(verify_audio)}ms) differs significantly from expected ({len(final_audio)}ms)"
                    )
            except Exception as e:
                logger.error(f"Output file verification failed: {e}")
        else:
            logger.warning("Output file was not created")

    except Exception as e:
        logger.error(f"\nError during audio concatenation: {str(e)}")
        logger.error(traceback.format_exc())  # Log full traceback for debugging
        # Re-raise the exception so the caller knows concatenation failed
        raise


def load_json_chunks(input_file: str) -> List[Dict]:
    """Load and parse JSON chunks from input file."""
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Input JSON file not found: {input_file}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from file {input_file}: {e}")
        raise ValueError(f"Invalid JSON format in {input_file}") from e
    except Exception as e:
        logger.error(f"Failed to load input file {input_file}: {e}")
        # Use a more specific exception or re-raise if appropriate
        raise IOError(f"Could not read input file {input_file}") from e


def create_output_folders(
    input_file: str, run_mode: str = ""
) -> Tuple[str, str, str, str]:
    """
    Create and return paths for output folders (main, cache, logs, output file).

    Args:
        input_file: Path to the input JSON file
        run_mode: String indicating run mode for log file name prefix

    Returns:
        Tuple of (main_output_folder, cache_folder, output_file, log_file)
    """
    # Get base name without extension
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Set up folder structure relative to the script's execution directory
    # Assuming 'output' is a top-level directory
    main_output_folder = os.path.join("output", base_name)
    cache_folder = os.path.join(main_output_folder, "cache")
    logs_folder = os.path.join(main_output_folder, "logs")
    output_file = os.path.join(main_output_folder, f"{base_name}.mp3")

    # Create log filename with run mode prefix
    mode_prefix = f"[{run_mode}]_" if run_mode else ""
    log_file = os.path.join(logs_folder, f"{mode_prefix}log_{timestamp}.txt")

    # Create directories
    try:
        os.makedirs(cache_folder, exist_ok=True)
        logger.debug(f"Ensured cache folder exists: {cache_folder}")
        os.makedirs(logs_folder, exist_ok=True)
        logger.debug(f"Ensured logs folder exists: {logs_folder}")

    except OSError as e:
        logger.error(f"Error creating output directories: {e}")
        raise  # Propagate the error

    return main_output_folder, cache_folder, output_file, log_file
