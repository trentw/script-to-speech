from .pyttsx3_tts_provider import Pyttsx3TTSProvider
from ..registry import register_provider

register_provider('pyttsx3', Pyttsx3TTSProvider)
