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

from ..utils.logging import get_screenplay_logger
from .models import AudioClipInfo, AudioGenerationTask, ReportingState

# Get logger for this module
logger = get_screenplay_logger("audio_generation.utils")


def concatenate_tasks_batched(
    tasks: List[AudioGenerationTask],
    output_file: str,
    batch_size: int = 250,
    gap_duration_ms: int = 500,
) -> None:
    """
    Concatenate audio from tasks using pydub with batch processing for improved performance.
    This function loads audio files directly from task cache paths, one batch at a time.

    Args:
        tasks: List of AudioGenerationTask objects
        output_file: Path for the output audio file
        batch_size: Number of clips to process in each batch
        gap_duration_ms: Duration of silence (in ms) to add between clips
    """
    logger.info(f"\nStarting batched audio concatenation of {len(tasks)} tasks")
    logger.info(f"Using batch size: {batch_size} clips per batch")

    if gap_duration_ms > 0:
        logger.info(f"Adding {gap_duration_ms}ms gap between clips.")

    # Create gap segment if needed
    gap_segment = (
        AudioSegment.silent(duration=gap_duration_ms) if gap_duration_ms > 0 else None
    )

    # Count valid tasks (those with existing cache files)
    valid_tasks = [task for task in tasks if os.path.exists(task.cache_filepath)]
    if len(valid_tasks) < len(tasks):
        logger.warning(
            f"Skipping {len(tasks) - len(valid_tasks)} tasks with missing cache files"
        )

    if not valid_tasks:
        logger.error("No valid audio files found for concatenation")
        return

    # Divide tasks into batches
    batches = [
        valid_tasks[i : i + batch_size] for i in range(0, len(valid_tasks), batch_size)
    ]
    logger.debug(f"Divided into {len(batches)} batches")

    try:
        # Create temporary directory for batch files
        temp_dir = os.path.join(os.path.dirname(output_file), "temp_batches")
        os.makedirs(temp_dir, exist_ok=True)

        batch_files = []
        total_clips_processed = 0

        # Setup a single progress bar for all clips
        with tqdm(
            total=len(valid_tasks),
            desc="Processing Audio Clips",
            unit="clip",
            file=sys.stderr,
            leave=False,
        ) as progress_bar:
            # Process each batch
            for batch_idx, batch_tasks in enumerate(batches):
                batch_file = os.path.join(temp_dir, f"batch_{batch_idx}.mp3")
                logger.debug(
                    f"Processing batch {batch_idx+1}/{len(batches)} ({len(batch_tasks)} clips)"
                )

                # Concatenate clips within the batch
                batch_audio = AudioSegment.empty()

                for task_idx, task in enumerate(batch_tasks):
                    try:
                        # Load segment directly from cache file path
                        segment = AudioSegment.from_mp3(task.cache_filepath)
                        batch_audio += segment

                        # Add gap if needed (not after last clip, not if next clip is expected silence)
                        next_task_idx = total_clips_processed + 1
                        if (
                            gap_segment
                            and next_task_idx < len(valid_tasks)
                            and not task.expected_silence
                        ):
                            batch_audio += gap_segment

                        total_clips_processed += 1
                        progress_bar.update(1)

                    except Exception as e:
                        logger.error(
                            f"Failed to load audio segment for task {task.idx} from file {task.cache_filepath}: {e}"
                        )
                        progress_bar.update(
                            1
                        )  # Still update progress bar for skipped files

                # Export batch to file
                if len(batch_audio) > 0:
                    logger.debug(
                        f"Exporting batch {batch_idx+1} (duration: {len(batch_audio)}ms)"
                    )
                    batch_audio.export(batch_file, format="mp3")
                    batch_files.append(batch_file)
                else:
                    logger.warning(f"Batch {batch_idx+1} is empty, skipping export")

        if not batch_files:
            logger.error("No batch files were created, cannot generate output")
            return

        # Concatenate batch files
        logger.info(f"Concatenating {len(batch_files)} batch files into final output")
        final_audio = AudioSegment.empty()

        for batch_file in tqdm(
            batch_files,
            desc="Concatenating Batches",
            unit="batch",
            file=sys.stderr,
            leave=False,
        ):
            batch_segment = AudioSegment.from_mp3(batch_file)
            final_audio += batch_segment

        # Export final audio
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
        logger.error(f"\nError during batched audio concatenation: {str(e)}")
        logger.error(traceback.format_exc())  # Log full traceback for debugging
        # Re-raise the exception so the caller knows concatenation failed
        raise

    finally:
        # Clean up temporary files
        try:
            if "temp_dir" in locals() and os.path.exists(temp_dir):
                for batch_file in os.listdir(temp_dir):
                    try:
                        os.remove(os.path.join(temp_dir, batch_file))
                    except Exception as e:
                        logger.warning(
                            f"Failed to remove temporary file {batch_file}: {e}"
                        )
                os.rmdir(temp_dir)
                logger.info("Temporary batch files cleaned up")
        except Exception as e:
            logger.warning(f"Failed to clean up some temporary files: {e}")


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
