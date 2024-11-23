import unicodedata
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs
from tts_provider import TTSProvider
import os
import random
import yaml
import json
from collections import Counter


def normalize_unicode(s):
    return unicodedata.normalize('NFKC', s)


class ElevenLabsProvider(TTSProvider):
    def __init__(self, yaml_config=None):
        self.client = None
        self.available_voices = None
        self.speaker_voice_map = {}
        self.current_voice = None
        self.yaml_config = yaml_config
        self.default_voice = None
        self.used_voice_ids = set()

    def initialize(self):
        api_key = os.environ.get("ELEVEN_API_KEY")
        if not api_key:
            raise ValueError("ELEVEN_API_KEY environment variable is not set")
        self.client = ElevenLabs(api_key=api_key)
        self.refresh_voices()
        if self.yaml_config:
            self.load_yaml_config()

    def refresh_voices(self):
        response = self.client.voices.get_all()
        self.available_voices = response.voices
        self.voice_dict = {
            voice.voice_id: voice for voice in self.available_voices}
        # Debug print
        print(
            f"Available voices in library: {[{voice.voice_id: voice.name} for voice in self.available_voices]}")

    def get_speaker_identifier(self, speaker):
        voice = self.get_voice_for_speaker(speaker)
        return voice.voice_id if hasattr(voice, 'voice_id') else voice

    def get_provider_identifier(self):
        return "elevenlabs"

    def load_yaml_config(self):
        with open(self.yaml_config, 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)

        print(f"Loaded config: {config}")  # Debug print

        # Load default voice
        default_voice_id = config.get('default', '')
        if default_voice_id:
            self.default_voice = self.voice_dict.get(
                default_voice_id, default_voice_id)
            self.used_voice_ids.add(default_voice_id)
        else:
            self.default_voice = random.choice(self.available_voices)
            self.used_voice_ids.add(self.default_voice.voice_id)

        # Load speaker voices
        for speaker, voice_id in config.items():
            if speaker == 'default':
                continue
            normalized_speaker = normalize_unicode(speaker)
            # Debug print
            print(
                f"Processing speaker: '{normalized_speaker}', Voice ID: '{voice_id}'")
            if voice_id:
                if voice_id in self.voice_dict:
                    self.speaker_voice_map[normalized_speaker] = self.voice_dict[voice_id]
                else:
                    print(
                        f"Voice ID '{voice_id}' not in library. Using as-is.")
                    self.speaker_voice_map[normalized_speaker] = voice_id
                self.used_voice_ids.add(voice_id)
            else:
                print(
                    f"Warning: No voice ID provided for speaker '{normalized_speaker}'. Assigning a random voice.")
                self.assign_random_voice(normalized_speaker)

        print("Loaded speaker_voice_map:")
        for speaker, voice in self.speaker_voice_map.items():
            print(
                f"  '{speaker}': {voice if isinstance(voice, str) else voice.voice_id}")

    def assign_random_voice(self, speaker):
        available_voices = [
            v for v in self.available_voices if v.voice_id not in self.used_voice_ids]
        if not available_voices:
            available_voices = self.available_voices
        voice = random.choice(available_voices)
        self.speaker_voice_map[speaker] = voice
        self.used_voice_ids.add(voice.voice_id)

    def get_available_voices(self):
        return self.available_voices

    def get_voice_for_speaker(self, speaker):
        normalized_speaker = normalize_unicode(speaker)
        # Debug print
        print(f"Getting voice for speaker: '{normalized_speaker}'")
        # Debug print
        print(f"Unicode code points: {[ord(c) for c in normalized_speaker]}")
        if normalized_speaker.lower() == 'none':
            print("Returning default voice for 'none'")
            return self.default_voice

        voice = self.speaker_voice_map.get(normalized_speaker)
        if voice:
            print(
                f"Got voice: {voice if isinstance(voice, str) else voice.voice_id}")
            return voice

        print(
            f"Warning: No voice assigned for speaker '{normalized_speaker}'. Assigning a random voice.")
        self.assign_random_voice(normalized_speaker)
        return self.speaker_voice_map[normalized_speaker]

    def set_voice(self, voice):
        self.current_voice = voice

    def generate_audio(self, text):
        voice_id = self.current_voice if isinstance(
            self.current_voice, str) else self.current_voice.voice_id
        response = self.client.text_to_speech.convert(
            voice_id=voice_id,
            optimize_streaming_latency="0",
            output_format="mp3_44100_192",
            text=text,
            model_id="eleven_multilingual_v2",
            voice_settings=VoiceSettings(
                stability=0.5,
                similarity_boost=0.75,
                style=0.0,
                use_speaker_boost=True,
            ),
        )

        audio_data = b''
        for chunk in response:
            if chunk:
                audio_data += chunk

        return audio_data

    @staticmethod
    def generate_yaml_config(json_file, output_yaml):
        with open(json_file, 'r') as f:
            dialogues = json.load(f)

        speaker_count = Counter(
            dialogue['speaker'] for dialogue in dialogues if dialogue['type'] == 'dialog')

        yaml_content = """# Voice configuration for speakers
# 
# Instructions:
# - For each speaker and the default voice, you can specify a voice_id from ElevenLabs.
# - If you leave the voice_id empty or remove the line, a random voice will be assigned.
# - To see available voices and their IDs, run the script with --list-voices option.
#
# Example:
# default: voice_id_here
# SPEAKER_NAME: another_voice_id_here
# ANOTHER_SPEAKER: 
#
# The number of lines for each speaker is provided as a comment.

# The default voice will be used for all scene headings, scene descriptions, and dialog modifiers.
# It will remain distinct from all other voices.
default: 

"""
        for speaker, count in speaker_count.items():
            yaml_content += f"# {speaker}: {count} lines\n"
            yaml_content += f"{speaker}: \n\n"

        with open(output_yaml, 'w') as f:
            f.write(yaml_content)
