from typing import Dict, Type
from .tts_provider_base import TTSProvider

# Registry of provider classes
_providers: Dict[str, Type[TTSProvider]] = {}


def register_provider(name: str, provider_class: Type[TTSProvider]) -> None:
    """Register a TTS provider class."""
    _providers[name] = provider_class


def get_provider(name: str) -> Type[TTSProvider]:
    """Get a TTS provider class by name."""
    if name not in _providers:
        raise ValueError(f"No TTS provider registered with name '{name}'")
    return _providers[name]


def get_available_providers() -> Dict[str, Type[TTSProvider]]:
    """Get all registered providers."""
    return dict(_providers)
