from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, Optional


class TaskStatus(Enum):
    """Status of an audio generation task"""

    PENDING = auto()  # Task is waiting to be processed
    PROCESSING = auto()  # Task is currently being processed
    CACHED = auto()  # Audio was already in cache or override was applied
    GENERATED = auto()  # Audio was successfully generated and cached
    FAILED_RATE_LIMIT = auto()  # Task failed due to rate limit (will be retried)
    FAILED_OTHER = auto()  # Task failed due to other error (will not be retried)
    SKIPPED_DUPLICATE = auto()  # Task was skipped because a duplicate task handled it


@dataclass
class AudioClipInfo:
    """Information about an audio clip"""

    text: str
    cache_path: str
    dbfs_level: Optional[float] = None
    # Human-readable name for UI display (e.g., "JOHN", "(default)")
    speaker_display: Optional[str] = None
    # Voice identifier from TTS provider (e.g., "nova_tts-1", "voice_id_abc123")
    speaker_id: Optional[str] = None
    # TTS provider name (e.g., "openai", "elevenlabs")
    provider_id: Optional[str] = None
    # Config key for speaker lookup (e.g., "JOHN", "default") - used to get full speaker config
    speaker: Optional[str] = None


@dataclass
class AudioGenerationTask:
    """Represents the plan and state for generating a single audio clip."""

    idx: int
    original_dialogue: Dict[str, Any]
    processed_dialogue: Dict[str, Any]
    text_to_speak: str
    speaker: Optional[str]
    provider_id: Optional[str]
    speaker_id: Optional[str]
    speaker_display: str  # For reporting
    cache_filename: str
    cache_filepath: str
    is_cache_hit: bool = False
    is_override_available: bool = (
        False  # Useful to know if override *could* have been applied
    )
    expected_silence: bool = False
    expected_cache_duplicate: bool = (
        False  # Flag to indicate if another task will likely cache the same path
    )
    # Status fields updated during planning/fetching
    checked_override: bool = False  # Checked if override file exists during planning
    checked_cache: bool = False  # Checked if cache file exists during planning
    checked_silence_level: Optional[float] = None  # Store level if checked
    status: TaskStatus = TaskStatus.PENDING  # Current status of the task
    retry_count: int = 0  # Number of times this task has been retried


@dataclass
class ReportingState:
    """State for unified reporting of silent clips and cache misses"""

    silent_clips: Dict[str, AudioClipInfo] = field(default_factory=dict)
    cache_misses: Dict[str, AudioClipInfo] = field(default_factory=dict)
