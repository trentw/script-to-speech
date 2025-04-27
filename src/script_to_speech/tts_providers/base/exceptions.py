class TTSError(Exception):
    """Base exception class for TTS-related errors"""

    pass


class VoiceNotFoundError(TTSError):
    """Raised when a requested voice is not found"""

    pass


class TTSRateLimitError(TTSError):
    """Raised when a TTS provider's rate limit is exceeded"""

    pass
