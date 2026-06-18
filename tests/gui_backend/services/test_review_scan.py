"""Tests for the background silent-clips scan + shared silence-scan registry.

Covers the registry on AudiobookGenerationService and ReviewService's
start_scan / get_scan_progress / _run_scan orchestration. The actual audio
silence detection (``_scan_for_silent_clips``) is mocked here since it requires
real cached mp3 files; it is covered by tests/audio_generation/.
"""

from unittest.mock import MagicMock, patch

import pytest

from script_to_speech.audio_generation.processing import SilenceCheckProgressTracker
from script_to_speech.gui_backend.models import (
    SilenceScanProgress,
    SilentClipsResponse,
)
from script_to_speech.gui_backend.services.audiobook_generation_service import (
    audiobook_generation_service,
)
from script_to_speech.gui_backend.services.review_service import review_service


@pytest.fixture(autouse=True)
def clean_registry():
    """Clear shared registry + cache before and after each test."""
    audiobook_generation_service._silence_scans.clear()
    audiobook_generation_service._silent_clips_cache.clear()
    yield
    audiobook_generation_service._silence_scans.clear()
    audiobook_generation_service._silent_clips_cache.clear()


def _fake_result() -> SilentClipsResponse:
    return SilentClipsResponse(
        silent_clips=[],
        total_clips_scanned=5,
        cache_folder="/tmp/cache",
        scanned_at="2026-06-17T00:00:00+00:00",
    )


class TestSilenceScanRegistry:
    """Registry methods on AudiobookGenerationService."""

    def test_idle_when_no_scan(self):
        progress = audiobook_generation_service.get_silence_scan_progress("nope")
        assert progress.status == "idle"
        assert progress.progress == 0.0
        assert progress.total_clips == 0

    def test_register_marks_running_and_reflects_tracker(self):
        tracker = SilenceCheckProgressTracker(total_tasks=10)
        tracker.update(4)
        audiobook_generation_service.register_silence_scan("proj", tracker, "review")

        assert audiobook_generation_service.is_silence_scan_running("proj") is True
        progress = audiobook_generation_service.get_silence_scan_progress("proj")
        assert progress.status == "running"
        assert progress.source == "review"
        assert progress.total_clips == 10
        assert progress.completed_clips == 4
        assert progress.progress == pytest.approx(0.4)

    def test_complete_marks_completed_with_timestamp(self):
        tracker = SilenceCheckProgressTracker(total_tasks=2)
        audiobook_generation_service.register_silence_scan("proj", tracker, "review")
        audiobook_generation_service.complete_silence_scan(
            "proj", scanned_at="2026-06-17T00:00:00+00:00"
        )

        assert audiobook_generation_service.is_silence_scan_running("proj") is False
        progress = audiobook_generation_service.get_silence_scan_progress("proj")
        assert progress.status == "completed"
        assert progress.scanned_at == "2026-06-17T00:00:00+00:00"
        assert progress.error is None

    def test_complete_with_error_marks_failed(self):
        tracker = SilenceCheckProgressTracker(total_tasks=2)
        audiobook_generation_service.register_silence_scan(
            "proj", tracker, "generation"
        )
        audiobook_generation_service.complete_silence_scan("proj", error="boom")

        progress = audiobook_generation_service.get_silence_scan_progress("proj")
        assert progress.status == "failed"
        assert progress.error == "boom"
        assert audiobook_generation_service.is_silence_scan_running("proj") is False

    def test_complete_unknown_project_is_noop(self):
        # Should not raise
        audiobook_generation_service.complete_silence_scan("ghost", error="x")
        assert (
            audiobook_generation_service.get_silence_scan_progress("ghost").status
            == "idle"
        )


class TestStartScan:
    """ReviewService.start_scan scheduling + piggybacking behavior."""

    def test_piggybacks_on_running_generation_scan(self):
        # Simulate an in-flight generation silence scan.
        tracker = SilenceCheckProgressTracker(total_tasks=8)
        tracker.update(2)
        audiobook_generation_service.register_silence_scan(
            "proj", tracker, "generation"
        )

        mock_create_task = MagicMock()
        mock_to_thread = MagicMock()
        with (
            patch("asyncio.create_task", mock_create_task),
            patch("asyncio.to_thread", mock_to_thread),
        ):
            progress = review_service.start_scan("proj")

        # No new scan scheduled; returns the in-flight generation progress.
        mock_create_task.assert_not_called()
        mock_to_thread.assert_not_called()
        assert progress.status == "running"
        assert progress.source == "generation"
        assert progress.completed_clips == 2

    def test_starts_new_review_scan_when_idle(self):
        mock_create_task = MagicMock()
        mock_to_thread = MagicMock(return_value="scheduled")
        with (
            patch("asyncio.create_task", mock_create_task),
            patch("asyncio.to_thread", mock_to_thread),
        ):
            progress = review_service.start_scan("proj")

        # A review-sourced scan is registered as running and scheduled once.
        assert progress.status == "running"
        assert progress.source == "review"
        mock_to_thread.assert_called_once()
        # _run_scan is the scheduled target
        assert mock_to_thread.call_args.args[0] == review_service._run_scan
        mock_create_task.assert_called_once()
        assert audiobook_generation_service.is_silence_scan_running("proj") is True


class TestRunScan:
    """ReviewService._run_scan completion / failure handling."""

    def test_completion_writes_cache_and_marks_completed(self):
        tracker = SilenceCheckProgressTracker(total_tasks=5)
        audiobook_generation_service.register_silence_scan("proj", tracker, "review")
        result = _fake_result()

        with patch.object(
            review_service, "_scan_for_silent_clips", return_value=result
        ) as mock_scan:
            review_service._run_scan("proj", tracker)

        mock_scan.assert_called_once_with("proj", progress_tracker=tracker)
        # Cache populated for the review page to read.
        assert audiobook_generation_service.get_cached_silent_clips("proj") is result
        progress = audiobook_generation_service.get_silence_scan_progress("proj")
        assert progress.status == "completed"
        assert progress.scanned_at == result.scanned_at

    def test_failure_marks_failed_and_skips_cache(self):
        tracker = SilenceCheckProgressTracker(total_tasks=5)
        audiobook_generation_service.register_silence_scan("proj", tracker, "review")

        with patch.object(
            review_service,
            "_scan_for_silent_clips",
            side_effect=RuntimeError("scan exploded"),
        ):
            review_service._run_scan("proj", tracker)

        assert audiobook_generation_service.get_cached_silent_clips("proj") is None
        progress = audiobook_generation_service.get_silence_scan_progress("proj")
        assert progress.status == "failed"
        assert "scan exploded" in (progress.error or "")


class TestModelSerialization:
    """SilenceScanProgress serializes to camelCase for the frontend."""

    def test_camel_case_fields(self):
        progress = SilenceScanProgress(
            status="running",
            progress=0.25,
            total_clips=8,
            completed_clips=2,
            source="review",
        )
        dumped = progress.model_dump(by_alias=True)
        assert dumped["totalClips"] == 8
        assert dumped["completedClips"] == 2
        assert dumped["status"] == "running"
        assert dumped["scannedAt"] is None
