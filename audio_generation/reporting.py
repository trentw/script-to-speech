import os
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from tts_providers.tts_provider_manager import TTSProviderManager
from utils.generate_standalone_speech import get_command_string

from .models import AudioClipInfo
from .utils import check_audio_level, truncate_text


def print_audio_task_details(task, logger, max_text_length: int = 50, log_prefix=""):
    """
    Print detailed information about an audio generation task.

    Args:
        task: The AudioGenerationTask object containing task details
        logger: Logger to use for output
        max_text_length: Maximum length of text to display before truncating
    """
    # Extract dialogue type from processed dialogue
    dialogue_type = task.processed_dialogue.get("type", "unknown")
    speaker_info = task.speaker_display if task.speaker else "(default)"

    # Truncate text if needed
    truncated_text = truncate_text(task.text_to_speak, max_text_length)

    # Print detailed information
    logger.debug(f"{log_prefix}Dialogue #: {task.idx}")
    logger.debug(f"{log_prefix}Speaker: {speaker_info}, Type: {dialogue_type}")
    logger.debug(f"{log_prefix}Text: {truncated_text}")
    logger.debug(f"{log_prefix}Provider ID: {task.provider_id}")
    logger.debug(f"{log_prefix}Speaker ID: {task.speaker_id}")
    logger.debug(f"{log_prefix}Cache filepath: {task.cache_filepath}")
    logger.debug(f"{log_prefix}Cache hit: {task.is_cache_hit}")

    # Print audio level if available
    if task.checked_silence_level is not None:
        logger.debug(f"{log_prefix}Audio level (dBFS): {task.checked_silence_level}")

    # Print compact summary line
    cache_status = "cache hit" if task.is_cache_hit else "cache miss"
    logger.info(
        f"[{task.idx:04d}][{cache_status}][{speaker_info}][{truncated_text[:max_text_length]}...]"
    )


@dataclass
class ReportingState:
    """State for unified reporting of silent clips and cache misses"""

    silent_clips: Dict[str, AudioClipInfo] = field(default_factory=dict)
    cache_misses: Dict[str, AudioClipInfo] = field(default_factory=dict)


def recheck_audio_files(
    reporting_state: ReportingState, cache_folder: str, silence_threshold: float, logger
) -> None:
    """Recheck all tracked audio files for current status."""

    # Get current state of cache folder
    try:
        existing_files = set(os.listdir(cache_folder))
    except FileNotFoundError:
        logger.warning(f"Cache folder {cache_folder} not found during recheck.")
        existing_files = set()  # Assume no files exist if folder is missing

    # First recheck silent clips
    still_silent = {}
    for cache_filename, clip_info in reporting_state.silent_clips.items():
        cache_filepath = os.path.join(cache_folder, cache_filename)
        if cache_filename not in existing_files:
            # If the file doesn't exist anymore, it's not silent, it's missing
            continue
        try:
            with open(cache_filepath, "rb") as f:
                audio_data = f.read()
            current_dbfs = check_audio_level(audio_data)
            if current_dbfs is not None and current_dbfs < silence_threshold:
                clip_info.dbfs_level = current_dbfs  # Update with current level
                still_silent[cache_filename] = clip_info
            # else: File exists but is no longer silent, remove from silent list (or in this case, don't add it to the still_silent list)
        except Exception as e:
            logger.error(f"Error rechecking audio file {cache_filepath}: {e}")
    reporting_state.silent_clips = still_silent

    # Then recheck cache misses (ensure files previously marked as misses still don't exist)
    actual_misses = {}
    for cache_filename, clip_info in reporting_state.cache_misses.items():
        if cache_filename not in existing_files:
            actual_misses[cache_filename] = clip_info
    reporting_state.cache_misses = actual_misses

    # Add any previously silent files that are now missing to the cache_misses
    for cache_filename, clip_info in list(reporting_state.silent_clips.items()):
        if cache_filename not in existing_files:
            if cache_filename not in reporting_state.cache_misses:
                reporting_state.cache_misses[cache_filename] = clip_info
            # Remove from silent list as it's now a miss
            del reporting_state.silent_clips[cache_filename]


def print_unified_report(
    reporting_state: ReportingState,
    logger,
    tts_provider_manager: TTSProviderManager,
    silence_checking_enabled: bool = False,
    max_misses_to_report: int = 20,
    max_text_length: int = 30,
) -> None:
    """Print unified report of silent clips and cache misses."""

    # Helper function to group clips by speaker
    def group_by_speaker(
        clips: Dict[str, AudioClipInfo],
    ) -> Dict[Tuple[str, str], List[AudioClipInfo]]:
        grouped = defaultdict(list)
        for clip_info in clips.values():
            speaker_key = (
                clip_info.speaker_display or "(default)",
                clip_info.speaker_id or "",
            )
            grouped[speaker_key].append(clip_info)
        return grouped

    # Print silent clips section if silence checking was enabled
    if silence_checking_enabled:
        if reporting_state.silent_clips:
            logger.info("\nSilent clips detected:")
        else:
            logger.info("\nNo silent clips detected.")
        grouped_silent = group_by_speaker(reporting_state.silent_clips)

        for (speaker_display, speaker_id), clips in sorted(grouped_silent.items()):
            logger.info(f"\n- {speaker_display} ({speaker_id}): {len(clips)} clips")
            for clip_info in sorted(clips, key=lambda x: x.text):
                logger.info(f'  • Text: "{clip_info.text}"')
                logger.info(f"    Cache: {clip_info.cache_path}")
                logger.info(f"    dBFS: {clip_info.dbfs_level}")

    # Print cache misses
    if reporting_state.cache_misses:
        header = (
            "\nAdditional cache misses (audio that would need to be generated):"
            if reporting_state.silent_clips and silence_checking_enabled
            else "\nCache misses (audio that would need to be generated):"
        )
        logger.info(header)

        grouped_misses = group_by_speaker(reporting_state.cache_misses)

        for (speaker_display, speaker_id), clips in sorted(grouped_misses.items()):
            logger.info(f"\n- {speaker_display} ({speaker_id}): {len(clips)} clips")
            for clip_info in sorted(clips, key=lambda x: x.text):
                logger.info(f'  • Text: "{clip_info.text}"')
                logger.info(f"    Cache: {clip_info.cache_path}")

    # Only show "all cached" if there were no cache misses, and no silent clips (if checking enabled)
    elif not reporting_state.silent_clips or not silence_checking_enabled:
        logger.info(
            "\nAll audio clips are cached. No additional audio generation needed\n"
        )

    # Print summary if either type of issue was found
    if reporting_state.silent_clips or reporting_state.cache_misses:
        logger.info("\nSummary:")
        if reporting_state.silent_clips and silence_checking_enabled:
            logger.info(f"- Silent clips: {len(reporting_state.silent_clips)}")
        if reporting_state.cache_misses:
            logger.info(f"- Cache misses: {len(reporting_state.cache_misses)}")
            total_chars = sum(
                len(clip.text) for clip in reporting_state.cache_misses.values()
            )
            logger.info(f"- Total characters to generate: {total_chars}")

        # Generate CLI commands for missing audio
        # Combine misses and potentially silent clips (if checking enabled) that need regeneration
        all_issues_needing_generation = {**reporting_state.cache_misses}
        if silence_checking_enabled:
            all_issues_needing_generation.update(reporting_state.silent_clips)

        # Group misses by (provider_id, speaker_id)
        provider_groups = defaultdict(list)
        for clip_info in all_issues_needing_generation.values():
            if clip_info.provider_id and clip_info.speaker_id:
                provider_groups[
                    (
                        clip_info.provider_id,
                        clip_info.speaker_id,
                        clip_info.speaker_display,
                    )
                ].append(clip_info.text)

        # Filter out texts over max length
        commands_to_show = []
        for (
            provider_id,
            speaker_id,
            speaker_display,
        ), texts in provider_groups.items():
            # Apply text length filter
            filtered_texts = [t for t in texts if len(t) <= max_text_length]

            if filtered_texts:
                commands_to_show.append(
                    {
                        "provider": provider_id,
                        "voice_id": speaker_id,
                        "speaker": speaker_display,
                        "texts": filtered_texts,
                        "count": len(filtered_texts),
                    }
                )

        # Apply reporting limits and show commands
        if len(commands_to_show) > 0:
            logger.info("\nCommands to generate missing audio clips:")
            total_misses = sum(c["count"] for c in commands_to_show)

            if total_misses > max_misses_to_report:
                logger.info(
                    f"\nToo many misses to show commands ({total_misses} total)."
                )
                logger.info(f"Use a higher --max-misses-to-report value to see more.")
            else:
                for cmd in commands_to_show:
                    command = get_command_string(
                        tts_provider_manager, cmd["speaker"], cmd["texts"]
                    )
                    if command:
                        logger.info(
                            f"\n# {cmd['count']} clips for {cmd['provider']} voice {cmd['voice_id']} ({cmd['speaker']}):"
                        )
                        logger.info(command)
