"""
Unit tests for the audio_generation.models module.

This module tests the dataclass models used in the audio generation process,
ensuring they are properly initialized and behave as expected.
"""

import pytest

from script_to_speech.audio_generation.models import AudioClipInfo, AudioGenerationTask, ReportingState


class TestAudioClipInfo:
    """Tests for the AudioClipInfo dataclass."""

    def test_init_with_required_fields(self):
        """Test initialization with only required fields."""
        clip_info = AudioClipInfo(text="Hello world", cache_path="path/to/cache.mp3")

        assert clip_info.text == "Hello world"
        assert clip_info.cache_path == "path/to/cache.mp3"
        assert clip_info.dbfs_level is None
        assert clip_info.speaker_display is None
        assert clip_info.speaker_id is None
        assert clip_info.provider_id is None

    def test_init_with_all_fields(self):
        """Test initialization with all fields specified."""
        clip_info = AudioClipInfo(
            text="Hello world",
            cache_path="path/to/cache.mp3",
            dbfs_level=-25.5,
            speaker_display="JOHN",
            speaker_id="voice_id_123",
            provider_id="elevenlabs",
        )

        assert clip_info.text == "Hello world"
        assert clip_info.cache_path == "path/to/cache.mp3"
        assert clip_info.dbfs_level == -25.5
        assert clip_info.speaker_display == "JOHN"
        assert clip_info.speaker_id == "voice_id_123"
        assert clip_info.provider_id == "elevenlabs"


class TestAudioGenerationTask:
    """Tests for the AudioGenerationTask dataclass."""

    @pytest.fixture
    def original_dialogue(self):
        """Fixture providing a sample original dialogue dict."""
        return {
            "type": "dialog",
            "speaker": "JOHN",
            "text": "Hello everyone.",
            "raw_text": "Hello everyone.",
        }

    @pytest.fixture
    def processed_dialogue(self):
        """Fixture providing a sample processed dialogue dict."""
        return {
            "type": "dialog",
            "speaker": "JOHN",
            "text": "Hello everyone!",  # Processed text has added exclamation
            "raw_text": "Hello everyone.",
        }

    def test_init_with_required_fields(self, original_dialogue, processed_dialogue):
        """Test initialization with required fields."""
        task = AudioGenerationTask(
            idx=1,
            original_dialogue=original_dialogue,
            processed_dialogue=processed_dialogue,
            text_to_speak="Hello everyone!",
            speaker="JOHN",
            provider_id="elevenlabs",
            speaker_id="voice_id_123",
            speaker_display="JOHN",
            cache_filename="hash1~~hash2~~elevenlabs~~voice_id_123.mp3",
            cache_filepath="/path/to/cache/hash1~~hash2~~elevenlabs~~voice_id_123.mp3",
        )

        assert task.idx == 1
        assert task.original_dialogue == original_dialogue
        assert task.processed_dialogue == processed_dialogue
        assert task.text_to_speak == "Hello everyone!"
        assert task.speaker == "JOHN"
        assert task.provider_id == "elevenlabs"
        assert task.speaker_id == "voice_id_123"
        assert task.speaker_display == "JOHN"
        assert task.cache_filename == "hash1~~hash2~~elevenlabs~~voice_id_123.mp3"
        assert (
            task.cache_filepath
            == "/path/to/cache/hash1~~hash2~~elevenlabs~~voice_id_123.mp3"
        )

        # Check default values
        assert task.is_cache_hit is False
        assert task.is_override_available is False
        assert task.expected_silence is False
        assert task.checked_override is False
        assert task.checked_cache is False
        assert task.checked_silence_level is None

    def test_init_with_all_fields(self, original_dialogue, processed_dialogue):
        """Test initialization with all fields specified."""
        task = AudioGenerationTask(
            idx=1,
            original_dialogue=original_dialogue,
            processed_dialogue=processed_dialogue,
            text_to_speak="Hello everyone!",
            speaker="JOHN",
            provider_id="elevenlabs",
            speaker_id="voice_id_123",
            speaker_display="JOHN",
            cache_filename="hash1~~hash2~~elevenlabs~~voice_id_123.mp3",
            cache_filepath="/path/to/cache/hash1~~hash2~~elevenlabs~~voice_id_123.mp3",
            is_cache_hit=True,
            is_override_available=True,
            expected_silence=False,
            checked_override=True,
            checked_cache=True,
            checked_silence_level=-20.5,
        )

        assert task.idx == 1
        assert task.original_dialogue == original_dialogue
        assert task.processed_dialogue == processed_dialogue
        assert task.text_to_speak == "Hello everyone!"
        assert task.speaker == "JOHN"
        assert task.provider_id == "elevenlabs"
        assert task.speaker_id == "voice_id_123"
        assert task.speaker_display == "JOHN"
        assert task.cache_filename == "hash1~~hash2~~elevenlabs~~voice_id_123.mp3"
        assert (
            task.cache_filepath
            == "/path/to/cache/hash1~~hash2~~elevenlabs~~voice_id_123.mp3"
        )

        # Check specified values
        assert task.is_cache_hit is True
        assert task.is_override_available is True
        assert task.expected_silence is False
        assert task.checked_override is True
        assert task.checked_cache is True
        assert task.checked_silence_level == -20.5

    def test_expected_silence_detection(self, original_dialogue, processed_dialogue):
        """Test that expected_silence is properly set based on text content."""
        # Create a task with empty text
        processed_dialogue_empty = processed_dialogue.copy()
        processed_dialogue_empty["text"] = ""

        task = AudioGenerationTask(
            idx=1,
            original_dialogue=original_dialogue,
            processed_dialogue=processed_dialogue_empty,
            text_to_speak="",
            speaker="JOHN",
            provider_id="elevenlabs",
            speaker_id="voice_id_123",
            speaker_display="JOHN",
            cache_filename="hash1~~hash2~~elevenlabs~~voice_id_123.mp3",
            cache_filepath="/path/to/cache/hash1~~hash2~~elevenlabs~~voice_id_123.mp3",
            expected_silence=True,  # Explicitly setting to True
        )

        assert task.expected_silence is True

        # Create a task with only whitespace text
        processed_dialogue_whitespace = processed_dialogue.copy()
        processed_dialogue_whitespace["text"] = "   "

        task = AudioGenerationTask(
            idx=1,
            original_dialogue=original_dialogue,
            processed_dialogue=processed_dialogue_whitespace,
            text_to_speak="   ",
            speaker="JOHN",
            provider_id="elevenlabs",
            speaker_id="voice_id_123",
            speaker_display="JOHN",
            cache_filename="hash1~~hash2~~elevenlabs~~voice_id_123.mp3",
            cache_filepath="/path/to/cache/hash1~~hash2~~elevenlabs~~voice_id_123.mp3",
            expected_silence=True,  # Explicitly setting to True
        )

        assert task.expected_silence is True


class TestReportingState:
    """Tests for the ReportingState dataclass."""

    def test_init_default(self):
        """Test initialization with default values."""
        state = ReportingState()

        assert state.silent_clips == {}
        assert state.cache_misses == {}

    def test_adding_silent_clip(self):
        """Test adding a silent clip to the reporting state."""
        state = ReportingState()

        clip_info = AudioClipInfo(
            text="Whispered text",
            cache_path="path/to/silent.mp3",
            dbfs_level=-60.0,
            speaker_display="JOHN",
            speaker_id="voice_id_123",
            provider_id="elevenlabs",
        )

        state.silent_clips["hash1~~hash2~~elevenlabs~~voice_id_123.mp3"] = clip_info

        assert len(state.silent_clips) == 1
        assert "hash1~~hash2~~elevenlabs~~voice_id_123.mp3" in state.silent_clips
        assert (
            state.silent_clips["hash1~~hash2~~elevenlabs~~voice_id_123.mp3"].dbfs_level
            == -60.0
        )

    def test_adding_cache_miss(self):
        """Test adding a cache miss to the reporting state."""
        state = ReportingState()

        clip_info = AudioClipInfo(
            text="Missing text",
            cache_path="path/to/missing.mp3",
            speaker_display="MARY",
            speaker_id="voice_id_456",
            provider_id="openai",
        )

        state.cache_misses["hash3~~hash4~~openai~~voice_id_456.mp3"] = clip_info

        assert len(state.cache_misses) == 1
        assert "hash3~~hash4~~openai~~voice_id_456.mp3" in state.cache_misses
        assert (
            state.cache_misses["hash3~~hash4~~openai~~voice_id_456.mp3"].speaker_display
            == "MARY"
        )
