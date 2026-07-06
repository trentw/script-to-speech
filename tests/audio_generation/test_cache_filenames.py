"""
Unit tests for the audio_generation.cache_filenames module.

This module tests the cache filename convention: building/parsing filenames,
the user-modified flag (edit/retake), the authority ladder resolution, and the
standalone-variant kind token.
"""

import pytest

from script_to_speech.audio_generation.cache_filenames import (
    AUTHORITY_LADDER,
    CacheFlag,
    ParsedCacheFilename,
    build_cache_filename,
    get_cache_flag,
    parse_cache_filename,
    parse_variant_kind,
    resolve_cache_filename,
    sibling_cache_filenames,
    strip_cache_flag,
    variant_kind_suffix,
    with_cache_flag,
)

ORIG = "a" * 32
PROC = "b" * 32
PLAIN = f"{ORIG}~~{PROC}~~openai~~nova_tts-1.mp3"
EDIT = f"{ORIG}~~{PROC}~~openai~~nova_tts-1~~edit.mp3"
RETAKE = f"{ORIG}~~{PROC}~~openai~~nova_tts-1~~retake.mp3"


class TestBuildCacheFilename:
    """Tests for build_cache_filename function."""

    def test_build_plain(self):
        assert build_cache_filename(ORIG, PROC, "openai", "nova_tts-1") == PLAIN

    def test_build_with_flag(self):
        assert (
            build_cache_filename(ORIG, PROC, "openai", "nova_tts-1", CacheFlag.EDIT)
            == EDIT
        )
        assert (
            build_cache_filename(ORIG, PROC, "openai", "nova_tts-1", CacheFlag.RETAKE)
            == RETAKE
        )

    def test_build_matches_legacy_format(self):
        """The plain format must remain byte-identical to the historical one."""
        # Legacy construction from processing.py
        legacy = f"{ORIG}~~{PROC}~~elevenlabs~~voice_abc123.mp3"
        assert build_cache_filename(ORIG, PROC, "elevenlabs", "voice_abc123") == legacy


class TestParseCacheFilename:
    """Tests for parse_cache_filename function."""

    def test_parse_plain(self):
        parsed = parse_cache_filename(PLAIN)
        assert parsed == ParsedCacheFilename(ORIG, PROC, "openai", "nova_tts-1")
        assert parsed.flag is None
        assert not parsed.is_user_modified

    def test_parse_flagged(self):
        parsed = parse_cache_filename(EDIT)
        assert parsed is not None
        assert parsed.flag == "edit"
        assert parsed.is_user_modified

    def test_parse_unknown_future_flag(self):
        """Unknown 5th-field tokens still parse as user-modified."""
        parsed = parse_cache_filename(
            f"{ORIG}~~{PROC}~~openai~~nova_tts-1~~futureflag.mp3"
        )
        assert parsed is not None
        assert parsed.flag == "futureflag"
        assert parsed.is_user_modified

    def test_parse_rejects_non_cache_names(self):
        assert parse_cache_filename("openai--nova--hello--20260101_120000.mp3") is None
        assert parse_cache_filename("random.mp3") is None
        assert parse_cache_filename(PLAIN.replace(".mp3", ".wav")) is None
        assert parse_cache_filename(f"{ORIG}~~{PROC}.mp3") is None
        # Too many fields
        assert parse_cache_filename(f"{ORIG}~~{PROC}~~p~~s~~edit~~extra.mp3") is None

    def test_roundtrip(self):
        for flag in (None, CacheFlag.EDIT, CacheFlag.RETAKE):
            name = build_cache_filename(ORIG, PROC, "cartesia", "abc123def456", flag)
            parsed = parse_cache_filename(name)
            assert parsed is not None
            rebuilt = build_cache_filename(
                parsed.original_hash,
                parsed.processed_hash,
                parsed.provider_id,
                parsed.speaker_id,
                flag,
            )
            assert rebuilt == name


class TestFlagHelpers:
    """Tests for get_cache_flag, strip_cache_flag, with_cache_flag, siblings."""

    def test_get_cache_flag(self):
        assert get_cache_flag(PLAIN) is None
        assert get_cache_flag(EDIT) == "edit"
        assert get_cache_flag(RETAKE) == "retake"
        assert get_cache_flag("not-a-cache-file.mp3") is None

    def test_strip_cache_flag(self):
        assert strip_cache_flag(PLAIN) == PLAIN
        assert strip_cache_flag(EDIT) == PLAIN
        assert strip_cache_flag(RETAKE) == PLAIN

    def test_strip_cache_flag_invalid_raises(self):
        with pytest.raises(ValueError):
            strip_cache_flag("garbage.mp3")

    def test_with_cache_flag_any_flavor_in(self):
        assert with_cache_flag(PLAIN, CacheFlag.EDIT) == EDIT
        assert with_cache_flag(EDIT, CacheFlag.RETAKE) == RETAKE
        assert with_cache_flag(RETAKE, None) == PLAIN

    def test_sibling_cache_filenames(self):
        siblings = sibling_cache_filenames(PLAIN)
        assert siblings == [EDIT, RETAKE, PLAIN]
        # Same siblings regardless of which flavor is passed in
        assert sibling_cache_filenames(EDIT) == siblings


class TestResolveCacheFilename:
    """Tests for resolve_cache_filename (authority ladder)."""

    def test_miss_returns_none(self):
        assert resolve_cache_filename(PLAIN, set()) is None
        assert resolve_cache_filename(PLAIN, {"other.mp3"}) is None

    def test_plain_only(self):
        assert resolve_cache_filename(PLAIN, {PLAIN}) == PLAIN

    def test_flagged_only(self):
        assert resolve_cache_filename(PLAIN, {EDIT}) == EDIT
        assert resolve_cache_filename(PLAIN, {RETAKE}) == RETAKE

    def test_ladder_edit_beats_take_beats_plain(self):
        assert resolve_cache_filename(PLAIN, {PLAIN, RETAKE, EDIT}) == EDIT
        assert resolve_cache_filename(PLAIN, {PLAIN, RETAKE}) == RETAKE
        assert resolve_cache_filename(PLAIN, {PLAIN, EDIT}) == EDIT

    def test_ladder_order_constant(self):
        """The ladder itself is the spec: edit > retake > plain."""
        assert AUTHORITY_LADDER == (CacheFlag.EDIT, CacheFlag.RETAKE, None)


class TestVariantKind:
    """Tests for the standalone-variant kind token."""

    def test_suffix(self):
        assert variant_kind_suffix(CacheFlag.EDIT) == "--edit"
        assert variant_kind_suffix(CacheFlag.RETAKE) == "--retake"

    def test_parse_tagged_variant(self):
        name = "openai--nova_tts-1--Hello_world--20260101_120000--edit.mp3"
        assert parse_variant_kind(name) == CacheFlag.EDIT
        name = "openai--nova_tts-1--Hello_world_variant2--20260101_120000--retake.mp3"
        assert parse_variant_kind(name) == CacheFlag.RETAKE

    def test_parse_untagged_variant(self):
        """Pre-existing variants have no token and must parse as None."""
        name = "openai--nova_tts-1--Hello_world--20260101_120000.mp3"
        assert parse_variant_kind(name) is None

    def test_parse_text_preview_containing_token_word(self):
        """A text preview ending in the token word must not confuse parsing
        because the timestamp always follows the preview."""
        name = "openai--nova--lets_do_another--retake--20260101_120000.mp3"
        assert parse_variant_kind(name) is None

    def test_parse_plain_names(self):
        assert parse_variant_kind("no_delimiters.mp3") is None
        assert parse_variant_kind(PLAIN) is None
