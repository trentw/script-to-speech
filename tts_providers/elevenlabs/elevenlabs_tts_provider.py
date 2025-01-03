from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs
from .elevenlabs_voice_registry_manager import ElevenLabsVoiceRegistryManager
import os
import yaml
from typing import Dict, Optional, List
from collections import Counter
from ..tts_provider_base import TTSProvider, TTSError, VoiceNotFoundError


class ElevenLabsTTSProvider(TTSProvider):
    """
    TTS Provider implementation for ElevenLabs API. Handles voice mapping and audio generation
    while abstracting away the complexity of ElevenLabs' voice registry system.
    """

    def __init__(self):
        self.client = None
        self.voice_registry_manager = None
        # Maps speaker names to public voice IDs
        self.voice_map: Dict[str, str] = {}
        self.default_voice_id: Optional[str] = None

    def initialize(self, config_path: Optional[str] = None) -> None:
        """Initialize the provider with API key and voice configuration."""
        api_key = os.environ.get("ELEVEN_API_KEY")
        if not api_key:
            raise TTSError("ELEVEN_API_KEY environment variable is not set")

        self.client = ElevenLabs(api_key=api_key)
        self.voice_registry_manager = ElevenLabsVoiceRegistryManager(api_key)

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
        """
        Get the voice ID from configuration for a given speaker.
        This returns the public/config voice ID, not the registry ID.
        """
        if speaker is None:
            if not self.default_voice_id:
                raise VoiceNotFoundError("No default voice configured")
            return self.default_voice_id

        voice_id = self.voice_map.get(speaker)
        if not voice_id:
            raise VoiceNotFoundError(
                f"No voice assigned for speaker '{speaker}'. "
                "Please update the voice configuration file."
            )

        return voice_id

    def generate_audio(self, speaker: Optional[str], text: str) -> bytes:
        """Generate audio for the given speaker and text."""
        if not self.client or not self.voice_registry_manager:
            raise TTSError(
                "Provider not initialized. Call initialize() first.")

        # Get the public voice ID first
        public_voice_id = self.get_speaker_identifier(speaker)

        # Then get the registry voice ID for actual generation
        registry_voice_id = self.voice_registry_manager.get_library_voice_id(
            public_voice_id)

        try:
            response = self.client.text_to_speech.convert(
                voice_id=registry_voice_id,
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
    def generate_yaml_config(chunks: List[Dict], output_path: str) -> None:
        """Generate a template YAML configuration file from processed chunks."""
        try:
            # Count dialog lines per speaker
            speaker_count = Counter(
                chunk['speaker'] for chunk in chunks
                if chunk['type'] == 'dialog' and chunk['speaker']
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

            with open(output_path, 'w') as f:
                f.write(yaml_content)

        except Exception as e:
            raise TTSError(f"Failed to generate YAML template: {e}")
