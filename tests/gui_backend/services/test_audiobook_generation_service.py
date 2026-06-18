"""Tests for AudiobookGenerationService session + cancellation logic.

Covers the active-task lookup (resume), single-session enforcement, and
cooperative cancellation (cancel_task + the CANCELLED terminal state). The full
generation pipeline (_run_generation's real work) is not exercised here; only
its cancellation guard and the task-registry behaviour are.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from script_to_speech.gui_backend.models import (
    AudiobookGenerationPhase,
    AudiobookGenerationRequest,
    TaskStatus,
)
from script_to_speech.gui_backend.services.audiobook_generation_service import (
    ActiveTaskExistsError,
    AudiobookGenerationTask,
    _GenerationCancelled,
)
from script_to_speech.gui_backend.services.audiobook_generation_service import (
    audiobook_generation_service as service,
)


@pytest.fixture(autouse=True)
def clean_tasks():
    service._tasks.clear()
    service._silence_scans.clear()
    yield
    service._tasks.clear()
    service._silence_scans.clear()


def _request(stem: str) -> AudiobookGenerationRequest:
    return AudiobookGenerationRequest(
        project_name=f"{stem} Title",  # friendlier title — must NOT be the key
        input_json_path=f"/ws/input/{stem}/{stem}.json",
        voice_config_path=f"/ws/input/{stem}/{stem}_voice_config.yaml",
    )


def _close_coro() -> MagicMock:
    """Mock for asyncio.create_task that closes the coroutine (no event loop).

    Prevents a 'coroutine was never awaited' warning when create_task is patched.
    """

    def _consume(coro):
        coro.close()

    return MagicMock(side_effect=_consume)


def _insert_task(
    stem: str,
    *,
    status: TaskStatus = TaskStatus.PROCESSING,
    created_at: datetime | None = None,
) -> AudiobookGenerationTask:
    task_id = f"task-{stem}-{len(service._tasks)}"
    task = AudiobookGenerationTask(task_id, _request(stem))
    task.status = status
    if created_at is not None:
        task.created_at = created_at
    service._tasks[task_id] = task
    return task


class TestActiveTaskLookup:
    def test_none_when_no_tasks(self):
        assert service.get_active_task_id_for_project("ghost") is None
        assert service.get_active_task_for_project("ghost") is None

    def test_keyed_off_stem_not_project_name(self):
        task = _insert_task("my_screenplay")
        # Lookup uses the input JSON stem, matching the frontend screenplayName.
        progress = service.get_active_task_for_project("my_screenplay")
        assert progress is not None
        assert progress.task_id == task.task_id

    def test_returns_most_recent_by_created_at(self):
        now = datetime.now(timezone.utc)
        _insert_task("proj", created_at=now - timedelta(minutes=5))
        newer = _insert_task("proj", created_at=now)
        assert service.get_active_task_id_for_project("proj") == newer.task_id

    def test_isolated_by_stem(self):
        _insert_task("alpha")
        beta = _insert_task("beta")
        assert service.get_active_task_id_for_project("beta") == beta.task_id


class TestSingleSessionEnforcement:
    def test_rejects_second_live_task_for_same_project(self):
        _insert_task("proj", status=TaskStatus.PROCESSING)
        with patch("asyncio.create_task", MagicMock()):
            with pytest.raises(ActiveTaskExistsError):
                service.create_task(_request("proj"))

    def test_allows_when_previous_task_terminal(self):
        _insert_task("proj", status=TaskStatus.COMPLETED)
        with patch("asyncio.create_task", _close_coro()) as mock_create:
            task_id = service.create_task(_request("proj"))
        assert task_id in service._tasks
        mock_create.assert_called_once()

    def test_allows_different_project_concurrently(self):
        _insert_task("alpha", status=TaskStatus.PROCESSING)
        with patch("asyncio.create_task", _close_coro()):
            task_id = service.create_task(_request("beta"))
        assert task_id in service._tasks


class TestCancelTask:
    def test_unknown_task_returns_false(self):
        assert service.cancel_task("nope") is False

    def test_terminal_task_not_cancellable(self):
        task = _insert_task("proj", status=TaskStatus.COMPLETED)
        assert service.cancel_task(task.task_id) is False
        assert not task.cancel_event.is_set()

    def test_live_task_sets_event_and_signals_manager(self):
        task = _insert_task("proj", status=TaskStatus.PROCESSING)
        stub_manager = MagicMock()
        task.set_download_manager(stub_manager)

        assert service.cancel_task(task.task_id) is True
        assert task.cancel_event.is_set()
        stub_manager.request_stop.assert_called_once()

    def test_live_task_without_manager_still_cancels(self):
        task = _insert_task("proj", status=TaskStatus.PROCESSING)
        assert service.cancel_task(task.task_id) is True
        assert task.cancel_event.is_set()


class TestRunGenerationCancellation:
    def test_run_generation_raises_when_preset(self):
        task = _insert_task("proj", status=TaskStatus.PROCESSING)
        task.cancel_event.set()
        with pytest.raises(_GenerationCancelled):
            service._run_generation(task)

    def test_process_task_translates_cancel_to_terminal_state(self):
        task = _insert_task("proj", status=TaskStatus.PENDING)

        def raise_cancel(_task):
            raise _GenerationCancelled()

        with patch.object(service, "_run_generation", side_effect=raise_cancel):
            asyncio.run(service._process_task(task))

        assert task.status == TaskStatus.CANCELLED
        assert task.phase == AudiobookGenerationPhase.CANCELLED
        assert task.completed_at is not None
        assert task.message == "Generation cancelled"
