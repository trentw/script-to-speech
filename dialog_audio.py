from typing import Optional, List, Dict, Tuple
from collections import defaultdict
from dataclasses import dataclass
from text_processors.processor_manager import TextProcessorManager
from datetime import datetime
from pydub import AudioSegment
from tts_providers.tts_provider_manager import TTSProviderManager
from utils.logging import setup_screenplay_logging, get_screenplay_logger
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
class CacheMissInfo:
    """Information about cache misses for a speaker"""
    line_count: int = 0
    char_count: int = 0
    texts: List[str] = None  # Optional, for detailed debugging

    def __post_init__(self):
        if self.texts is None:
            self.texts = []


@dataclass
class SilentClipInfo:
    """Information about silent audio clips"""
    filename_to_info: Dict[str, Tuple[str, float, str, str]
                           ] = None  # cache_filename -> (text, dbfs_level, speaker_display, speaker_id)

    def __post_init__(self):
        if self.filename_to_info is None:
            self.filename_to_info = {}


def configure_ffmpeg(ffmpeg_path: Optional[str] = None) -> None:
    """
    Configure the ffmpeg binary path for pydub and system PATH.

    Args:
        ffmpeg_path: Optional path to ffmpeg binary directory or executable.
                    If not provided, system ffmpeg will be used.

    Raises:
        ValueError: If the provided path is invalid or executables aren't accessible
    """
    if ffmpeg_path:
        ffmpeg_path = os.path.abspath(ffmpeg_path)

        # Add to system PATH
        os.environ["PATH"] = f"{ffmpeg_path}:{os.environ.get('PATH', '')}"

        # Handle both directory and direct executable paths
        if os.path.isdir(ffmpeg_path):
            ffmpeg_executable = os.path.join(ffmpeg_path, 'ffmpeg')
            ffprobe_executable = os.path.join(ffmpeg_path, 'ffprobe')
        else:
            ffmpeg_executable = ffmpeg_path
            ffprobe_executable = os.path.join(
                os.path.dirname(ffmpeg_path), 'ffprobe')

        # Verify executables exist and are executable
        for exe in [ffmpeg_executable, ffprobe_executable]:
            if not os.path.exists(exe):
                raise ValueError(f"Executable not found: {exe}")
            if not os.access(exe, os.X_OK):
                raise ValueError(f"File is not executable: {exe}")

        # Configure pydub
        AudioSegment.converter = ffmpeg_executable
        AudioSegment.ffmpeg = ffmpeg_executable
        AudioSegment.ffprobe = ffprobe_executable

    # Verify ffmpeg works
    try:
        test_file = AudioSegment.silent(duration=1)
        test_file.export("test.mp3", format="mp3")
        os.remove("test.mp3")
    except Exception as e:
        raise RuntimeError("Failed to verify ffmpeg installation") from e


def create_output_folders(input_file: str, create_sequence: bool = True, run_mode: str = "") -> Tuple[str, str, str, str, str]:
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
        main_output_folder, "sequence", f"sequence_{timestamp}")
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
        with open(input_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        raise ValueError(f"Failed to load input file {input_file}: {e}")


def generate_chunk_hash(text: str, speaker: Optional[str]) -> str:
    # Convert None to empty string for hashing purposes
    speaker_str = '' if speaker is None else speaker
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
    speaker = dialogue.get('speaker')
    if speaker is None or speaker.lower() == 'none' or speaker == '':
        return None

    return speaker


def get_audio_dbfs(audio_data: bytes) -> Optional[float]:
    """
    Get the maximum dBFS level of audio data.

    Args:
        audio_data: Raw audio bytes

    Returns:
        Optional[float]: The maximum dBFS level, or None if analysis fails
    """
    try:
        # Convert bytes to AudioSegment
        audio_segment = AudioSegment.from_mp3(io.BytesIO(audio_data))
        return audio_segment.max_dBFS
    except Exception as e:
        logger.error(f"Error analyzing audio: {e}")
        return None


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
    silence_threshold: Optional[float] = None
) -> Tuple[List[AudioSegment], List[Dict]]:
    logger.info("Starting generate_audio_clips function")
    audio_clips = []
    modified_dialogues = []
    existing_files = set(os.listdir(cache_folder))  # Initial cache inventory

    # First run pre-processors
    logger.info("Running pre-processors")
    preprocessed_chunks = processor.preprocess_chunks(dialogues)

    # Track cache misses by speaker
    cache_misses: DefaultDict[Tuple[str, str],
                              CacheMissInfo] = defaultdict(CacheMissInfo)

    # Track silent clips by unique cache file
    silent_clips = SilentClipInfo()

    for idx, dialogue in enumerate(preprocessed_chunks):
        logger.info(f"\nProcessing dialogue {idx}")

        # Process the dialogue
        processed_dialogue, was_modified = processor.process_chunk(dialogue)
        modified_dialogues.append(processed_dialogue)

        speaker = determine_speaker(processed_dialogue)
        text = processed_dialogue.get('text', '')
        dialogue_type = processed_dialogue.get('type', '')

        logger.info(f"Speaker: {speaker}, Type: {dialogue_type}")
        logger.info(f"Text: {text[:50]}...")

        original_hash = generate_chunk_hash(
            dialogue.get('text', ''),
            determine_speaker(dialogue)
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

        cache_hit = cache_filename in existing_files
        logger.info(f"Cache hit: {cache_hit}")

        # Check for empty text - these should be silent
        expect_silence = not text.strip()

        if cache_hit and not expect_silence and silence_threshold is not None:
            # Check cached files for silence if requested
            try:
                with open(cache_filepath, 'rb') as f:
                    audio_data = f.read()
                max_dbfs = get_audio_dbfs(audio_data)
                logger.info(f"Audio level (dBFS): {max_dbfs}")

                if max_dbfs is not None and max_dbfs < silence_threshold:
                    logger.warning(
                        f"Audio level {max_dbfs} dBFS is below threshold {silence_threshold} dBFS")
                    cache_hit = False
                    # Track silent clip if we haven't seen this cache file before
                    if cache_filename not in silent_clips.filename_to_info:
                        speaker_display = speaker if speaker is not None else "(default)"
                        silent_clips.filename_to_info[cache_filename] = (
                            text, max_dbfs, speaker_display, speaker_id)
            except Exception as e:
                logger.error(f"Error checking audio file: {e}")
                cache_hit = False

        if not cache_hit:
            # Track cache miss information
            speaker_display = speaker if speaker is not None else "(default)"
            cache_misses[(speaker_display, speaker_id)].line_count += 1
            cache_misses[(speaker_display, speaker_id)].char_count += len(text)
            if verbose:
                cache_misses[(speaker_display, speaker_id)].texts.append(text)

        if not dry_run:
            audio_data = None
            if cache_hit:
                logger.info("Using cached audio file")
                try:
                    with open(cache_filepath, 'rb') as f:
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
                        logger.info(
                            "Creating intentional silent audio for empty text")
                        silent_segment = AudioSegment.silent(duration=10)
                        audio_data = silent_segment.export(format="mp3").read()
                    else:
                        # Generate audio normally for non-empty text
                        audio_data = tts_provider_manager.generate_audio(
                            speaker, text)

                        # Check newly generated audio for silence if requested
                        if silence_threshold is not None:
                            max_dbfs = get_audio_dbfs(audio_data)
                            logger.info(
                                f"Generated audio level (dBFS): {max_dbfs}")
                            if max_dbfs is not None and max_dbfs < silence_threshold:
                                logger.warning(
                                    f"Generated audio level {max_dbfs} dBFS is below threshold {silence_threshold} dBFS")
                                # Track silent clip if we haven't seen this cache file before
                                if cache_filename not in silent_clips.filename_to_info:
                                    speaker_display = speaker if speaker is not None else "(default)"
                                    silent_clips.filename_to_info[cache_filename] = (
                                        text, max_dbfs, speaker_display, speaker_id)

                    logger.info("Audio generated")

                    # Save to cache
                    with open(cache_filepath, 'wb') as f:
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
                    with open(sequence_filepath, 'wb') as f:
                        f.write(audio_data)
                    logger.info(
                        f"Audio saved to sequence folder: {sequence_filepath}")

                    # Add to audio clips
                    audio_segment = AudioSegment.from_mp3(
                        io.BytesIO(audio_data))
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
            logger.info(
                f"[{idx:04d}][{status}][{speaker_display}][{text[:20]}...]")

    logger.info("\nDialogue processing complete")

    if dry_run or populate_cache:
        if not cache_misses:
            logger.info(
                "\nAll audio clips are cached. No new audio generation needed.")
        else:
            logger.info(
                "\nCache misses (audio that would need to be generated):")
            for (speaker_display, speaker_id), info in sorted(cache_misses.items()):
                logger.info(
                    f"- {speaker_display} ({speaker_id}): {info.line_count} lines ({info.char_count} characters)")
                if verbose:
                    for text in info.texts:
                        logger.info(f"  • {text[:50]}...")

            logger.info(
                f"\nTotal unique speakers requiring generation: {len(cache_misses)}")
            total_lines = sum(
                info.line_count for info in cache_misses.values())
            total_chars = sum(
                info.char_count for info in cache_misses.values())
            logger.info(f"Total lines to generate: {total_lines}")
            logger.info(f"Total characters to generate: {total_chars}")

    # Report silent clips if silence checking was enabled
    if silence_threshold is not None and silent_clips.filename_to_info:
        logger.info("\nSilent clips detected:")

        # For populate_cache mode, recheck all clips before reporting
        if populate_cache:
            still_silent = {}
            for cache_filename, (text, dbfs, speaker_display, speaker_id) in silent_clips.filename_to_info.items():
                cache_filepath = os.path.join(cache_folder, cache_filename)
                try:
                    with open(cache_filepath, 'rb') as f:
                        audio_data = f.read()
                    current_dbfs = get_audio_dbfs(audio_data)
                    if current_dbfs is not None and current_dbfs < silence_threshold:
                        still_silent[cache_filename] = (
                            text, current_dbfs, speaker_display, speaker_id)
                except Exception as e:
                    logger.error(
                        f"Error rechecking audio file {cache_filepath}: {e}")

            silent_clips.filename_to_info = still_silent

        # Group by speaker for output
        by_speaker: Dict[Tuple[str, str],
                         List[Tuple[str, float, str]]] = defaultdict(list)
        for cache_filename, (text, dbfs, speaker_display, speaker_id) in silent_clips.filename_to_info.items():
            by_speaker[(speaker_display, speaker_id)].append(
                (text, dbfs, cache_filename))

        # Print results
        for (speaker_display, speaker_id), clips in sorted(by_speaker.items()):
            logger.info(
                f"\n- {speaker_display} ({speaker_id}): {len(clips)} clips")
            for text, dbfs, cache_filename in sorted(clips):
                logger.info(f"  • dBFS: {dbfs}")
                logger.info(f"    Cache: {cache_filename}")
                logger.info(f"    Text: \"{text}\"")

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
        logger.info(
            f"Clip {i}: Duration = {duration_ms}ms ({duration_ms/1000:.2f}s)")

    logger.info(
        f"\nTotal duration to process: {total_duration}ms ({total_duration/1000:.2f}s)")

    try:
        logger.info("\nStarting clip concatenation...")
        final_audio = AudioSegment.empty()

        for i, clip in enumerate(audio_clips, 1):
            logger.info(
                f"Adding clip {i}/{len(audio_clips)} (duration: {len(clip)}ms)")
            final_audio += clip
            logger.info(f"Current total duration: {len(final_audio)}ms")

        logger.info(
            f"\nExporting final audio (duration: {len(final_audio)}ms) to: {output_file}")
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
                    f"Output file verification successful. Duration: {len(verify_audio)}ms")
            except Exception as e:
                logger.error(f"Output file verification failed: {e}")
        else:
            logger.warn("Output file was not created")

    except Exception as e:
        logger.error(f"\nError during audio concatenation: {str(e)}")
        traceback.print_exc()
        raise


def handle_yaml_generation(
    tts_manager: TTSProviderManager,
    input_file: str,
    processing_config: Optional[str],
    provider: Optional[str] = None,
    populate_yaml: Optional[str] = None
) -> int:
    """
    Handle YAML configuration generation or population.

    Args:
        tts_manager: Initialized TTSProviderManager instance
        input_file: Path to input JSON file
        processing_config: Path to processing configuration file
        provider: Optional provider name for generation
        populate_yaml: Optional path to YAML file to populate

    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    processor = TextProcessorManager(processing_config)

    try:
        # Load and process chunks
        chunks = load_json_chunks(input_file)
        processed_chunks = processor.process_chunks(chunks)
    except Exception as e:
        logger.error(f"Error processing input file: {e}")
        return 1

    try:
        if populate_yaml:
            # Handle population case
            logger.info(
                f"Populating provider-specific fields in YAML: {populate_yaml}")
            input_dir = os.path.dirname(populate_yaml)
            base_name = os.path.splitext(os.path.basename(populate_yaml))[0]
            yaml_output = os.path.join(
                input_dir, f"{base_name}_populated.yaml")

            tts_manager.update_yaml_with_provider_fields_preserving_comments(
                populate_yaml, yaml_output, processed_chunks)
            logger.info(
                f"Updated YAML configuration generated: {yaml_output}")
        else:
            # Handle generation case
            logger.info("Generating YAML configuration")
            input_dir = os.path.dirname(input_file)
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            yaml_output = os.path.join(
                input_dir, f"{base_name}_voice_config.yaml")

            tts_manager.generate_yaml_config(
                processed_chunks, yaml_output, provider)
            logger.info(
                f"YAML configuration template generated: {yaml_output}")

        return 0

    except Exception as e:
        action = "populating" if populate_yaml else "generating"
        logger.error(f"Error {action} YAML configuration: {e}")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description='Generate an audio file from dialogues.')
    parser.add_argument(
        'input_file', help='Path to the input JSON file containing dialogues.')
    parser.add_argument('--gap', type=int, default=500,
                        help='Gap duration between dialogues in milliseconds (default: 500ms).')
    parser.add_argument('--provider', choices=TTSProviderManager.get_available_providers(),
                        help='Choose the TTS provider (if not specified in voice config)')
    parser.add_argument(
        '--tts-config', help='Path to YAML configuration file for TTS provider')
    parser.add_argument('--processing-config',
                        help='Path to YAML configuration file for processing module')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable verbose output')
    parser.add_argument('--ffmpeg-path',
                        help='Path to ffmpeg binary or directory containing ffmpeg binaries')
    parser.add_argument('--check-silence', type=float, nargs='?', const=-40.0, metavar='DBFS',
                        help='Check audio files for silence. Optional dBFS threshold (default: -40.0)')

    # Add mutually exlusive group for additional run modes
    run_mode_group = parser.add_mutually_exclusive_group()
    run_mode_group.add_argument('--dry-run', action='store_true',
                                help='Perform a dry run without generating new audio files')
    run_mode_group.add_argument('--populate-cache', action='store_true',
                                help='Generate and cache audio files without creating sequence or output files')

    # Add mutually exclusive group for YAML operations
    yaml_group = parser.add_mutually_exclusive_group()
    yaml_group.add_argument('--generate-yaml', action='store_true',
                            help='Generate a template YAML configuration file')
    yaml_group.add_argument('--populate-multi-provider-yaml',
                            help='Path to YAML file to populate with provider-specific fields')

    args = parser.parse_args()

    if args.check_silence is not None:
        logger.info(
            f"Silence checking enabled with threshold: {args.check_silence} dBFS")

    # Determine run mode for log file naming
    run_mode = "dry-run" if args.dry_run else "populate-cache" if args.populate_cache else "generate-output"

    # Create output folders and get paths
    create_sequence = not (args.dry_run or args.populate_cache)
    output_folder, cache_folder, sequence_folder, output_file, log_file = create_output_folders(
        args.input_file, create_sequence, run_mode)

    # Set up logging
    setup_screenplay_logging(log_file)

    logger.info("Output folders created")

    if create_sequence:
        logger.info(f"Output will be saved to: {output_file}")

    # Verify input file exists
    if not os.path.exists(args.input_file):
        raise FileNotFoundError(f"Input file not found: {args.input_file}")

    # Verify processing config exists if provided
    if args.processing_config and not os.path.exists(args.processing_config):
        raise FileNotFoundError(
            f"Processing config file not found: {args.processing_config}")

    # Initialize TTS manager
    tts_manager = TTSProviderManager(args.tts_config, args.provider)
    logger.info("TTS provider manager initialized")

    # Handle YAML generation/population cases
    if args.generate_yaml or args.populate_multi_provider_yaml:
        return handle_yaml_generation(
            tts_manager=tts_manager,
            input_file=args.input_file,
            processing_config=args.processing_config,
            provider=args.provider if args.generate_yaml else None,
            populate_yaml=args.populate_multi_provider_yaml if args.populate_multi_provider_yaml else None
        )

    # Verify TTS config exists if provided
    if args.tts_config and not os.path.exists(args.tts_config):
        raise FileNotFoundError(
            f"TTS config file not found: {args.tts_config}")

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

    # Initialize processing module
    processor = TextProcessorManager(args.processing_config)
    logger.info("Processing module initialized")

    # Generate and process audio
    logger.info("Generating audio clips")
    audio_clips, modified_dialogues = generate_audio_clips(
        dialogues, args.gap, tts_manager, cache_folder, sequence_folder,
        processor, args.verbose, args.dry_run, args.populate_cache, args.check_silence)

    # Save modified JSON in output folder
    base_name = os.path.splitext(os.path.basename(args.input_file))[0]
    modified_json_path = os.path.join(
        output_folder, f"{base_name}-modified.json")
    with open(modified_json_path, 'w', encoding='utf-8') as f:
        json.dump(modified_dialogues, f, ensure_ascii=False, indent=2)
    logger.info(f'Modified JSON file generated: {modified_json_path}')

    if not args.dry_run and not args.populate_cache:
        logger.info(f"Concatenating audio clips and saving to: {output_file}")
        concatenate_audio_clips(audio_clips, output_file)
        logger.info(f'Audio file generated: {output_file}')
    elif args.populate_cache:
        logger.info('Cache population completed.')
    else:
        logger.info('Dry run completed. No audio files were generated.')

    logger.info(f'Cache folder: {cache_folder}')
    logger.info(f'Sequence folder: {sequence_folder}')
    logger.info("Main function completed")


if __name__ == '__main__':
    main()
