from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs
from tts_provider import TTSProvider
import os
import random
import yaml
import json
from collections import Counter


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

    def get_speaker_identifier(self, speaker):
        voice = self.get_voice_for_speaker(speaker)
        return voice.voice_id

    def get_provider_identifier(self):
        return "elevenlabs"

    def load_yaml_config(self):
        with open(self.yaml_config, 'r') as file:
            config = yaml.safe_load(file)

        # Load default voice
        default_voice_id = config.get('default', '')
        if default_voice_id and default_voice_id in self.voice_dict:
            self.default_voice = self.voice_dict[default_voice_id]
            self.used_voice_ids.add(default_voice_id)
        else:
            self.default_voice = random.choice(self.available_voices)
            self.used_voice_ids.add(self.default_voice.voice_id)

        # Load speaker voices
        for speaker, voice_id in config.items():
            if speaker != 'default' and voice_id and voice_id in self.voice_dict:
                if voice_id not in self.used_voice_ids:
                    self.speaker_voice_map[speaker] = self.voice_dict[voice_id]
                    self.used_voice_ids.add(voice_id)
                else:
                    print(
                        f"Warning: Voice for {speaker} is already in use. Assigning a random voice.")
                    self.assign_random_voice(speaker)

    def assign_random_voice(self, speaker):
        available_voices = [
            v for v in self.available_voices if v.voice_id not in self.used_voice_ids]
        if not available_voices:
            available_voices = [
                v for v in self.available_voices if v.voice_id != self.default_voice.voice_id]
        voice = random.choice(available_voices)
        self.speaker_voice_map[speaker] = voice
        self.used_voice_ids.add(voice.voice_id)

    def get_available_voices(self):
        return self.available_voices

    def get_voice_for_speaker(self, speaker):
        if speaker == 'none':
            return self.default_voice
        if speaker not in self.speaker_voice_map:
            self.assign_random_voice(speaker)
        return self.speaker_voice_map[speaker]

    def set_voice(self, voice):
        self.current_voice = voice

    def generate_audio(self, text):
        response = self.client.text_to_speech.convert(
            voice_id=self.current_voice.voice_id,
            optimize_streaming_latency="0",
            output_format="mp3_22050_32",
            text=text,
            model_id="eleven_monolingual_v1",
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
