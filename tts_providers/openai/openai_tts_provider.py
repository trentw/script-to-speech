from typing import Optional, Dict, Set
from openai import OpenAI, AuthenticationError, APIError, RateLimitError
from ..tts_provider_base import TTSProvider, TTSError, VoiceNotFoundError
import os
import yaml


class OpenAITTSProvider(TTSProvider):
    """
    TTS Provider implementation for OpenAI's Text-to-Speech API.
    """

    VALID_VOICES: Set[str] = {'alloy', 'echo',
                              'fable', 'onyx', 'nova', 'shimmer'}
    MODEL = "tts-1-hd"

    def __init__(self):
        self.client: Optional[OpenAI] = None
        self.voice_map: Dict[str, str] = {}
        self.default_voice: Optional[str] = None

    def initialize(self, config_path: Optional[str] = None) -> None:
        """Initialize the provider with configuration."""
        try:
            self.client = OpenAI()
        except AuthenticationError:
            raise TTSError(
                "OPENAI_API_KEY environment variable is invalid or not set")
        except Exception as e:
            raise TTSError(f"Failed to initialize OpenAI client: {e}")

        if config_path:
            self._load_voice_config(config_path)

    def get_speaker_identifier(self, speaker: Optional[str]) -> str:
        """Get the voice name for a given speaker."""
        if speaker is None:
            if not self.default_voice:
                raise VoiceNotFoundError("No default voice configured")
            return self.default_voice

        voice = self.voice_map.get(speaker)
        if not voice:
            raise VoiceNotFoundError(
                f"No voice assigned for speaker '{speaker}'. "
                "Please update the voice configuration file."
            )

        return voice

    def generate_audio(self, speaker: Optional[str], text: str) -> bytes:
        """Generate audio for the given speaker and text."""
        if not self.client:
            raise TTSError(
                "Provider not initialized. Call initialize() first.")

        try:
            voice = self.get_speaker_identifier(speaker)
            response = self.client.audio.speech.create(
                model=self.MODEL,
                voice=voice,
                input=text
            )

            # OpenAI returns a streamable response, get the raw bytes
            return response.content

        except RateLimitError:
            raise TTSError("OpenAI rate limit exceeded")
        except AuthenticationError:
            raise TTSError("OpenAI authentication failed")
        except APIError as e:
            raise TTSError(f"OpenAI API error: {str(e)}")
        except Exception as e:
            raise TTSError(f"Failed to generate audio: {str(e)}")

    def get_provider_identifier(self) -> str:
        """Get the provider identifier."""
        return f"openai_{self.MODEL}"

    def _load_voice_config(self, config_path: str) -> None:
        """Load and validate voice configuration from YAML."""
        try:
            with open(config_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)
        except Exception as e:
            raise TTSError(f"Failed to load voice configuration file: {e}")

        # Validate and set default voice
        self.default_voice = config.get('default')
        if not self.default_voice:
            raise TTSError("No default voice specified in configuration")
        if self.default_voice not in self.VALID_VOICES:
            raise TTSError(f"Invalid default voice '{self.default_voice}'. "
                           f"Must be one of: {', '.join(sorted(self.VALID_VOICES))}")

        # Load and validate speaker voice mappings
        for speaker, voice in config.items():
            if speaker == 'default':
                continue
            if not voice:
                raise TTSError(f"No voice specified for speaker '{speaker}'")
            if voice not in self.VALID_VOICES:
                raise TTSError(f"Invalid voice '{voice}' for speaker '{speaker}'. "
                               f"Must be one of: {', '.join(sorted(self.VALID_VOICES))}")
            self.voice_map[speaker] = voice

    @staticmethod
    def generate_yaml_config(json_file: str, output_yaml: str) -> None:
        """Generate a template YAML configuration file from a JSON script."""
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
# - Specify a voice name for each speaker and the default voice
# - The default voice is required and will be used for scene descriptions
# - All speakers must have a voice specified
# - Valid voices are: alloy, echo, fable, onyx, nova, shimmer
#
# Format:
# default: voice_name_here
# SPEAKER_NAME: voice_name_here

default: alloy

"""
            # Add speakers sorted by number of lines
            for speaker, count in sorted(speaker_count.items(), key=lambda x: (-x[1], x[0])):
                yaml_content += f"# {speaker}: {count} lines\n"
                yaml_content += f"{speaker}: alloy\n\n"

            with open(output_yaml, 'w') as f:
                f.write(yaml_content)

        except Exception as e:
            raise TTSError(f"Failed to generate YAML template: {e}")
