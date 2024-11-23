import pyttsx3
import random
from tts_provider import TTSProvider


class Pyttsx3Provider(TTSProvider):
    def __init__(self):
        self.engine = None
        self.voices = None
        self.speaker_voice_map = {}

    def initialize(self):
        self.engine = pyttsx3.init()
        voices = self.engine.getProperty('voices')
        self.voices = [voice for voice in voices if 'en_US' in voice.languages]
        random.shuffle(self.voices)

    def get_available_voices(self):
        return self.voices

    def get_voice_for_speaker(self, speaker):
        if speaker not in self.speaker_voice_map:
            if not self.voices:
                self.voices = self.get_available_voices()
                random.shuffle(self.voices)
            self.speaker_voice_map[speaker] = self.voices.pop()
        return self.speaker_voice_map[speaker]

    def set_voice(self, voice):
        self.engine.setProperty('voice', voice.id)

    def generate_audio(self, text, output_file):
        self.engine.save_to_file(text, output_file)
        self.engine.runAndWait()
