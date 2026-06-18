"""Router tests for audiobook active-task lookup, single-session, and cancel."""

import pytest
from fastapi.testclient import TestClient

from script_to_speech.gui_backend.main import app
from script_to_speech.gui_backend.models import (
    AudiobookGenerationRequest,
    TaskStatus,
)
from script_to_speech.gui_backend.services.audiobook_generation_service import (
    AudiobookGenerationTask,
)
from script_to_speech.gui_backend.services.audiobook_generation_service import (
    audiobook_generation_service as service,
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def clean_tasks():
    service._tasks.clear()
    yield
    service._tasks.clear()


def _insert(stem: str, status: TaskStatus = TaskStatus.PROCESSING) -> str:
    task_id = f"task-{stem}-{len(service._tasks)}"
    request = AudiobookGenerationRequest(
        project_name=f"{stem} Title",
        input_json_path=f"/ws/input/{stem}/{stem}.json",
        voice_config_path=f"/ws/input/{stem}/{stem}_voice_config.yaml",
    )
    task = AudiobookGenerationTask(task_id, request)
    task.status = status
    service._tasks[task_id] = task
    return task_id


class TestActiveEndpoint:
    def test_returns_null_when_idle(self, client):
        resp = client.get("/api/audiobook/active/ghost")
        assert resp.status_code == 200
        assert resp.json() is None

    def test_returns_progress_when_present(self, client):
        task_id = _insert("my_screenplay")
        resp = client.get("/api/audiobook/active/my_screenplay")
        assert resp.status_code == 200
        body = resp.json()
        assert body is not None
        assert body["taskId"] == task_id
        assert body["status"] == "processing"


class TestSingleSession:
    def test_generate_conflicts_with_live_task(self, client):
        _insert("proj", status=TaskStatus.PROCESSING)
        resp = client.post(
            "/api/audiobook/generate",
            json={
                "project_name": "proj",
                "input_json_path": "/ws/input/proj/proj.json",
                "voice_config_path": "/ws/input/proj/proj_voice_config.yaml",
            },
        )
        assert resp.status_code == 409
        assert "already running" in resp.json()["detail"].lower()


class TestCancelEndpoint:
    def test_unknown_task_404(self, client):
        resp = client.post("/api/audiobook/nope/cancel")
        assert resp.status_code == 404

    def test_terminal_task_409(self, client):
        task_id = _insert("proj", status=TaskStatus.COMPLETED)
        resp = client.post(f"/api/audiobook/{task_id}/cancel")
        assert resp.status_code == 409

    def test_live_task_cancels_200(self, client):
        task_id = _insert("proj", status=TaskStatus.PROCESSING)
        resp = client.post(f"/api/audiobook/{task_id}/cancel")
        assert resp.status_code == 200
        assert resp.json()["taskId"] == task_id
        assert service._tasks[task_id].cancel_event.is_set()
