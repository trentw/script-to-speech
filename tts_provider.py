from abc import ABC, abstractmethod


class TTSProvider(ABC):
    @abstractmethod
    def initialize(self):
        """Initialize the TTS provider."""
        pass

    @abstractmethod
    def get_available_voices(self):
        """Get a list of available voices."""
        pass

    @abstractmethod
    def get_voice_for_speaker(self, speaker):
        """Get the voice object for a given speaker."""
        pass

    @abstractmethod
    def set_voice(self, voice):
        """Set the current voice to be used."""
        pass

    @abstractmethod
    def generate_audio(self, text, output_file):
        """Generate audio for the given text and save it to the output file."""
        pass

    @abstractmethod
    def get_speaker_identifier(self, speaker):
        """Get a unique identifier for the given speaker."""
        pass

    @abstractmethod
    def get_provider_identifier(self):
        """Get a unique identifier for this TTS provider."""
        pass
