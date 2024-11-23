import json
import os
import argparse
from pydub import AudioSegment
from pyttsx3_provider import Pyttsx3Provider
from elevenlabs_provider import ElevenLabsProvider
from datetime import datetime


def load_dialogues(input_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        dialogues = json.load(f)
    return dialogues


def generate_audio_clips(dialogues, gap_duration_ms, tts_provider, preserve_files, output_folder):
    audio_clips = []
    for idx, dialogue in enumerate(dialogues):
        speaker = dialogue.get('speaker', 'none')
        text = dialogue.get('text', '')
        dialogue_type = dialogue.get('type', '')

        if dialogue_type in ['scene header', 'scene description', 'dialog modifier']:
            speaker = 'none'

        voice = tts_provider.get_voice_for_speaker(speaker)
        tts_provider.set_voice(voice)

        if preserve_files:
            audio_file = os.path.join(
                output_folder, f'clip_{idx:04d}_{speaker}_{dialogue_type}.wav')
        else:
            audio_file = f'clip_{idx:04d}.wav'

        tts_provider.generate_audio(text, audio_file)

        audio_segment = AudioSegment.from_file(audio_file)
        audio_clips.append(audio_segment)

        if idx < len(dialogues) - 1:
            gap = AudioSegment.silent(duration=gap_duration_ms)
            audio_clips.append(gap)

        if not preserve_files:
            os.remove(audio_file)

    return audio_clips


def concatenate_audio_clips(audio_clips, output_file):
    final_audio = AudioSegment.empty()
    for clip in audio_clips:
        final_audio += clip
    final_audio.export(output_file, format='wav')


def print_available_voices(provider):
    voices = provider.get_available_voices()
    print("Available voices:")
    for voice in voices:
        print(f"- Name: {voice.name}")
        print(f"  ID: {voice.voice_id}")
        print(f"  Labels: {voice.labels}")
        print("---")


def create_output_folder(input_file):
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_name = f"{base_name}_{timestamp}"
    os.makedirs(folder_name, exist_ok=True)
    return folder_name


def main():
    parser = argparse.ArgumentParser(
        description='Generate an audio file from dialogues.')
    parser.add_argument(
        'input_file', help='Path to the input JSON file containing dialogues.')
    parser.add_argument('output_file', help='Path for the output audio file.')
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
    parser.add_argument('--preserve-files', action='store_true',
                        help='Preserve individual audio files for debugging')

    args = parser.parse_args()

    if args.generate_yaml:
        yaml_output = args.input_file.rsplit('.', 1)[0] + '_voice_config.yaml'
        ElevenLabsProvider.generate_yaml_config(args.input_file, yaml_output)
        print(f"YAML configuration template generated: {yaml_output}")
        return

    if args.provider == 'pyttsx3':
        tts_provider = Pyttsx3Provider()
    elif args.provider == 'elevenlabs':
        tts_provider = ElevenLabsProvider(yaml_config=args.yaml_config)
    else:
        raise ValueError("Invalid TTS provider specified")

    tts_provider.initialize()

    if args.list_voices:
        print_available_voices(tts_provider)
        return

    dialogues = load_dialogues(args.input_file)

    if args.preserve_files:
        output_folder = create_output_folder(args.input_file)
        print(f"Individual audio files will be preserved in: {output_folder}")
    else:
        output_folder = None

    audio_clips = generate_audio_clips(
        dialogues, args.gap, tts_provider, args.preserve_files, output_folder)

    concatenate_audio_clips(audio_clips, args.output_file)

    print(f'Audio file generated: {args.output_file}')


if __name__ == '__main__':
    main()
