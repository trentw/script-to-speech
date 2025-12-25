"""Shared constants for TTS provider configuration."""

# Whitelist of allowed environment variables for security
# Only these keys can be read/written via the settings API
ALLOWED_ENV_KEYS = {
    "OPENAI_API_KEY",
    "ELEVEN_API_KEY",
    "CARTESIA_API_KEY",
    "MINIMAX_API_KEY",
    "MINIMAX_GROUP_ID",
    "ZONOS_API_KEY",
}

# Provider metadata for UI display
# This should be kept in sync with ALLOWED_ENV_KEYS
PROVIDER_METADATA = [
    {"key": "OPENAI_API_KEY", "label": "OpenAI API Key", "provider": "OpenAI"},
    {"key": "ELEVEN_API_KEY", "label": "ElevenLabs API Key", "provider": "ElevenLabs"},
    {
        "key": "CARTESIA_API_KEY",
        "label": "Cartesia API Key",
        "provider": "Cartesia",
    },
    {"key": "MINIMAX_API_KEY", "label": "Minimax API Key", "provider": "Minimax"},
    {"key": "MINIMAX_GROUP_ID", "label": "Minimax Group ID", "provider": "Minimax"},
    {"key": "ZONOS_API_KEY", "label": "Zonos API Key", "provider": "Zonos"},
]
