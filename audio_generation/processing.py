import hashlib
import io
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from pydub import AudioSegment

from text_processors.processor_manager import TextProcessorManager
from tts_providers.tts_provider_manager import TTSProviderManager
from utils.logging import get_screenplay_logger

from .models import AudioClipInfo, AudioGenerationTask, ReportingState
from .reporting import print_audio_task_details
from .utils import check_audio_level, truncate_text

# Use a less common delimiter (consistent with original)
DELIMITER = "~~"

# Get logger for this module
logger = get_screenplay_logger("audio_generation.processing")


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

    This function no longer performs silence checking, which is now handled separately.

    Returns:
        A tuple containing:
        - A list of AudioGenerationTask objects.
        - A ReportingState object populated with initial cache misses.
    """
    logger.info("Starting audio generation planning...")
    tasks: List[AudioGenerationTask] = []
    reporting_state = ReportingState()
    modified_dialogues: List[Dict[str, Any]] = []  # Track processed dialogues

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
            provider_id = tts_provider_manager.get_provider_for_speaker(speaker)
            speaker_id = tts_provider_manager.get_speaker_identifier(speaker)
            logger.debug(f"  Provider ID: {provider_id}, Speaker ID: {speaker_id}")

            # Define filenames and paths
            cache_filename = f"{original_hash}{DELIMITER}{processed_hash}{DELIMITER}{provider_id}{DELIMITER}{speaker_id}.mp3"
            cache_filepath = os.path.join(cache_folder, cache_filename)
            logger.debug(f"  Cache filepath: {cache_filepath}")

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
                task.is_cache_hit = (
                    True  # Assume hit initially, silence check might change this later
                )
            task.checked_cache = True

            # Record initial cache miss state (based only on file existence for now)
            # Override application and silence check results will refine this later.
            if not task.is_cache_hit:
                logger.debug("  Cache file initially missing.")
                if not task.expected_silence:
                    reporting_state.cache_misses[task.cache_filename] = AudioClipInfo(
                        text=task.text_to_speak,
                        cache_path=task.cache_filename,
                        speaker_display=task.speaker_display,
                        speaker_id=task.speaker_id,
                        provider_id=task.provider_id,
                    )

            tasks.append(task)

        except Exception as e:
            logger.error(f"Failed to plan dialogue chunk {idx}: {e}", exc_info=True)
            # Decide whether to skip this chunk or halt entirely.
            # For now, let's log and continue planning other chunks.
            # We might need a way to report planning failures.

    logger.info(f"Audio generation planning complete. {len(tasks)} tasks created.")
    logger.info(f"Initial report state: {len(reporting_state.cache_misses)} misses.")
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
                # Move the file (atomic replace if possible)
                os.replace(override_path, task.cache_filepath)
                logger.info(
                    f"  Successfully applied override for task {task.idx}: {task.cache_filename}"
                )
                # Update task status: it's now definitely a cache hit
                task.is_cache_hit = True
                applied_count += 1
                # If it was previously marked as silent, the override fixed it (we assume overrides are good)
                # We might could update reporting state here if we want to remove it from silent list now, but
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

    for task in tasks:
        if not task.is_cache_hit or task.expected_silence:
            # Skip if not a cache hit or if silence is expected
            continue

        logger.info(
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
    Fetches non-cached audio using TTS provider.
    Saves generated audio to the cache folder. Cache override logic is handled separately.

    This function only handles fetching and caching, not reading the audio data.
    Silence checking for existing cache files is handled by the check_for_silence function.

    Args:
        tasks: List of AudioGenerationTask objects from plan_audio_generation
               (potentially updated by apply_cache_overrides and check_for_silence).
        tts_provider_manager: Initialized TTSProviderManager.
        silence_threshold: dBFS threshold for detecting silence (applied to newly generated files).

    Returns:
        A ReportingState object containing info about *newly generated* silent clips.
    """
    logger.info(
        "Starting audio fetching and caching (post-override and silence check)..."
    )
    fetch_reporting_state = ReportingState()  # To track issues during this phase

    for task in tasks:
        # Print detailed information about the task
        logger.debug(f"\nFetching dialogue #{task.idx}")
        print_audio_task_details(task, logger, log_prefix="  ")

        try:
            # If file is cached, go to next task
            if task.is_cache_hit:
                continue

            try:
                # Generate audio data
                audio_data = None
                if task.expected_silence:
                    logger.info("  Creating intentional silent audio for empty text.")
                    silent_segment = AudioSegment.silent(duration=10)
                    with io.BytesIO() as buf:
                        silent_segment.export(buf, format="mp3")
                        audio_data = buf.getvalue()
                else:
                    audio_data = tts_provider_manager.generate_audio(
                        task.speaker, task.text_to_speak
                    )

                if not audio_data:
                    logger.error(
                        f"  TTS provider returned no audio data for task {task.idx}."
                    )
                    continue

                logger.info(
                    f"  Audio generated successfully for task {task.idx} (size: {len(audio_data)} bytes)."
                )

                # Check for silence
                if silence_threshold is not None:
                    is_silent = check_audio_silence(
                        task=task,
                        audio_data=audio_data,
                        silence_threshold=silence_threshold,
                        reporting_state=fetch_reporting_state,
                        log_prefix="  ",
                    )

                    if is_silent:
                        logger.warning(f"  Newly generated audio is silent.")

                # Save to cache
                try:
                    os.makedirs(os.path.dirname(task.cache_filepath), exist_ok=True)
                    with open(task.cache_filepath, "wb") as f:
                        f.write(audio_data)
                    task.is_cache_hit = True  # It's now cached
                except Exception as e:
                    logger.error(f"  Error saving generated audio to cache: {e}")

            except Exception as e:
                logger.error(f"  Error generating audio: {e}", exc_info=True)

        except Exception as e:
            # Catch unexpected errors during the processing of a single task
            logger.error(
                f"Unexpected error processing task {task.idx}: {e}", exc_info=True
            )
            # Continue to the next task

    logger.info("Audio fetching and caching complete.")
    logger.info(
        f"Fetch report state: {len(fetch_reporting_state.silent_clips)} newly generated silent clips."
    )
    return fetch_reporting_state


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
