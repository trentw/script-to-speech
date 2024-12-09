from tts_provider import TTSProvider
from typing import Optional, List, Dict, Tuple
from collections import defaultdict
from dataclasses import dataclass
from processing_module import ProcessingModule
from datetime import datetime
from elevenlabs_provider import ElevenLabsProvider
from pyttsx3_provider import Pyttsx3Provider
from pydub import AudioSegment
import hashlib
import argparse
import io
import json
import os
import sys
import traceback

# Use a less common delimiter
DELIMITER = "~~"


@dataclass
class CacheMissInfo:
    """Information about cache misses for a speaker"""
    line_count: int = 0
    char_count: int = 0
    texts: List[str] = None  # Optional, for detailed debugging

    def __post_init__(self):
        if self.texts is None:
            self.texts = []


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


def load_dialogues(input_file: str) -> List[Dict]:
    with open(input_file, 'r', encoding='utf-8') as f:
        dialogues = json.load(f)
    return dialogues


def generate_chunk_hash(text: str, speaker: Optional[str]) -> str:
    # Convert None to empty string for hashing purposes
    speaker_str = '' if speaker is None else speaker
    return hashlib.md5(f"{text}{speaker_str}".encode()).hexdigest()


def create_output_folders(input_file: str, output_folder: Optional[str] = None) -> Tuple[str, str, str]:
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if output_folder is None:
        output_folder = f"{base_name}_output"

    cache_folder = os.path.join(output_folder, "cache")
    sequence_folder = os.path.join(output_folder, f"sequence_{timestamp}")

    os.makedirs(cache_folder, exist_ok=True)
    os.makedirs(sequence_folder, exist_ok=True)

    return output_folder, cache_folder, sequence_folder


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
    if speaker is None or speaker.lower() == 'none':
        return None

    return speaker


def generate_audio_clips(
    dialogues: List[Dict],
    gap_duration_ms: int,
    tts_provider: TTSProvider,
    cache_folder: str,
    sequence_folder: str,
    processor: ProcessingModule,
    verbose: bool = False,
    dry_run: bool = False
) -> Tuple[List[AudioSegment], List[Dict]]:
    print("Starting generate_audio_clips function")
    audio_clips = []
    modified_dialogues = []
    existing_files = set(os.listdir(cache_folder))
    provider_id = tts_provider.get_provider_identifier()
    print(f"Provider ID: {provider_id}")

    # Track cache misses by speaker
    cache_misses: DefaultDict[Tuple[str, str],
                              CacheMissInfo] = defaultdict(CacheMissInfo)

    for idx, dialogue in enumerate(dialogues):
        print(f"\nProcessing dialogue {idx}")

        # Process the dialogue
        processed_dialogue, was_modified = processor.process_chunk(dialogue)
        modified_dialogues.append(processed_dialogue)

        speaker = determine_speaker(processed_dialogue)
        text = processed_dialogue.get('text', '')
        dialogue_type = processed_dialogue.get('type', '')

        print(f"Speaker: {speaker}, Type: {dialogue_type}")
        print(f"Text: {text[:50]}...")

        original_hash = generate_chunk_hash(
            dialogue.get('text', ''),
            determine_speaker(dialogue)
        )
        processed_hash = generate_chunk_hash(text, speaker)
        print(f"Original hash: {original_hash}")
        print(f"Processed hash: {processed_hash}")

        speaker_id = tts_provider.get_speaker_identifier(speaker)
        print(f"Speaker ID: {speaker_id}")

        cache_filename = f"{original_hash}{DELIMITER}{processed_hash}{DELIMITER}{provider_id}{DELIMITER}{speaker_id}.mp3"
        sequence_filename = f"{idx:04d}{DELIMITER}{original_hash}{DELIMITER}{processed_hash}{DELIMITER}{provider_id}{DELIMITER}{speaker_id}.mp3"

        cache_filepath = os.path.join(cache_folder, cache_filename)
        sequence_filepath = os.path.join(sequence_folder, sequence_filename)

        print(f"Cache filepath: {cache_filepath}")
        print(f"Sequence filepath: {sequence_filepath}")

        cache_hit = cache_filename in existing_files
        print(f"Cache hit: {cache_hit}")

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
                print("Using cached audio file")
                try:
                    with open(cache_filepath, 'rb') as f:
                        audio_data = f.read()
                    print("Successfully read cached audio")
                except Exception as e:
                    print(f"Error reading cached audio: {e}")
                    cache_hit = False  # Force regeneration

            if not cache_hit:
                print("Generating new audio file")
                try:
                    if not text.strip():
                        # Create a very short silent audio for empty text
                        print("Creating silent audio for empty text")
                        silent_segment = AudioSegment.silent(
                            duration=10)  # 10ms of silence
                        audio_data = silent_segment.export(format="mp3").read()
                    else:
                        # Generate audio normally for non-empty text
                        audio_data = tts_provider.generate_audio(speaker, text)
                    print("Audio generated")

                    # Save to cache
                    with open(cache_filepath, 'wb') as f:
                        f.write(audio_data)
                    print(f"Audio saved to cache: {cache_filepath}")
                except Exception as e:
                    print(f"Error generating new audio: {e}")

            if audio_data:
                try:
                    # Save to sequence folder
                    with open(sequence_filepath, 'wb') as f:
                        f.write(audio_data)
                    print(
                        f"Audio saved to sequence folder: {sequence_filepath}")

                    # Add to audio clips
                    audio_segment = AudioSegment.from_mp3(
                        io.BytesIO(audio_data))
                    audio_clips.append(audio_segment)
                    print("Audio added to clips list")

                    # Only add gap if this isn't empty text and isn't the last item
                    if idx < len(dialogues) - 1 and text.strip():
                        print("Adding gap between dialogues")
                        gap = AudioSegment.silent(duration=gap_duration_ms)
                        audio_clips.append(gap)
                        print("Gap added")
                except Exception as e:
                    print(f"Error processing audio data: {e}")

        if verbose or (dry_run and not cache_hit):
            status = "cache hit" if cache_hit else "cache miss"
            speaker_display = speaker if speaker is not None else "(default)"
            print(f"[{idx:04d}][{status}][{speaker_display}][{text[:20]}...]")

    print("\nDialogue processing complete")

    if dry_run:
        if not cache_misses:
            print("\nAll audio clips are cached. No new audio generation needed.")
        else:
            print("\nCache misses (audio that would need to be generated):")
            for (speaker_display, speaker_id), info in sorted(cache_misses.items()):
                print(
                    f"- {speaker_display} ({speaker_id}): {info.line_count} lines ({info.char_count} characters)")
                if verbose:
                    for text in info.texts:
                        print(f"  • {text[:50]}...")

            print(
                f"\nTotal unique speakers requiring generation: {len(cache_misses)}")
            total_lines = sum(
                info.line_count for info in cache_misses.values())
            total_chars = sum(
                info.char_count for info in cache_misses.values())
            print(f"Total lines to generate: {total_lines}")
            print(f"Total characters to generate: {total_chars}")

    return audio_clips, modified_dialogues


def concatenate_audio_clips(audio_clips: List[AudioSegment], output_file: str) -> None:
    """
    Concatenate audio clips using pydub with detailed progress tracking.

    Args:
        audio_clips: List of AudioSegment objects
        output_file: Path for the output audio file
    """
    print(f"\nStarting audio concatenation of {len(audio_clips)} clips")
    print("Memory usage and clip details:")

    total_duration = 0
    for i, clip in enumerate(audio_clips):
        duration_ms = len(clip)
        total_duration += duration_ms
        print(f"Clip {i}: Duration = {duration_ms}ms ({duration_ms/1000:.2f}s)")

    print(
        f"\nTotal duration to process: {total_duration}ms ({total_duration/1000:.2f}s)")

    try:
        print("\nStarting clip concatenation...")
        final_audio = AudioSegment.empty()

        for i, clip in enumerate(audio_clips, 1):
            print(
                f"Adding clip {i}/{len(audio_clips)} (duration: {len(clip)}ms)")
            final_audio += clip
            print(f"Current total duration: {len(final_audio)}ms")

        print(
            f"\nExporting final audio (duration: {len(final_audio)}ms) to: {output_file}")
        final_audio.export(output_file, format="mp3")
        print("Audio export completed")

        # Verify the output file
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            print(f"Output file size: {file_size/1024/1024:.2f}MB")

            # Try to load the output file as a sanity check
            try:
                verify_audio = AudioSegment.from_mp3(output_file)
                print(
                    f"Output file verification successful. Duration: {len(verify_audio)}ms")
            except Exception as e:
                print(f"Warning: Output file verification failed: {e}")
        else:
            print("Warning: Output file was not created")

    except Exception as e:
        print(f"\nError during audio concatenation: {str(e)}")
        traceback.print_exc()
        raise


def main():
    print("Starting main function")
    parser = argparse.ArgumentParser(
        description='Generate an audio file from dialogues.')
    parser.add_argument(
        'input_file', help='Path to the input JSON file containing dialogues.')
    parser.add_argument(
        'output_file', help='Path for the output audio file (will be saved as .mp3)')
    parser.add_argument('--gap', type=int, default=500,
                        help='Gap duration between dialogues in milliseconds (default: 500ms).')
    parser.add_argument('--provider', choices=['pyttsx3', 'elevenlabs'],
                        default='pyttsx3', help='Choose the TTS provider (default: pyttsx3)')
    parser.add_argument(
        '--tts-config', help='Path to YAML configuration file for TTS provider')
    parser.add_argument('--processing-config',
                        help='Path to YAML configuration file for processing module')
    parser.add_argument('--generate-yaml', action='store_true',
                        help='Generate a template YAML configuration file')
    parser.add_argument('--output-folder',
                        help='Specify custom output folder name')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable verbose output')
    parser.add_argument('--dry-run', action='store_true',
                        help='Perform a dry run without generating new audio files')
    parser.add_argument('--ffmpeg-path',
                        help='Path to ffmpeg binary or directory containing ffmpeg binaries')

    args = parser.parse_args()

    # Configure ffmpeg
    try:
        configure_ffmpeg(args.ffmpeg_path)
        print("FFMPEG configuration successful")
    except Exception as e:
        print(f"Error configuring FFMPEG: {e}")
        return 1

    # Ensure the output file has .mp3 extension
    output_file = args.output_file
    if not output_file.lower().endswith('.mp3'):
        output_file = f"{os.path.splitext(output_file)[0]}.mp3"
        print(f"Output file name adjusted to: {output_file}")

    if args.generate_yaml:
        print("Generating YAML configuration")
        yaml_output = args.input_file.rsplit('.', 1)[0] + '_voice_config.yaml'
        ElevenLabsProvider.generate_yaml_config(args.input_file, yaml_output)
        print(f"YAML configuration template generated: {yaml_output}")
        return

    print(f"Initializing TTS provider: {args.provider}")
    if args.provider == 'pyttsx3':
        tts_provider = Pyttsx3Provider()
    elif args.provider == 'elevenlabs':
        tts_provider = ElevenLabsProvider()
    else:
        raise ValueError("Invalid TTS provider specified")

    tts_provider.initialize(args.tts_config)
    print("TTS provider initialized")

    print(f"Loading dialogues from: {args.input_file}")
    dialogues = load_dialogues(args.input_file)
    print(f"Loaded {len(dialogues)} dialogues")

    print("Creating output folders")
    output_folder, cache_folder, sequence_folder = create_output_folders(
        args.input_file, args.output_folder)

    # Initialize processing module
    processor = ProcessingModule(args.processing_config)
    print("Processing module initialized")

    print("Generating audio clips")
    audio_clips, modified_dialogues = generate_audio_clips(
        dialogues, args.gap, tts_provider, cache_folder, sequence_folder, processor, args.verbose, args.dry_run)

    if not args.dry_run:
        print(f"Concatenating audio clips and saving to: {output_file}")
        concatenate_audio_clips(audio_clips, output_file)
        print(f'Audio file generated: {output_file}')

        # Save modified JSON
        modified_json_path = os.path.join(
            output_folder, f"{os.path.splitext(os.path.basename(args.input_file))[0]}-modified.json")
        with open(modified_json_path, 'w', encoding='utf-8') as f:
            json.dump(modified_dialogues, f, ensure_ascii=False, indent=2)
        print(f'Modified JSON file generated: {modified_json_path}')
    else:
        print('Dry run completed. No audio files were generated.')

    print(f'Cache folder: {cache_folder}')
    print(f'Sequence folder: {sequence_folder}')
    print("Main function completed")


if __name__ == '__main__':
    main()
