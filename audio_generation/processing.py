import concurrent.futures
import hashlib
import io
import logging
import os
import sys
import threading
from typing import Any, Dict, List, Optional, Tuple

from pydub import AudioSegment
from tqdm import tqdm

from text_processors.processor_manager import TextProcessorManager
from tts_providers.tts_provider_manager import TTSProviderManager
from utils.logging import get_screenplay_logger

from .models import AudioClipInfo, AudioGenerationTask, ReportingState, TaskStatus
from .reporting import print_audio_task_details
from .utils import check_audio_level, check_audio_silence, truncate_text

# Use a less common delimiter (consistent with original)
DELIMITER = "~~"

# Get logger for this module
logger = get_screenplay_logger("audio_generation.processing")

# Download manager sonstants
GLOBAL_MAX_WORKERS = 12  # Max global concurrent TTS downloads/generations
INITIAL_BACKOFF_SECONDS = 10.0  # Initial backoff time when rate limited
BACKOFF_FACTOR = 2.0  # Factor to multiply backoff time by on each retry
MAX_RETRIES = 3  # Maximum number of times to retry a rate-limited task


def generate_chunk_hash(text: str, speaker: Optional[str]) -> str:
    """Generates an MD5 hash for a text and speaker combination."""
    # Convert None to empty string for hashing purposes
    speaker_str = "" if speaker is None else speaker
    return hashlib.md5(f"{text}{speaker_str}".encode()).hexdigest()


def determine_speaker(dialogue: Dict[str, Any]) -> Optional[str]:
    """
    Determines the speaker for a dialogue chunk.
    Returns None if no speaker is specified or if speaker is explicitly "none".
    """
    speaker = dialogue.get("speaker")
    if speaker is None or str(speaker).lower() == "none" or str(speaker) == "":
        return None
    return str(speaker)


def plan_audio_generation(
    dialogues: List[Dict[str, Any]],
    tts_provider_manager: TTSProviderManager,
    processor: TextProcessorManager,
    cache_folder: str,
    cache_overrides_dir: Optional[str],
) -> Tuple[List[AudioGenerationTask], ReportingState]:
    """
    Plans the audio generation process by analyzing dialogues, checking cache,
    and preparing tasks for fetching/generation.

    It additionally tracks cache filepaths to identify duplicates and mark tasks accordingly.

    Returns:
        A tuple containing:
        - A list of AudioGenerationTask objects.
        - A ReportingState object populated with initial cache misses.
    """
    logger.info("Starting audio generation planning...")
    tasks: List[AudioGenerationTask] = []
    reporting_state = ReportingState()
    modified_dialogues: List[Dict[str, Any]] = []  # Track processed dialogues
    cache_filepath_tracking = set()  # Track cache filepaths to detect duplicates

    try:
        existing_cache_files = set(os.listdir(cache_folder))
        logger.info(
            f"Found {len(existing_cache_files)} files in cache folder: {cache_folder}"
        )
    except FileNotFoundError:
        logger.warning(f"Cache folder not found: {cache_folder}. Assuming empty cache.")
        existing_cache_files = set()

    # 1. Pre-process all chunks first
    logger.info("Running pre-processors...")
    try:
        preprocessed_chunks = processor.preprocess_chunks(dialogues)
    except Exception as e:
        logger.error(f"Error during pre-processing: {e}", exc_info=True)
        raise  # Cannot proceed without pre-processing

    logger.info(
        f"Pre-processing complete. Processing {len(preprocessed_chunks)} chunks."
    )

    # 2. Process each chunk and create a plan (task)
    # Use tqdm with context manager for better progress bar display
    with tqdm(
        total=len(preprocessed_chunks),
        desc="Planning Audio Generation",
        unit="chunk",
        file=sys.stderr,
        leave=False,
        mininterval=0.1,  # Update more frequently
        dynamic_ncols=True,  # Adapt to terminal resizing
    ) as progress_bar:
        for idx, original_dialogue in enumerate(preprocessed_chunks):
            logger.debug(f"\nPlanning dialogue #{idx}")

            try:
                # Process the dialogue chunk
                processed_dialogue, _ = processor.process_chunk(original_dialogue)
                modified_dialogues.append(
                    processed_dialogue
                )  # Store for potential later use

                speaker = determine_speaker(processed_dialogue)
                text = processed_dialogue.get("text", "")
                dialogue_type = processed_dialogue.get(
                    "type", ""
                )  # Keep track of type if needed
                speaker_display = speaker if speaker is not None else "(default)"

                logger.debug(f"  Speaker: {speaker}, Type: {dialogue_type}")
                logger.debug(f"  Text: {text[:50]}...")

                # Generate hashes based on original and processed states
                original_speaker = determine_speaker(
                    original_dialogue
                )  # Use original speaker for original hash
                original_hash = generate_chunk_hash(
                    original_dialogue.get("text", ""), original_speaker
                )
                processed_hash = generate_chunk_hash(text, speaker)
                logger.debug(f"  Original hash: {original_hash}")
                logger.debug(f"  Processed hash: {processed_hash}")

                # Determine provider and speaker ID
                provider_id = tts_provider_manager.get_provider_for_speaker(
                    speaker if speaker is not None else "default"
                )
                speaker_id = tts_provider_manager.get_speaker_identifier(speaker)
                logger.debug(f"  Provider ID: {provider_id}, Speaker ID: {speaker_id}")

                # Define filenames and paths
                cache_filename = f"{original_hash}{DELIMITER}{processed_hash}{DELIMITER}{provider_id}{DELIMITER}{speaker_id}.mp3"
                cache_filepath = os.path.join(cache_folder, cache_filename)
                logger.debug(f"  Cache filepath: {cache_filepath}")

                # Check if this is a duplicate cache filepath
                expected_cache_duplicate = cache_filepath in cache_filepath_tracking
                if expected_cache_duplicate:
                    logger.debug(
                        f"  Cache filepath duplicate detected: {cache_filepath}"
                    )

                # Track this filepath for future duplicate detection
                cache_filepath_tracking.add(cache_filepath)

                # Initialize task
                task = AudioGenerationTask(
                    idx=idx,
                    original_dialogue=original_dialogue,
                    processed_dialogue=processed_dialogue,
                    text_to_speak=text,
                    speaker=speaker,
                    provider_id=provider_id,
                    speaker_id=speaker_id,
                    speaker_display=speaker_display,
                    cache_filename=cache_filename,
                    cache_filepath=cache_filepath,
                    expected_silence=not text.strip(),  # Mark if text is empty/whitespace
                    expected_cache_duplicate=expected_cache_duplicate,  # Set duplicate flag
                )

                # Check if cache override *exists*
                task.is_override_available = False
                if cache_overrides_dir:
                    override_path = os.path.join(cache_overrides_dir, cache_filename)
                    if os.path.exists(override_path):
                        logger.debug(f"  Cache override available: {override_path}")
                        task.is_override_available = True
                task.checked_override = True  # Mark that we checked

                # Check if cache file *exists* (independent of override check)
                task.is_cache_hit = False
                if cache_filename in existing_cache_files:
                    logger.debug(f"  Cache file exists: {cache_filename}")
                    task.is_cache_hit = True  # Assume hit initially, silence check might change this later
                task.checked_cache = True

                # Record initial cache miss state (based only on file existence for now)
                # Override application and silence check results will refine this later.
                if not task.is_cache_hit:
                    logger.debug("  Cache file initially missing.")
                    if not task.expected_silence:
                        reporting_state.cache_misses[task.cache_filename] = (
                            AudioClipInfo(
                                text=task.text_to_speak,
                                cache_path=task.cache_filename,
                                speaker_display=task.speaker_display,
                                speaker_id=task.speaker_id,
                                provider_id=task.provider_id,
                            )
                        )

                tasks.append(task)

            except Exception as e:
                logger.error(f"Failed to plan dialogue chunk {idx}: {e}", exc_info=True)
                # Decide whether to skip this chunk or halt entirely.
                # For now, let's log and continue planning other chunks.
                # We might need a way to report planning failures.

            # Update progress bar after each iteration
            progress_bar.update(1)

    logger.info(f"Audio generation planning complete. {len(tasks)} tasks created.")
    logger.info(f"Initial report state: {len(reporting_state.cache_misses)} misses.")
    # Log info about duplicates
    duplicate_count = sum(1 for task in tasks if task.expected_cache_duplicate)
    logger.info(f"Detected {duplicate_count} tasks with duplicate cache filepaths.")
    return tasks, reporting_state


def apply_cache_overrides(
    tasks: List[AudioGenerationTask],
    cache_overrides_dir: Optional[str],
    cache_folder: str,
) -> None:
    """
    Applies cache overrides by moving files from the override directory to the cache.
    Updates the is_cache_hit status of tasks if an override is successfully applied.
    Modifies the tasks list in place.
    """
    if not cache_overrides_dir:
        logger.info(
            "Cache overrides directory not specified, skipping override application."
        )
        return

    logger.info(f"Applying cache overrides from directory: {cache_overrides_dir}")
    applied_count = 0
    error_count = 0

    for task in tasks:
        if task.is_override_available:  # Check if planning phase found an override file
            override_path = os.path.join(cache_overrides_dir, task.cache_filename)
            logger.debug(
                f"  Attempting override for task {task.idx}: {override_path} -> {task.cache_filepath}"
            )
            try:
                # Ensure cache directory exists before moving
                os.makedirs(os.path.dirname(task.cache_filepath), exist_ok=True)

                if os.path.exists(override_path):
                    # Move the file (atomic replace if possible)
                    os.replace(override_path, task.cache_filepath)
                    logger.info(
                        f"  Successfully applied override for task {task.idx}: {task.cache_filename}"
                    )
                    applied_count += 1
                else:
                    # If override path no longer exists, assume that previous task with same cache path
                    # already moved override to cache dir
                    logger.info(
                        f"  Override already applied for task {task.idx}: {task.cache_filename}"
                    )
                # Update task status: it's now definitely a cache hit
                task.is_cache_hit = True
                # If it was previously marked as silent, the override fixed it (we assume overrides are good)
                # We could update reporting state here if we want to remove it from silent list now, but
                # this should be caught and updated when we re-check silence before final reporting
            except Exception as e:
                logger.error(
                    f"  Error applying override file {override_path} for task {task.idx}: {e}"
                )
                error_count += 1
                # If override failed, the original cache status (hit or miss) remains.

    logger.info(
        f"Cache override application complete. Applied: {applied_count}, Errors: {error_count}"
    )


def check_for_silence(
    tasks: List[AudioGenerationTask],
    silence_threshold: Optional[float],
) -> ReportingState:
    """
    Checks existing cache files for silence.
    This is a separate step in the audio generation pipeline.

    Args:
        tasks: List of AudioGenerationTask objects from plan_audio_generation.
        silence_threshold: dBFS threshold for detecting silence.

    Returns:
        A ReportingState object containing info about silent clips.
    """
    logger.info("Starting silence check for existing cache files...")
    reporting_state = ReportingState()

    if silence_threshold is None:
        logger.info("Silence checking disabled. Skipping.")
        return reporting_state

    # Filter tasks that need silence checking
    tasks_to_check = [
        task for task in tasks if task.is_cache_hit and not task.expected_silence
    ]

    if not tasks_to_check:
        logger.info("No tasks need silence checking.")
        return reporting_state

    # Use tqdm with context manager for better progress bar display
    with tqdm(
        total=len(tasks_to_check),
        desc="Checking for Silence",
        unit="file",
        file=sys.stderr,
        leave=False,
        mininterval=0.1,  # Update more frequently
        dynamic_ncols=True,  # Adapt to terminal resizing
    ) as progress_bar:
        for task in tasks_to_check:
            # Remove the per-task logging that would clutter the console
            # logger.info(f"Checking task #{task.idx} for silence (threshold: {silence_threshold} dBFS)")
            logger.debug(
                f"Checking task #{task.idx} for silence (threshold: {silence_threshold} dBFS)"
            )
            try:
                with open(task.cache_filepath, "rb") as f:
                    audio_data = f.read()

                is_silent = check_audio_silence(
                    task=task,
                    audio_data=audio_data,
                    silence_threshold=silence_threshold,
                    reporting_state=reporting_state,
                    log_prefix="  ",
                )

                if is_silent:
                    logger.warning(
                        f"  Existing cache file is silent: {task.cache_filepath}. Will be treated as miss unless overridden."
                    )
                    # Mark as cache miss so it will be regenerated
                    task.is_cache_hit = False
            except Exception as e:
                logger.error(
                    f"  Error checking audio file {task.cache_filepath}: {e}. Cannot confirm silence level."
                )
                # Don't assume miss, maybe file is just corrupted? Let fetch handle it.

            # Update progress bar after each iteration
            progress_bar.update(1)

    logger.info(
        f"Silence check complete. Found {len(reporting_state.silent_clips)} silent clips."
    )
    return reporting_state


def fetch_and_cache_audio(
    tasks: List[AudioGenerationTask],
    tts_provider_manager: TTSProviderManager,
    silence_threshold: Optional[float],
) -> ReportingState:
    """
    Fetches non-cached audio using the AudioDownloadManager with provider-specific
    concurrency limits and rate limit handling.

    Args:
        tasks: List of AudioGenerationTask objects from plan_audio_generation
               (potentially updated by apply_cache_overrides and check_for_silence).
        tts_provider_manager: Initialized TTSProviderManager.
        silence_threshold: dBFS threshold for detecting silence (applied to newly generated files).

    Returns:
        A ReportingState object containing info about *newly generated* silent clips.
    """
    from .download_manager import AudioDownloadManager

    logger.info(
        "Starting audio fetching and caching (post-override and silence check)..."
    )

    # Update the expected_cache_duplicate state based on current cache hits
    # This ensures we don't try to generate the same file in multiple threads
    # if overrides or silence checks changed the cache status.
    update_cache_duplicate_state(tasks)

    # Mark tasks with appropriate status
    for task in tasks:
        if task.is_cache_hit:
            task.status = TaskStatus.CACHED
        elif task.expected_cache_duplicate:
            task.status = TaskStatus.SKIPPED_DUPLICATE
        else:
            task.status = TaskStatus.PENDING

    # Count statistics for logging
    cached_count = sum(1 for task in tasks if task.status == TaskStatus.CACHED)
    skipped_duplicates = sum(
        1 for task in tasks if task.status == TaskStatus.SKIPPED_DUPLICATE
    )
    pending_count = sum(1 for task in tasks if task.status == TaskStatus.PENDING)
    total_tasks = len(tasks)

    logger.info(
        f"Total tasks: {total_tasks}, Cached: {cached_count}, "
        f"Skipped Duplicates: {skipped_duplicates}, To Process: {pending_count}"
    )

    # If there are no tasks to process, return empty reporting state
    if pending_count == 0:
        logger.info("No tasks to process, returning.")
        return ReportingState()

    # Create and run the download manager
    download_manager = AudioDownloadManager(
        tasks=tasks,
        tts_provider_manager=tts_provider_manager,
        global_max_workers=GLOBAL_MAX_WORKERS,
        initial_backoff_seconds=INITIAL_BACKOFF_SECONDS,
        backoff_factor=BACKOFF_FACTOR,
        max_retries=MAX_RETRIES,
        silence_threshold=silence_threshold,
    )

    # Run the download manager and get the reporting state
    reporting_state = download_manager.run()

    # Final statistics for logging
    generated_count = sum(1 for task in tasks if task.status == TaskStatus.GENERATED)
    failed_count = sum(
        1
        for task in tasks
        if task.status in (TaskStatus.FAILED_OTHER, TaskStatus.FAILED_RATE_LIMIT)
    )
    rate_limited_count = sum(
        1 for task in tasks if task.status == TaskStatus.FAILED_RATE_LIMIT
    )

    logger.info("Audio fetching and caching complete.")
    logger.info(f"  Total tasks: {total_tasks}")
    logger.info(f"  Already cached: {cached_count}")
    logger.info(f"  Skipped duplicates: {skipped_duplicates}")
    logger.info(f"  Successfully generated: {generated_count}")
    logger.info(f"  Failed: {failed_count} (rate limited: {rate_limited_count})")
    logger.info(
        f"  Newly generated silent clips detected: {len(reporting_state.silent_clips)}"
    )

    return reporting_state


def update_cache_duplicate_state(tasks: List[AudioGenerationTask]) -> int:
    """
    Updates the expected_cache_duplicate flag for each task based on cache filepath.
    This ensures we have the most up-to-date state of which tasks will create duplicate cache files.

    Args:
        tasks: List of AudioGenerationTask objects to update

    Returns:
        The number of tasks marked as duplicates
    """
    logger.info("Updating cache duplicate state for tasks...")
    cache_filepath_tracking = set()
    duplicate_count = 0

    for task in tasks:
        # Reset the flag
        task.expected_cache_duplicate = False

        # Check if this filepath has already been seen
        if task.cache_filepath in cache_filepath_tracking:
            task.expected_cache_duplicate = True
            duplicate_count += 1
            logger.debug(
                f"  Task #{task.idx} marked as duplicate for filepath: {task.cache_filepath}"
            )

        # Add to tracking set
        cache_filepath_tracking.add(task.cache_filepath)

    logger.info(
        f"Cache duplicate update complete. {duplicate_count} tasks marked as duplicates."
    )
    return duplicate_count
