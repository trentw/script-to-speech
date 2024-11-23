import json
import os
import io
import argparse
import hashlib
from pydub import AudioSegment
from pyttsx3_provider import Pyttsx3Provider
from elevenlabs_provider import ElevenLabsProvider
from datetime import datetime

# Use a less common delimiter
DELIMITER = "~~"


def load_dialogues(input_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        dialogues = json.load(f)
    return dialogues


def generate_chunk_hash(text, speaker):
    return hashlib.md5(f"{text}{speaker}".encode()).hexdigest()


def create_output_folders(input_file, output_folder=None):
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if output_folder is None:
        output_folder = f"{base_name}_output"

    cache_folder = os.path.join(output_folder, "cache")
    sequence_folder = os.path.join(output_folder, f"sequence_{timestamp}")

    os.makedirs(cache_folder, exist_ok=True)
    os.makedirs(sequence_folder, exist_ok=True)

    return output_folder, cache_folder, sequence_folder


def generate_audio_clips(dialogues, gap_duration_ms, tts_provider, cache_folder, sequence_folder, verbose=False, dry_run=False):
    print("Starting generate_audio_clips function")
    audio_clips = []
    existing_files = set(os.listdir(cache_folder))
    provider_id = tts_provider.get_provider_identifier()
    print(f"Provider ID: {provider_id}")

    for idx, dialogue in enumerate(dialogues):
        print(f"\nProcessing dialogue {idx}")
        speaker = dialogue.get('speaker', 'none')
        text = dialogue.get('text', '')
        dialogue_type = dialogue.get('type', '')

        print(f"Speaker: {speaker}, Type: {dialogue_type}")
        print(f"Text: {text[:50]}...")

        if dialogue_type in ['scene header', 'scene description', 'dialog modifier']:
            speaker = 'none'
            print("Speaker set to 'none' based on dialogue type")

        chunk_hash = generate_chunk_hash(text, speaker)
        print(f"Generated chunk hash: {chunk_hash}")

        tts_speaker_id = tts_provider.get_speaker_identifier(speaker)
        print(f"TTS Speaker ID: {tts_speaker_id}")

        cache_filename = f"{chunk_hash}{DELIMITER}{provider_id}{DELIMITER}{tts_speaker_id}.mp3"
        sequence_filename = f"{idx:04d}{DELIMITER}{chunk_hash}{DELIMITER}{provider_id}{DELIMITER}{tts_speaker_id}.mp3"

        cache_filepath = os.path.join(cache_folder, cache_filename)
        sequence_filepath = os.path.join(sequence_folder, sequence_filename)

        print(f"Cache filepath: {cache_filepath}")
        print(f"Sequence filepath: {sequence_filepath}")

        cache_hit = cache_filename in existing_files
        print(f"Cache hit: {cache_hit}")

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
                    voice = tts_provider.get_voice_for_speaker(speaker)
                    print(f"Got voice for speaker: {voice}")
                    tts_provider.set_voice(voice)
                    print("Voice set")
                    audio_data = tts_provider.generate_audio(text)
                    print(f"Audio generated")

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

                    if idx < len(dialogues) - 1:
                        print("Adding gap between dialogues")
                        gap = AudioSegment.silent(duration=gap_duration_ms)
                        audio_clips.append(gap)
                        print("Gap added")
                except Exception as e:
                    print(f"Error processing audio data: {e}")

        if verbose or (dry_run and not cache_hit):
            status = "cache hit" if cache_hit else "cache miss"
            print(f"[{idx:04d}][{status}][{speaker}][{text[:20]}...]")

    print("Finished processing all dialogues")
    return audio_clips


def concatenate_audio_clips(audio_clips, output_file):
    print("Starting audio concatenation")
    final_audio = AudioSegment.empty()
    for clip in audio_clips:
        final_audio += clip

    print(f"Exporting final audio to: {output_file}")
    final_audio.export(output_file, format="mp3")
    print("Audio concatenation completed")


def print_available_voices(provider):
    voices = provider.get_available_voices()
    print("Available voices:")
    for voice in voices:
        print(f"- Name: {voice.name}")
        print(f"  ID: {voice.voice_id}")
        print(f"  Labels: {voice.labels}")
        print("---")


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
        '--yaml-config', help='Path to YAML configuration file for ElevenLabs voices')
    parser.add_argument('--generate-yaml', action='store_true',
                        help='Generate a template YAML configuration file')
    parser.add_argument('--list-voices', action='store_true',
                        help='List available voices for the selected provider')
    parser.add_argument('--output-folder',
                        help='Specify custom output folder name')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable verbose output')
    parser.add_argument('--dry-run', action='store_true',
                        help='Perform a dry run without generating new audio files')

    print("Parsing arguments")
    args = parser.parse_args()

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
        tts_provider = ElevenLabsProvider(yaml_config=args.yaml_config)
    else:
        raise ValueError("Invalid TTS provider specified")

    tts_provider.initialize()
    print("TTS provider initialized")

    if args.list_voices:
        print("Listing available voices")
        print_available_voices(tts_provider)
        return

    print(f"Loading dialogues from: {args.input_file}")
    dialogues = load_dialogues(args.input_file)
    print(f"Loaded {len(dialogues)} dialogues")

    print("Creating output folders")
    output_folder, cache_folder, sequence_folder = create_output_folders(
        args.input_file, args.output_folder)

    print("Generating audio clips")
    audio_clips = generate_audio_clips(
        dialogues, args.gap, tts_provider, cache_folder, sequence_folder, args.verbose, args.dry_run)

    if not args.dry_run:
        print(f"Concatenating audio clips and saving to: {output_file}")
        concatenate_audio_clips(audio_clips, output_file)
        print(f'Audio file generated: {output_file}')
    else:
        print('Dry run completed. No audio files were generated.')

    print(f'Cache folder: {cache_folder}')
    print(f'Sequence folder: {sequence_folder}')
    print("Main function completed")


if __name__ == '__main__':
    main()
