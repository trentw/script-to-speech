import pyttsx3
from typing import Dict, Optional
from ..tts_provider_base import TTSProvider, TTSError, VoiceNotFoundError
import io
import os
import wave


class Pyttsx3TTSProvider(TTSProvider):
    """
    TTS Provider implementation using pyttsx3 for local text-to-speech generation.
    Uses system voices and maintains consistent voice assignments for speakers.
    """

    def __init__(self):
        self.engine: Optional[pyttsx3.Engine] = None
        self.available_voices: Dict[str, pyttsx3.voice.Voice] = {}
        # Maps speakers to voice IDs
        self.speaker_voice_map: Dict[str, str] = {}
        self.default_voice_id: Optional[str] = None

    def initialize(self, config_path: Optional[str] = None) -> None:
        """
        Initialize the pyttsx3 engine and load available voices.

        Args:
            config_path: Not used in this provider, but kept for interface consistency

        Raises:
            TTSError: If initialization fails
        """
        try:
            self.engine = pyttsx3.init()
            voices = self.engine.getProperty('voices')

            # Filter for English voices and create mapping
            for voice in voices:
                if hasattr(voice, 'languages') and 'en' in ' '.join(voice.languages).lower():
                    self.available_voices[voice.id] = voice

            if not self.available_voices:
                raise TTSError("No English voices found in system")

            # Set default voice
            self.default_voice_id = next(iter(self.available_voices.keys()))

        except Exception as e:
            raise TTSError(f"Failed to initialize pyttsx3 engine: {e}")

    def get_speaker_identifier(self, speaker: Optional[str]) -> str:
        """
        Get the voice ID for a given speaker.

        Args:
            speaker: The speaker to get the voice for, or None for default voice

        Returns:
            str: Voice ID to use for the speaker

        Raises:
            VoiceNotFoundError: If no voice is available for the speaker
        """
        if speaker is None:
            if self.default_voice_id is None:
                raise VoiceNotFoundError("No default voice configured")
            return self.default_voice_id

        if speaker not in self.speaker_voice_map:
            # Assign a new voice from available voices
            unused_voices = set(self.available_voices.keys()) - \
                set(self.speaker_voice_map.values())
            if not unused_voices:
                # If all voices are used, start reusing voices
                unused_voices = set(self.available_voices.keys())

            if not unused_voices:
                raise VoiceNotFoundError("No voices available in system")

            # Choose a voice deterministically based on speaker name
            voice_list = sorted(list(unused_voices))
            voice_index = hash(speaker) % len(voice_list)
            self.speaker_voice_map[speaker] = voice_list[voice_index]

        return self.speaker_voice_map[speaker]

    def generate_audio(self, speaker: Optional[str], text: str) -> bytes:
        """
        Generate audio for the given speaker and text.

        Args:
            speaker: The speaker to generate audio for, or None for default voice
            text: The text to convert to speech

        Returns:
            bytes: The generated audio data in wave format

        Raises:
            TTSError: If provider not initialized or audio generation fails
            VoiceNotFoundError: If no voice is available for the speaker
        """
        if not self.engine:
            raise TTSError(
                "Provider not initialized. Call initialize() first.")

        try:
            voice_id = self.get_speaker_identifier(speaker)
            self.engine.setProperty('voice', voice_id)

            # Create an in-memory bytes buffer
            buffer = io.BytesIO()

            # Configure the engine to write to our buffer
            self.engine.save_to_file(text, 'temp.wav')
            self.engine.runAndWait()

            # Read the generated file and return its contents
            with open('temp.wav', 'rb') as f:
                audio_data = f.read()

            # Clean up the temporary file
            os.remove('temp.wav')

            return audio_data

        except VoiceNotFoundError:
            raise  # Re-raise voice not found errors
        except Exception as e:
            raise TTSError(f"Failed to generate audio: {e}")

    def get_provider_identifier(self) -> str:
        """Get the provider identifier."""
        return "pyttsx3"
