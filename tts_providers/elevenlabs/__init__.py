from .elevenlabs_tts_provider import ElevenLabsTTSProvider
from ..registry import register_provider

register_provider('elevenlabs', ElevenLabsTTSProvider)
