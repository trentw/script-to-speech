from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class AudioClipInfo:
    """Information about an audio clip"""

    text: str
    cache_path: str
    dbfs_level: Optional[float] = None
    speaker_display: Optional[str] = None
    speaker_id: Optional[str] = None
    provider_id: Optional[str] = None


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


@dataclass
class ReportingState:
    """State for unified reporting of silent clips and cache misses"""

    silent_clips: Dict[str, AudioClipInfo] = field(default_factory=dict)
    cache_misses: Dict[str, AudioClipInfo] = field(default_factory=dict)
