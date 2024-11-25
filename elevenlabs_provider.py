from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs
import os
import yaml
from typing import Dict, Optional
from tts_provider import TTSProvider, TTSError, VoiceNotFoundError
from elevenlabs_voice_library_manager import ElevenLabsVoiceLibraryManager


class ElevenLabsProvider(TTSProvider):
    def __init__(self):
        self.client = None
        self.voice_library_manager = None
        # Maps speaker names to public voice IDs
        self.voice_map: Dict[str, str] = {}
        self.default_voice_id: Optional[str] = None

    def initialize(self, config_path: Optional[str] = None) -> None:
        """Initialize the provider with API key and voice configuration."""
        api_key = os.environ.get("ELEVEN_API_KEY")
        if not api_key:
            raise TTSError("ELEVEN_API_KEY environment variable is not set")

        self.client = ElevenLabs(api_key=api_key)
        self.voice_library_manager = ElevenLabsVoiceLibraryManager(
            api_key, debug=True)  # Enable debug logging

        if config_path:
            self._load_voice_config(config_path)

    def _load_voice_config(self, config_path: str) -> None:
        """Load voice mappings from YAML configuration."""
        try:
            with open(config_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)
        except Exception as e:
            raise TTSError(f"Failed to load voice configuration file: {e}")

        # Load default voice
        self.default_voice_id = config.get('default')
        if not self.default_voice_id:
            raise TTSError("No default voice ID specified in configuration")

        # Load speaker voice mappings
        for speaker, voice_id in config.items():
            if speaker == 'default':
                continue
            if not voice_id:
                raise TTSError(
                    f"No voice ID specified for speaker '{speaker}'")
            self.voice_map[speaker] = voice_id

    def get_speaker_identifier(self, speaker: Optional[str]) -> str:
        """Get the voice ID for a given speaker."""
        if speaker is None:
            if not self.default_voice_id:
                raise VoiceNotFoundError("No default voice configured")
            return self.voice_library_manager.get_library_voice_id(self.default_voice_id)

        voice_id = self.voice_map.get(speaker)
        if not voice_id:
            raise VoiceNotFoundError(
                f"No voice assigned for speaker '{speaker}'. "
                "Please update the voice configuration file."
            )

        return self.voice_library_manager.get_library_voice_id(voice_id)

    def generate_audio(self, speaker: Optional[str], text: str) -> bytes:
        """Generate audio for the given speaker and text."""
        if not self.client or not self.voice_library_manager:
            raise TTSError(
                "Provider not initialized. Call initialize() first.")

        voice_id = self.get_speaker_identifier(speaker)

        try:
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
                )
            )

            audio_data = b''
            for chunk in response:
                if chunk:
                    audio_data += chunk

            return audio_data

        except Exception as e:
            raise TTSError(f"Failed to generate audio: {e}")

    def get_provider_identifier(self) -> str:
        """Get the provider identifier."""
        return "elevenlabs"

    @staticmethod
    def generate_yaml_config(json_file: str, output_yaml: str) -> None:
        """
        Generate a template YAML configuration file from a JSON script.

        Args:
            json_file: Path to the input JSON script file
            output_yaml: Path where the YAML template should be saved
        """
        from collections import Counter
        import json

        try:
            with open(json_file, 'r') as f:
                dialogues = json.load(f)

            speaker_count = Counter(
                dialogue['speaker'] for dialogue in dialogues
                if dialogue['type'] == 'dialog'
            )

            yaml_content = """# Voice configuration for speakers
#
# Instructions:
# - Specify a voice_id from ElevenLabs for each speaker and the default voice
# - The default voice is required and will be used for scene descriptions
# - All speakers must have a voice_id specified
# - Use --list-voices to see available voices and their IDs
#
# Format:
# default: voice_id_here
# SPEAKER_NAME: voice_id_here

default: 

"""
            # Add speakers sorted by number of lines
            for speaker, count in sorted(speaker_count.items(), key=lambda x: (-x[1], x[0])):
                yaml_content += f"# {speaker}: {count} lines\n"
                yaml_content += f"{speaker}: \n\n"

            with open(output_yaml, 'w') as f:
                f.write(yaml_content)

        except Exception as e:
            raise TTSError(f"Failed to generate YAML template: {e}")
