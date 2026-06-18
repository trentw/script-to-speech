"""Tests for cooperative cancellation in the audio generation pipeline.

Covers the inert-by-default stop mechanism added to AudioDownloadManager and the
optional ``should_stop`` callback on ``check_for_silence``. The CLI never sets
these, so the default behaviour is exercised by the existing suites; here we
verify the GUI-driven cancellation paths.
"""

from unittest.mock import MagicMock, patch

from script_to_speech.audio_generation.download_manager import AudioDownloadManager
from script_to_speech.audio_generation.models import (
    AudioGenerationTask,
    TaskStatus,
)
from script_to_speech.audio_generation.processing import check_for_silence


def _make_task(idx: int, cache_filepath: str, *, is_cache_hit: bool = False):
    return AudioGenerationTask(
        idx=idx,
        original_dialogue={
            "type": "dialogue",
            "speaker": "MARY",
            "text": f"line {idx}",
        },
        processed_dialogue={
            "type": "dialogue",
            "speaker": "MARY",
            "text": f"line {idx}",
        },
        text_to_speak=f"line {idx}",
        speaker="MARY",
        provider_id="openai",
        speaker_id="voice_id_456",
        speaker_display="MARY",
        cache_filename=f"clip_{idx}.mp3",
        cache_filepath=cache_filepath,
        is_cache_hit=is_cache_hit,
        expected_silence=False,
        status=TaskStatus.PENDING,
        retry_count=0,
    )


def _mock_provider():
    mock = MagicMock()
    mock.generate_audio.return_value = b"audio_data"
    mock.get_max_provider_download_threads.return_value = 2
    return mock


class TestDownloadManagerStop:
    def test_stop_preset_generates_nothing(self, tmp_path):
        """If stop is requested before run(), no audio is generated or written."""
        provider = _mock_provider()
        tasks = [_make_task(i, str(tmp_path / f"clip_{i}.mp3")) for i in range(3)]
        manager = AudioDownloadManager(
            tasks=tasks,
            tts_provider_manager=provider,
            global_max_workers=2,
            silence_threshold=None,
        )

        manager.request_stop()
        reporting_state = manager.run()

        provider.generate_audio.assert_not_called()
        assert list(tmp_path.glob("*.mp3")) == []
        assert reporting_state.silent_clips == {}
        # Untouched cache-miss tasks remain pending (resumable on a later run).
        assert all(t.status == TaskStatus.PENDING for t in tasks)

    def test_request_stop_midrun_skips_remaining(self, tmp_path):
        """In-flight clip finishes; queued clips are skipped once stop is set."""
        provider = _mock_provider()
        tasks = [_make_task(i, str(tmp_path / f"clip_{i}.mp3")) for i in range(5)]
        # Run strictly one-at-a-time so the test is deterministic.
        manager = AudioDownloadManager(
            tasks=tasks,
            tts_provider_manager=provider,
            global_max_workers=1,
            silence_threshold=None,
        )

        def generate(speaker, text):
            # Request stop as soon as the first clip is generated.
            manager.request_stop()
            return b"audio_data"

        provider.generate_audio.side_effect = generate

        manager.run()

        # Exactly one clip generated and written; the rest were skipped.
        assert provider.generate_audio.call_count == 1
        assert len(list(tmp_path.glob("*.mp3"))) == 1

    def test_request_stop_is_idempotent_and_inert_by_default(self, tmp_path):
        """Default (no stop) still generates every cache-miss clip."""
        provider = _mock_provider()
        tasks = [_make_task(i, str(tmp_path / f"clip_{i}.mp3")) for i in range(3)]
        manager = AudioDownloadManager(
            tasks=tasks,
            tts_provider_manager=provider,
            global_max_workers=2,
            silence_threshold=None,
        )

        manager.run()

        assert provider.generate_audio.call_count == 3
        assert len(list(tmp_path.glob("*.mp3"))) == 3


class TestCheckForSilenceStop:
    def test_should_stop_halts_scan_early(self, tmp_path):
        """should_stop returning True mid-loop stops scanning further files."""
        tasks = []
        for i in range(5):
            path = tmp_path / f"clip_{i}.mp3"
            path.write_bytes(b"x")
            tasks.append(_make_task(i, str(path), is_cache_hit=True))

        processed = {"n": 0}

        def fake_check_silence(*args, **kwargs):
            processed["n"] += 1
            return False

        # Stop after two files have been processed.
        def should_stop():
            return processed["n"] >= 2

        with patch(
            "script_to_speech.audio_generation.processing.check_audio_silence",
            side_effect=fake_check_silence,
        ):
            check_for_silence(
                tasks=tasks,
                silence_threshold=-40.0,
                should_stop=should_stop,
            )

        assert processed["n"] == 2

    def test_should_stop_none_scans_all(self, tmp_path):
        """Default (should_stop=None) scans every cached file."""
        tasks = []
        for i in range(4):
            path = tmp_path / f"clip_{i}.mp3"
            path.write_bytes(b"x")
            tasks.append(_make_task(i, str(path), is_cache_hit=True))

        with patch(
            "script_to_speech.audio_generation.processing.check_audio_silence",
            return_value=False,
        ) as mock_check:
            check_for_silence(tasks=tasks, silence_threshold=-40.0)

        assert mock_check.call_count == 4
