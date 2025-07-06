"""
Fetches available voices from ElevenLabs.
"""

from typing import List


def fetch_voices() -> List[str]:
    """Returns a hardcoded list of ElevenLabs sts_ids."""
    return ["shiv", "daniel", "attank"]
