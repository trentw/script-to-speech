"""Central definition of the audio cache filename convention.

Cache filenames encode everything needed to match an audio file back to a
screenplay chunk:

    {original_hash}~~{processed_hash}~~{provider_id}~~{speaker_id}.mp3

An optional fifth field marks files whose audio was hand-committed by the
user from the review flow ("user-modified"):

    {original_hash}~~{processed_hash}~~{provider_id}~~{speaker_id}~~edit.mp3
    {original_hash}~~{processed_hash}~~{provider_id}~~{speaker_id}~~retake.mp3

- ``edit``: committed audio generated from user-modified text
- ``retake``: committed audio generated from the unmodified processed text

Flags never affect cache-hit behavior: a chunk is a cache hit whether its
file is flagged or not. When multiple flavors of the same base name exist,
the authority ladder (edit > retake > plain) decides which file wins.

Standalone-speech variant files use a separate ``--``-delimited naming scheme
(see ``utils/generate_standalone_speech.py``); the helpers here also own the
trailing kind token appended to those names so the two conventions cannot
drift apart.

No other module may split on the delimiter -- all construction, parsing, and
resolution of cache filenames goes through this module. Provider and speaker
identifiers must never contain the delimiter.
"""

from dataclasses import dataclass
from enum import Enum
from typing import AbstractSet, List, Optional, Tuple

DELIMITER = "~~"
AUDIO_EXTENSION = ".mp3"

# Delimiter used by standalone-speech variant filenames.
VARIANT_DELIMITER = "--"


class CacheFlag(str, Enum):
    """User-modified flavor of a cache file, encoded as the filename's 5th field.

    This enum is the single registry of flag tokens; future flavors are added
    here (and to AUTHORITY_LADDER) rather than as string literals elsewhere.
    """

    EDIT = "edit"  # committed audio generated from user-modified text
    RETAKE = "retake"  # committed re-roll of the unmodified processed text


# Resolution order when multiple flavors of one base name coexist: manual
# work always wins, and an edited-text commit outranks a picked retake.
AUTHORITY_LADDER: Tuple[Optional[CacheFlag], ...] = (
    CacheFlag.EDIT,
    CacheFlag.RETAKE,
    None,
)


@dataclass(frozen=True)
class ParsedCacheFilename:
    """Components of a cache filename.

    ``flag`` is kept as a plain string (rather than CacheFlag) so filenames
    written by future versions with new flag tokens still parse as
    user-modified instead of failing.
    """

    original_hash: str
    processed_hash: str
    provider_id: str
    speaker_id: str
    flag: Optional[str] = None

    @property
    def is_user_modified(self) -> bool:
        return self.flag is not None


def build_cache_filename(
    original_hash: str,
    processed_hash: str,
    provider_id: str,
    speaker_id: str,
    flag: Optional[CacheFlag] = None,
) -> str:
    """Build a cache filename from its components."""
    base = DELIMITER.join([original_hash, processed_hash, provider_id, speaker_id])
    if flag is not None:
        base = f"{base}{DELIMITER}{flag.value}"
    return f"{base}{AUDIO_EXTENSION}"


def parse_cache_filename(filename: str) -> Optional[ParsedCacheFilename]:
    """Parse a cache filename into components, or None if it doesn't conform."""
    if not filename.endswith(AUDIO_EXTENSION):
        return None
    stem = filename[: -len(AUDIO_EXTENSION)]
    parts = stem.split(DELIMITER)
    if len(parts) == 4:
        return ParsedCacheFilename(parts[0], parts[1], parts[2], parts[3])
    if len(parts) == 5:
        return ParsedCacheFilename(
            parts[0], parts[1], parts[2], parts[3], flag=parts[4]
        )
    return None


def get_cache_flag(filename: str) -> Optional[str]:
    """Return the user-modified flag token of a cache filename, if any."""
    parsed = parse_cache_filename(filename)
    return parsed.flag if parsed else None


def strip_cache_flag(filename: str) -> str:
    """Return the plain (unflagged) filename for any flavor of a cache filename.

    Raises ValueError if the filename doesn't conform to the convention.
    """
    parsed = parse_cache_filename(filename)
    if parsed is None:
        raise ValueError(f"Not a valid cache filename: {filename}")
    return build_cache_filename(
        parsed.original_hash,
        parsed.processed_hash,
        parsed.provider_id,
        parsed.speaker_id,
    )


def with_cache_flag(filename: str, flag: Optional[CacheFlag]) -> str:
    """Return the given flavor of a cache filename (any flavor in, any out).

    Raises ValueError if the filename doesn't conform to the convention.
    """
    parsed = parse_cache_filename(filename)
    if parsed is None:
        raise ValueError(f"Not a valid cache filename: {filename}")
    return build_cache_filename(
        parsed.original_hash,
        parsed.processed_hash,
        parsed.provider_id,
        parsed.speaker_id,
        flag=flag,
    )


def sibling_cache_filenames(filename: str) -> List[str]:
    """All defined flavors (plain + each known flag) of a cache filename's base."""
    return [with_cache_flag(filename, flag) for flag in AUTHORITY_LADDER]


def resolve_cache_filename(
    expected_filename: str, existing_files: AbstractSet[str]
) -> Optional[str]:
    """Resolve the expected (plain) cache filename against files on disk.

    Walks the authority ladder (edit > retake > plain) and returns the first
    flavor present in ``existing_files``, or None when the chunk has no
    cached audio at all (a cache miss).
    """
    for flag in AUTHORITY_LADDER:
        candidate = with_cache_flag(expected_filename, flag)
        if candidate in existing_files:
            return candidate
    return None


def variant_kind_suffix(kind: CacheFlag) -> str:
    """Filename suffix (before extension) marking a standalone variant's kind."""
    return f"{VARIANT_DELIMITER}{kind.value}"


def parse_variant_kind(filename: str) -> Optional[CacheFlag]:
    """Extract the generation kind from a standalone variant filename.

    Returns None for untagged variants (including all files generated before
    this convention existed), which commit unmarked -- "fix forward" only.
    """
    stem = filename
    if stem.endswith(AUDIO_EXTENSION):
        stem = stem[: -len(AUDIO_EXTENSION)]
    parts = stem.split(VARIANT_DELIMITER)
    if len(parts) < 2:
        return None
    try:
        return CacheFlag(parts[-1])
    except ValueError:
        return None
