import io
import json
import logging
import os
import sys
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from pydub import AudioSegment
from tqdm import tqdm

from utils.logging import get_screenplay_logger

from .models import AudioClipInfo, AudioGenerationTask, ReportingState

# Get logger for this module
logger = get_screenplay_logger("audio_generation.utils")


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
    logger.info(
        f"\nStarting audio concatenation of {len(audio_clips)} clips (includes silent segments between clips)"
    )
    if gap_duration_ms > 0:
        logger.info(f"Adding {gap_duration_ms}ms gap between clips.")

    total_duration = 0
    for i, clip in enumerate(audio_clips):
        duration_ms = len(clip)
        total_duration += duration_ms
        logger.debug(f"Clip {i}: Duration = {duration_ms}ms ({duration_ms/1000:.2f}s)")

    # Add duration for gaps
    total_gap_duration = (
        gap_duration_ms * (len(audio_clips) - 1) if len(audio_clips) > 1 else 0
    )
    total_duration += total_gap_duration

    logger.info(
        f"  Total estimated duration (including gaps): {total_duration}ms ({total_duration/1000:.2f}s)"
    )

    try:
        final_audio = AudioSegment.empty()
        gap_segment = (
            AudioSegment.silent(duration=gap_duration_ms)
            if gap_duration_ms > 0
            else None
        )

        for i, clip in tqdm(
            enumerate(audio_clips, 1),
            desc="Concatenating Audio",
            unit="clip",
            file=sys.stderr,
            leave=False,
            total=len(audio_clips),
        ):
            logger.debug(
                f"Adding clip {i}/{len(audio_clips)} (duration: {len(clip)}ms)"
            )
            final_audio += clip
            if gap_segment and i < len(
                audio_clips
            ):  # Add gap after clip, except for the last one
                final_audio += gap_segment
            logger.debug(f"Current total duration: {len(final_audio)}ms")
        logger.info(f"  Complete: {len(audio_clips)} clips concatenated")
        logger.info(
            f"\nExporting final audio (duration: {len(final_audio)}ms) to: {output_file}"
        )
        final_audio.export(output_file, format="mp3")
        logger.info("  Complete: audio exported")

        # Verify the output file
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            logger.info(f"  Output file size: {file_size / 1024 / 1024:.2f}MB")

            # Try to load the output file as a sanity check
            try:
                verify_audio = AudioSegment.from_mp3(output_file)
                logger.info(
                    f"  Output file verification successful. Duration: {len(verify_audio)}ms"
                )
                # Compare duration as a basic check
                if (
                    abs(len(final_audio) - len(verify_audio)) > 50
                ):  # Allow small tolerance
                    logger.warning(
                        f"  Verified duration ({len(verify_audio)}ms) differs significantly from expected ({len(final_audio)}ms)"
                    )
            except Exception as e:
                logger.error(f"  Output file verification failed: {e}")
        else:
            logger.warning("  Output file was not created")

    except Exception as e:
        logger.error(f"\nError during audio concatenation: {str(e)}")
        logger.error(traceback.format_exc())  # Log full traceback for debugging
        # Re-raise the exception so the caller knows concatenation failed
        raise


def load_json_chunks(input_file: str) -> List[Dict[str, Any]]:
    """Load and parse JSON chunks from input file."""
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            # Load the JSON data and return it
            result: List[Dict[str, Any]] = json.load(f)
            return result
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
    input_file: str, run_mode: str = "", dummy_provider_override: bool = False
) -> Tuple[str, str, str, str]:
    """
    Create and return paths for output folders (main, cache, logs, output file).

    Args:
        input_file: Path to the input JSON file
        run_mode: String indicating run mode for log file name prefix
        dummy_provider_override: If True, prepend "dummy_" to cache folder and output file names

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

    # If dummy provider override is enabled, modify paths
    if dummy_provider_override:
        # Prepend "dummy_" to cache folder and output file
        cache_folder = os.path.join(
            os.path.dirname(cache_folder), f"dummy_{os.path.basename(cache_folder)}"
        )
        if output_file:
            output_dir = os.path.dirname(output_file)
            output_filename = f"dummy_{os.path.basename(output_file)}"
            output_file = os.path.join(output_dir, output_filename)

    # Create log filename with run mode prefix
    dummy_prefix = "[dummy]" if run_mode else ""
    mode_prefix = f"[{run_mode}]_" if run_mode else ""
    log_file = os.path.join(
        logs_folder, f"{dummy_prefix}{mode_prefix}log_{timestamp}.txt"
    )

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


def truncate_text(text: str, max_length: int = 40) -> str:
    """Truncate text if needed"""
    truncated_text = text

    if len(text) > max_length:
        truncated_text = text[: max_length - 3] + "..."

    return truncated_text


def check_audio_level(audio_data: bytes) -> Optional[float]:
    """Check audio data for silence level."""
    try:
        if not audio_data:
            return None

        audio_segment = AudioSegment.from_mp3(io.BytesIO(audio_data))
        return float(audio_segment.max_dBFS)
    except Exception as e:
        # Log the error but don't raise, allow calling function to decide how to handle None
        logger.error(f"Error analyzing audio level: {e}")
        return None


def check_audio_silence(
    task: AudioGenerationTask,
    audio_data: bytes,
    silence_threshold: float,
    reporting_state: ReportingState,
    log_prefix: str = "",
) -> bool:
    """
    Checks if audio data is silent based on the given threshold.
    Updates the task's checked_silence_level and adds to reporting state if silent.

    Args:
        task: The AudioGenerationTask to check
        audio_data: The audio data bytes to check
        silence_threshold: The dBFS threshold for silence detection
        reporting_state: The ReportingState to update if silent
        log_prefix: Optional prefix for log messages

    Returns:
        True if the audio is silent (below threshold), False otherwise
    """
    if task.expected_silence:
        # Skip silence check for intentionally silent audio
        return False

    max_dbfs = check_audio_level(audio_data)
    task.checked_silence_level = max_dbfs
    logger.debug(f"{log_prefix}Audio level (dBFS): {max_dbfs}")

    if max_dbfs is not None and max_dbfs < silence_threshold:
        truncated_text = truncate_text(task.text_to_speak)

        logger.warning("")
        logger.warning(
            f'{log_prefix}Silent clip detected for task #{task.idx} ("{truncated_text}")'
        )
        logger.warning(
            f"{log_prefix}Audio level {max_dbfs:.2f} dBFS is below threshold {silence_threshold} dBFS."
        )
        # Add to silent clips if not already there
        if task.cache_filename not in reporting_state.silent_clips:
            reporting_state.silent_clips[task.cache_filename] = AudioClipInfo(
                text=task.text_to_speak,
                cache_path=task.cache_filename,
                dbfs_level=max_dbfs,
                speaker_display=task.speaker_display,
                speaker_id=task.speaker_id,
                provider_id=task.provider_id,
            )
        return True
    return False
