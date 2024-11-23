from abc import ABC, abstractmethod


class TTSProvider(ABC):
    @abstractmethod
    def initialize(self):
        pass

    @abstractmethod
    def get_available_voices(self):
        pass

    @abstractmethod
    def get_voice_for_speaker(self, speaker):
        pass

    @abstractmethod
    def set_voice(self, voice):
        pass

    @abstractmethod
    def generate_audio(self, text, output_file):
        pass
