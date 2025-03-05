from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict
from dataclasses import dataclass, field
from text_processors.processor_manager import TextProcessorManager
from datetime import datetime
from pathlib import Path
from pydub import AudioSegment
from tts_providers.tts_provider_manager import TTSProviderManager
from utils.logging import setup_screenplay_logging, get_screenplay_logger
from utils.generate_standalone_speech import get_command_string
from text_processors.utils import get_processor_configs
from utils.audio_utils import configure_ffmpeg
import logging
import hashlib
import argparse
import io
import json
import os
import sys
import traceback

# Use a less common delimiter
DELIMITER = "~~"


logger = get_screenplay_logger("dialog_audio")


@dataclass
class AudioClipInfo:
    """Information about an audio clip"""

    text: str
    cache_path: str
    dbfs_level: Optional[float] = None
    speaker_display: Optional[str] = None
    speaker_id: Optional[str] = None
    provider_id: Optional[str] = None


@dataclass
class ReportingState:
    """State for unified reporting of silent clips and cache misses"""

    silent_clips: Dict[str, AudioClipInfo] = field(default_factory=dict)
    cache_misses: Dict[str, AudioClipInfo] = field(default_factory=dict)


def check_audio_level(audio_data: bytes) -> Optional[float]:
    """Check audio data for silence level."""
    try:
        if not audio_data:
            return None

        audio_segment = AudioSegment.from_mp3(io.BytesIO(audio_data))
        return audio_segment.max_dBFS
    except Exception as e:
        logger.error(f"Error analyzing audio: {e}")
        return None


def recheck_audio_files(
    reporting_state: ReportingState, cache_folder: str, silence_threshold: float, logger
) -> None:
    """Recheck all tracked audio files for current status."""

    # Get current state of cache folder
    existing_files = set(os.listdir(cache_folder))

    # First recheck silent clips
    still_silent = {}
    for cache_filename, clip_info in reporting_state.silent_clips.items():
        cache_filepath = os.path.join(cache_folder, cache_filename)
        try:
            with open(cache_filepath, "rb") as f:
                audio_data = f.read()
            current_dbfs = check_audio_level(audio_data)
            if current_dbfs is not None and current_dbfs < silence_threshold:
                clip_info.dbfs_level = current_dbfs  # Update with current level
                still_silent[cache_filename] = clip_info
        except Exception as e:
            logger.error(f"Error rechecking audio file {cache_filepath}: {e}")
    reporting_state.silent_clips = still_silent

    # Then recheck cache misses
    actual_misses = {}
    for cache_filename, clip_info in reporting_state.cache_misses.items():
        if cache_filename not in existing_files:
            actual_misses[cache_filename] = clip_info
    reporting_state.cache_misses = actual_misses


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
            if reporting_state.silent_clips
            else "\nCache misses (audio that would need to be generated):"
        )
        logger.info(header)

        grouped_misses = group_by_speaker(reporting_state.cache_misses)

        for (speaker_display, speaker_id), clips in sorted(grouped_misses.items()):
            logger.info(f"\n- {speaker_display} ({speaker_id}): {len(clips)} clips")
            for clip_info in sorted(clips, key=lambda x: x.text):
                logger.info(f'  • Text: "{clip_info.text}"')
                logger.info(f"    Cache: {clip_info.cache_path}")

    # Only show "all cached" if there were no cache misses, and no silent clips
    elif not reporting_state.silent_clips:
        logger.info(
            "\nAll audio clips are cached. No additional audio generation needed\n"
        )

    # Print summary if either type of issue was found
    if reporting_state.silent_clips or reporting_state.cache_misses:
        logger.info("\nSummary:")
        if reporting_state.silent_clips:
            logger.info(f"- Silent clips: {len(reporting_state.silent_clips)}")
        if reporting_state.cache_misses:
            logger.info(f"- Cache misses: {len(reporting_state.cache_misses)}")
            total_chars = sum(
                len(clip.text) for clip in reporting_state.cache_misses.values()
            )
            logger.info(f"- Total characters to generate: {total_chars}")

        # Generate CLI commands for missing audio
        all_misses = {**reporting_state.silent_clips, **reporting_state.cache_misses}

        # Group misses by (provider_id, speaker_id)
        provider_groups = defaultdict(list)
        for clip_info in all_misses.values():
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


def create_output_folders(
    input_file: str, create_sequence: bool = True, run_mode: str = ""
) -> Tuple[str, str, str, str, str]:
    """
    Create and return paths for output folders following the standard structure.

    Args:
        input_file: Path to the input JSON file
        create_sequence: Whether to create sequence folder (False for dry-run/populate-cache)
        run_mode: String indicating run mode for log file name prefix

    Returns:
        Tuple of (main_output_folder, cache_folder, sequence_folder, output_file, log_file)
    """
    # Get base name without extension
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Set up folder structure
    main_output_folder = os.path.join("output", base_name)
    cache_folder = os.path.join(main_output_folder, "cache")
    sequence_folder = os.path.join(
        main_output_folder, "sequence", f"sequence_{timestamp}"
    )
    logs_folder = os.path.join(main_output_folder, "logs")
    output_file = os.path.join(main_output_folder, f"{base_name}.mp3")

    # Create log filename with run mode prefix
    mode_prefix = f"[{run_mode}]_" if run_mode else ""
    log_file = os.path.join(logs_folder, f"{mode_prefix}log_{timestamp}.txt")

    # Create directories
    os.makedirs(cache_folder, exist_ok=True)
    os.makedirs(logs_folder, exist_ok=True)
    if create_sequence:
        os.makedirs(sequence_folder, exist_ok=True)

    return main_output_folder, cache_folder, sequence_folder, output_file, log_file


def load_json_chunks(input_file: str) -> List[Dict]:
    """Load and parse JSON chunks from input file."""
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise ValueError(f"Failed to load input file {input_file}: {e}")


def generate_chunk_hash(text: str, speaker: Optional[str]) -> str:
    # Convert None to empty string for hashing purposes
    speaker_str = "" if speaker is None else speaker
    return hashlib.md5(f"{text}{speaker_str}".encode()).hexdigest()


def determine_speaker(dialogue: Dict[str, str]) -> Optional[str]:
    """
    Determine the speaker for a dialogue chunk.
    Returns None if no speaker is specified.

    Args:
        dialogue: Dictionary containing dialogue information

    Returns:
        Optional[str]: Speaker name or None if no speaker specified
    """
    speaker = dialogue.get("speaker")
    if speaker is None or speaker.lower() == "none" or speaker == "":
        return None

    return speaker


def generate_audio_clips(
    dialogues: List[Dict],
    gap_duration_ms: int,
    tts_provider_manager: TTSProviderManager,
    cache_folder: str,
    sequence_folder: str,
    processor: TextProcessorManager,
    verbose: bool = False,
    dry_run: bool = False,
    populate_cache: bool = False,
    silence_threshold: Optional[float] = None,
    cache_overrides_dir: Optional[str] = None,
) -> Tuple[List[AudioSegment], List[Dict]]:
    logger.info("Starting generate_audio_clips function")
    audio_clips = []
    modified_dialogues = []

    # Track existing files for cache hit detection
    existing_files = set(os.listdir(cache_folder))

    # Initialize reporting state
    reporting_state = ReportingState()

    # First run pre-processors
    logger.info("Running pre-processors")
    preprocessed_chunks = processor.preprocess_chunks(dialogues)

    for idx, dialogue in enumerate(preprocessed_chunks):
        logger.info(f"\nProcessing dialogue {idx}")

        # Process the dialogue
        processed_dialogue, was_modified = processor.process_chunk(dialogue)
        modified_dialogues.append(processed_dialogue)

        speaker = determine_speaker(processed_dialogue)
        text = processed_dialogue.get("text", "")
        dialogue_type = processed_dialogue.get("type", "")

        logger.info(f"Speaker: {speaker}, Type: {dialogue_type}")
        logger.info(f"Text: {text[:50]}...")

        original_hash = generate_chunk_hash(
            dialogue.get("text", ""), determine_speaker(dialogue)
        )
        processed_hash = generate_chunk_hash(text, speaker)
        logger.info(f"Original hash: {original_hash}")
        logger.info(f"Processed hash: {processed_hash}")

        provider_id = tts_provider_manager.get_provider_for_speaker(speaker)
        logger.info(f"Provider ID: {provider_id}")

        speaker_id = tts_provider_manager.get_speaker_identifier(speaker)
        logger.info(f"Speaker ID: {speaker_id}")

        cache_filename = f"{original_hash}{DELIMITER}{processed_hash}{DELIMITER}{provider_id}{DELIMITER}{speaker_id}.mp3"
        sequence_filename = f"{idx:04d}{DELIMITER}{original_hash}{DELIMITER}{processed_hash}{DELIMITER}{provider_id}{DELIMITER}{speaker_id}.mp3"

        cache_filepath = os.path.join(cache_folder, cache_filename)
        sequence_filepath = os.path.join(sequence_folder, sequence_filename)

        logger.info(f"Cache filepath: {cache_filepath}")
        if not dry_run and not populate_cache:
            logger.info(f"Sequence filepath: {sequence_filepath}")

        # Check cache overrides directory first
        if cache_overrides_dir:
            cache_overrides_path = os.path.join(cache_overrides_dir, cache_filename)
            if os.path.exists(cache_overrides_path):
                if dry_run:
                    logger.info(
                        f"Would move cache override audio file to cache: {cache_overrides_path} -> {cache_filepath}"
                    )
                else:
                    try:
                        # Ensure cache directory exists
                        os.makedirs(os.path.dirname(cache_filepath), exist_ok=True)
                        # Move the file from cache override directory to cache (will overwrite if exists)
                        os.replace(cache_overrides_path, cache_filepath)
                        logger.info(
                            f"Moved cache override audio file to cache: {cache_overrides_path} -> {cache_filepath}"
                        )
                        # Add to existing files since we just moved it
                        existing_files.add(cache_filename)
                    except Exception as e:
                        logger.error(f"Error moving preferred audio file: {e}")

        # Check if file exists in cache
        cache_hit = cache_filename in existing_files
        logger.info(f"Cache hit: {cache_hit}")

        # Check for empty text - these should be silent
        expect_silence = not text.strip()

        if cache_hit and not expect_silence and silence_threshold is not None:
            # Check cached files for silence if requested
            try:
                with open(cache_filepath, "rb") as f:
                    audio_data = f.read()
                max_dbfs = check_audio_level(audio_data)
                logger.info(f"Audio level (dBFS): {max_dbfs}")

                if max_dbfs is not None and max_dbfs < silence_threshold:
                    logger.warning(
                        f"Audio level {max_dbfs} dBFS is below threshold {silence_threshold} dBFS"
                    )
                    cache_hit = False
                    # Track silent clip
                    speaker_display = speaker if speaker is not None else "(default)"
                    reporting_state.silent_clips[cache_filename] = AudioClipInfo(
                        text=text,
                        cache_path=cache_filename,
                        dbfs_level=max_dbfs,
                        speaker_display=speaker_display,
                        speaker_id=speaker_id,
                        provider_id=provider_id,
                    )
            except Exception as e:
                logger.error(f"Error checking audio file: {e}")
                cache_hit = False

        if not cache_hit:
            # Track cache miss
            speaker_display = speaker if speaker is not None else "(default)"
            reporting_state.cache_misses[cache_filename] = AudioClipInfo(
                text=text,
                cache_path=cache_filename,
                speaker_display=speaker_display,
                speaker_id=speaker_id,
                provider_id=provider_id,
            )

        if not dry_run:
            audio_data = None
            if cache_hit:
                logger.info("Using cached audio file")
                try:
                    with open(cache_filepath, "rb") as f:
                        audio_data = f.read()
                    logger.info("Successfully read cached audio")
                except Exception as e:
                    logger.error(f"Error reading cached audio: {e}")
                    cache_hit = False  # Force regeneration

            if not cache_hit:
                logger.info("Generating new audio file")
                try:
                    if expect_silence:
                        # Create a very short silent audio for empty text
                        logger.info("Creating intentional silent audio for empty text")
                        silent_segment = AudioSegment.silent(duration=10)
                        audio_data = silent_segment.export(format="mp3").read()
                    else:
                        # Generate audio normally for non-empty text
                        audio_data = tts_provider_manager.generate_audio(speaker, text)

                        # Check newly generated audio for silence if requested
                        if silence_threshold is not None:
                            max_dbfs = check_audio_level(audio_data)
                            logger.info(f"Generated audio level (dBFS): {max_dbfs}")
                            if max_dbfs is not None and max_dbfs < silence_threshold:
                                logger.warning(
                                    f"Generated audio level {max_dbfs} dBFS is below threshold {silence_threshold} dBFS"
                                )
                                # Track silent clip
                                speaker_display = (
                                    speaker if speaker is not None else "(default)"
                                )
                                reporting_state.silent_clips[cache_filename] = (
                                    AudioClipInfo(
                                        text=text,
                                        cache_path=cache_filename,
                                        dbfs_level=max_dbfs,
                                        speaker_display=speaker_display,
                                        speaker_id=speaker_id,
                                        provider_id=provider_id,
                                    )
                                )

                    logger.info("Audio generated")

                    # Save to cache
                    with open(cache_filepath, "wb") as f:
                        f.write(audio_data)
                    # Track the new cache file
                    existing_files.add(cache_filename)
                    logger.info(f"Audio saved to cache: {cache_filepath}")
                except Exception as e:
                    logger.error(f"Error generating new audio: {e}")

            # Only handle sequence files and audio clips if doing full run
            if not populate_cache and audio_data:
                try:
                    # Save to sequence folder
                    with open(sequence_filepath, "wb") as f:
                        f.write(audio_data)
                    logger.info(f"Audio saved to sequence folder: {sequence_filepath}")

                    # Add to audio clips
                    audio_segment = AudioSegment.from_mp3(io.BytesIO(audio_data))
                    audio_clips.append(audio_segment)
                    logger.info("Audio added to clips list")

                    # Only add gap if this isn't empty text and isn't the last item
                    if idx < len(dialogues) - 1 and text.strip():
                        logger.info("Adding gap between dialogues")
                        gap = AudioSegment.silent(duration=gap_duration_ms)
                        audio_clips.append(gap)
                        logger.info("Gap added")
                except Exception as e:
                    logger.error(f"Error processing audio data: {e}")

        if verbose or (dry_run and not cache_hit):
            status = "cache hit" if cache_hit else "cache miss"
            speaker_display = speaker if speaker is not None else "(default)"
            logger.info(f"[{idx:04d}][{status}][{speaker_display}][{text[:20]}...]")

    logger.info("\nDialogue processing complete")

    # For populate_cache mode or dry_run, recheck all audio files before reporting
    if dry_run or populate_cache:
        recheck_audio_files(reporting_state, cache_folder, silence_threshold, logger)
        print_unified_report(
            reporting_state,
            logger,
            tts_provider_manager,
            silence_checking_enabled=silence_threshold is not None,
            max_misses_to_report=20,
            max_text_length=30,
        )

    return audio_clips, modified_dialogues


def concatenate_audio_clips(audio_clips: List[AudioSegment], output_file: str) -> None:
    """
    Concatenate audio clips using pydub with detailed progress tracking.

    Args:
        audio_clips: List of AudioSegment objects
        output_file: Path for the output audio file
    """
    logger.info(f"\nStarting audio concatenation of {len(audio_clips)} clips")
    logger.info("Memory usage and clip details:")

    total_duration = 0
    for i, clip in enumerate(audio_clips):
        duration_ms = len(clip)
        total_duration += duration_ms
        logger.info(f"Clip {i}: Duration = {duration_ms}ms ({duration_ms/1000:.2f}s)")

    logger.info(
        f"\nTotal duration to process: {total_duration}ms ({total_duration/1000:.2f}s)"
    )

    try:
        logger.info("\nStarting clip concatenation...")
        final_audio = AudioSegment.empty()

        for i, clip in enumerate(audio_clips, 1):
            logger.info(f"Adding clip {i}/{len(audio_clips)} (duration: {len(clip)}ms)")
            final_audio += clip
            logger.info(f"Current total duration: {len(final_audio)}ms")

        logger.info(
            f"\nExporting final audio (duration: {len(final_audio)}ms) to: {output_file}"
        )
        final_audio.export(output_file, format="mp3")
        logger.info("Audio export completed")

        # Verify the output file
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            logger.info(f"Output file size: {file_size/1024/1024:.2f}MB")

            # Try to load the output file as a sanity check
            try:
                verify_audio = AudioSegment.from_mp3(output_file)
                logger.info(
                    f"Output file verification successful. Duration: {len(verify_audio)}ms"
                )
            except Exception as e:
                logger.error(f"Output file verification failed: {e}")
        else:
            logger.warn("Output file was not created")

    except Exception as e:
        logger.error(f"\nError during audio concatenation: {str(e)}")
        traceback.print_exc()
        raise


def main():
    parser = argparse.ArgumentParser(
        description="Generate an audio file from dialogues."
    )
    parser.add_argument(
        "input_file", help="Path to the input JSON file containing dialogues."
    )
    parser.add_argument(
        "--gap",
        type=int,
        default=500,
        help="Gap duration between dialogues in milliseconds (default: 500ms).",
    )
    parser.add_argument(
        "--provider",
        choices=TTSProviderManager.get_available_providers(),
        help="Choose the TTS provider (if not specified in voice config)",
    )
    parser.add_argument(
        "--tts-config", help="Path to YAML configuration file for TTS provider"
    )
    parser.add_argument(
        "--processor-configs",
        nargs="*",
        help="Path(s) to YAML configuration file(s) for text (pre)processors. "
        "Multiple paths can be provided.",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument(
        "--ffmpeg-path",
        help="Path to ffmpeg binary or directory containing ffmpeg binaries",
    )
    parser.add_argument(
        "--check-silence",
        type=float,
        nargs="?",
        const=-40.0,
        metavar="DBFS",
        help="Check audio files for silence. Optional dBFS threshold (default: -40.0)",
    )
    parser.add_argument(
        "--cache-overrides",
        nargs="?",
        const="standalone_speech",
        default="",
        help="Path to audio files that will override cache files if present. "
        'When flag is used without path, defaults to "standalone_speech". '
        "When flag is not used, no overrides are applied.",
    )
    parser.add_argument(
        "--optional-config",
        help="Path to optional configuration file. If not provided, will look for [input_json]_optional_config.yaml",
    )

    # Add mutually exclusive group for additional run modes
    run_mode_group = parser.add_mutually_exclusive_group()
    run_mode_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without generating new audio files",
    )
    run_mode_group.add_argument(
        "--populate-cache",
        action="store_true",
        help="Generate and cache audio files without creating sequence or output files",
    )

    args = parser.parse_args()

    if args.check_silence is not None:
        logger.info(
            f"Silence checking enabled with threshold: {args.check_silence} dBFS"
        )

    # Determine run mode for log file naming
    run_mode = (
        "dry-run"
        if args.dry_run
        else "populate-cache" if args.populate_cache else "generate-output"
    )

    # Create output folders and get paths
    create_sequence = not (args.dry_run or args.populate_cache)
    output_folder, cache_folder, sequence_folder, output_file, log_file = (
        create_output_folders(args.input_file, create_sequence, run_mode)
    )

    # Set up logging
    setup_screenplay_logging(log_file)

    logger.info("Output folders created")

    if create_sequence:
        logger.info(f"Output will be saved to: {output_file}")

    # Verify input file exists
    if not os.path.exists(args.input_file):
        raise FileNotFoundError(f"Input file not found: {args.input_file}")

    # Initialize TTS manager
    tts_manager = TTSProviderManager(args.tts_config, args.provider)
    logger.info("TTS provider manager initialized")

    # Verify TTS config exists if provided
    if args.tts_config and not os.path.exists(args.tts_config):
        raise FileNotFoundError(f"TTS config file not found: {args.tts_config}")

    # Configure ffmpeg
    try:
        configure_ffmpeg(args.ffmpeg_path)
        logger.info("FFMPEG configuration successful")
    except Exception as e:
        logger.error(f"Error configuring FFMPEG: {e}")
        return 1

    logger.info(f"Loading dialogues from: {args.input_file}")
    try:
        dialogues = load_json_chunks(args.input_file)
    except Exception as e:
        logger.error(f"Error loading input file: {e}")
        return 1
    logger.info(f"Loaded {len(dialogues)} dialogues")

    # Initialize processing module with configs
    generated_processor_configs = get_processor_configs(
        args.input_file, args.processor_configs
    )
    processor = TextProcessorManager(generated_processor_configs)
    logger.info(
        f"Processing module initialized with configs: {generated_processor_configs}"
    )

    # Generate and process audio
    logger.info("Generating audio clips")
    audio_clips, modified_dialogues = generate_audio_clips(
        dialogues,
        args.gap,
        tts_manager,
        cache_folder,
        sequence_folder,
        processor,
        args.verbose,
        args.dry_run,
        args.populate_cache,
        args.check_silence,
        args.cache_overrides,
    )

    # Save modified JSON in output folder
    base_name = os.path.splitext(os.path.basename(args.input_file))[0]
    modified_json_path = os.path.join(output_folder, f"{base_name}-modified.json")
    with open(modified_json_path, "w", encoding="utf-8") as f:
        json.dump(modified_dialogues, f, ensure_ascii=False, indent=2)
    logger.info(f"\nModified JSON file generated: {modified_json_path}")

    if not args.dry_run and not args.populate_cache:
        logger.info(f"Concatenating audio clips and saving to: {output_file}")
        concatenate_audio_clips(audio_clips, output_file)
        logger.info(f"Audio file generated: {output_file}")

        # Set ID3 tags if optional config is available
        config_path = args.optional_config
        if not config_path:
            # Try to find the default config file
            input_path = Path(args.input_file)
            base_name = input_path.stem
            default_config_path = (
                input_path.parent / f"{base_name}_optional_config.yaml"
            )
            if default_config_path.exists():
                config_path = str(default_config_path)
                logger.info(f"Found default optional config file: {config_path}")

        if config_path and os.path.exists(config_path):
            from utils.id3_tag_utils import set_id3_tags_from_config

            logger.info(f"Setting ID3 tags from config: {config_path}")
            if set_id3_tags_from_config(output_file, config_path):
                logger.info("ID3 tags set successfully")
            else:
                logger.warning("Failed to set ID3 tags or no tags specified in config")
    elif args.populate_cache:
        logger.info("Cache population completed.")
    else:
        logger.info("Dry run completed. No audio files were generated.")

    logger.info(f"Cache folder: {cache_folder}")
    logger.info(f"Sequence folder: {sequence_folder}")
    logger.info("Main function completed")


if __name__ == "__main__":
    main()
