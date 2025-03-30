from dataclasses import dataclass
from typing import Optional


@dataclass
class AudioClipInfo:
    """Information about an audio clip"""

    text: str
    cache_path: str
    dbfs_level: Optional[float] = None
    speaker_display: Optional[str] = None
    speaker_id: Optional[str] = None
    provider_id: Optional[str] = None
