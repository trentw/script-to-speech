from .openai_tts_provider import OpenAITTSProvider
from ..registry import register_provider

register_provider('openai', OpenAITTSProvider)