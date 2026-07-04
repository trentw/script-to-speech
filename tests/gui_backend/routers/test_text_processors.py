"""Unit tests for the text processor config API routes."""

from typing import Generator
from unittest.mock import MagicMock, patch

import pytest

from script_to_speech.gui_backend.services.text_processor_config_service import (
    ConfigConflictError,
    ConfigValidationError,
)


@pytest.fixture
def mock_service() -> Generator[MagicMock, None, None]:
    """Mock the text processor config service singleton in the router."""
    with patch(
        "script_to_speech.gui_backend.routers.text_processors.text_processor_config_service"
    ) as mock:
        yield mock


@pytest.fixture
def mock_settings_service() -> Generator[MagicMock, None, None]:
    """Mock the text processor config service singleton in the settings router."""
    with patch(
        "script_to_speech.gui_backend.routers.settings.text_processor_config_service"
    ) as mock:
        yield mock


SAMPLE_ENTRY = {
    "kind": "processor",
    "name": "skip_empty",
    "config": {"skip_types": ["page_number"]},
}


class TestRegistryEndpoint:
    """Tests for GET /api/text-processors/registry."""

    def test_registry_ok(self, client, mock_service):
        """The registry payload is returned in the ApiResponse envelope."""
        mock_service.get_registry.return_value = {"processors": []}

        response = client.get("/api/text-processors/registry")

        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert body["data"] == {"processors": []}


class TestValidateEndpoint:
    """Tests for POST /api/text-processors/validate."""

    def test_validate_ok(self, client, mock_service):
        """Validation results pass through the envelope."""
        mock_service.validate_entries.return_value = {
            "valid": True,
            "errors": [],
            "warnings": [],
        }

        response = client.post(
            "/api/text-processors/validate", json={"entries": [SAMPLE_ENTRY]}
        )

        assert response.status_code == 200
        assert response.json()["data"]["valid"] is True


class TestConfigEndpoints:
    """Tests for GET/PUT /api/project/text-processor-config."""

    def test_get_config_ok(self, client, mock_service):
        """A successful read returns the config payload."""
        mock_service.read_config.return_value = {"file_hash": "abc", "entries": []}

        response = client.get(
            "/api/project/text-processor-config",
            params={"input_path": "/workspace/input/my_script"},
        )

        assert response.status_code == 200
        assert response.json()["data"]["file_hash"] == "abc"

    def test_get_config_invalid_path(self, client, mock_service):
        """Path validation errors are reported in the envelope."""
        mock_service.read_config.side_effect = ValueError("outside workspace")

        response = client.get(
            "/api/project/text-processor-config", params={"input_path": "/etc"}
        )

        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is False
        assert body["error"] == "Invalid project path"

    def test_put_config_ok(self, client, mock_service):
        """A successful write returns the fresh read payload."""
        mock_service.write_config.return_value = {"file_hash": "def", "entries": []}

        response = client.put(
            "/api/project/text-processor-config",
            params={"input_path": "/workspace/input/my_script"},
            json={"entries": [SAMPLE_ENTRY], "base_file_hash": "abc"},
        )

        assert response.status_code == 200
        assert response.json()["data"]["file_hash"] == "def"
        args = mock_service.write_config.call_args
        assert args[0][2] == "abc"

    def test_put_config_conflict_maps_to_409(self, client, mock_service):
        """A stale base_file_hash yields HTTP 409."""
        mock_service.write_config.side_effect = ConfigConflictError("modified")

        response = client.put(
            "/api/project/text-processor-config",
            params={"input_path": "/workspace/input/my_script"},
            json={"entries": [SAMPLE_ENTRY], "base_file_hash": "stale"},
        )

        assert response.status_code == 409

    def test_put_config_validation_error(self, client, mock_service):
        """Validation failures return the error list in details."""
        mock_service.write_config.side_effect = ConfigValidationError(
            [{"entry_index": 0, "message": "Invalid configuration for skip_empty"}]
        )

        response = client.put(
            "/api/project/text-processor-config",
            params={"input_path": "/workspace/input/my_script"},
            json={"entries": [SAMPLE_ENTRY], "base_file_hash": "abc"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is False
        assert body["details"]["errors"][0]["entry_index"] == 0


class TestConvertAndResetEndpoints:
    """Tests for convert and reset actions."""

    def test_convert_ok(self, client, mock_service):
        """Convert returns the fresh config payload."""
        mock_service.convert_legacy_to_standalone.return_value = {"entries": []}

        response = client.post(
            "/api/project/text-processor-config/convert",
            params={"input_path": "/workspace/input/my_script"},
        )

        assert response.status_code == 200
        assert response.json()["ok"] is True

    def test_reset_ok(self, client, mock_service):
        """Reset passes the seed source through to the service."""
        mock_service.reset_config.return_value = {"entries": []}

        response = client.post(
            "/api/project/text-processor-config/reset",
            params={"input_path": "/workspace/input/my_script"},
            json={"source": "shipped_default"},
        )

        assert response.status_code == 200
        mock_service.reset_config.assert_called_once_with(
            "/workspace/input/my_script", "shipped_default"
        )

    def test_reset_rejects_unknown_source(self, client, mock_service):
        """Pydantic rejects seed sources outside the literal set."""
        response = client.post(
            "/api/project/text-processor-config/reset",
            params={"input_path": "/workspace/input/my_script"},
            json={"source": "bogus"},
        )

        assert response.status_code == 422


class TestGlobalDefaultEndpoints:
    """Tests for the settings global-default endpoints."""

    def test_get_global_default(self, client, mock_settings_service):
        """Read returns the global default payload."""
        mock_settings_service.read_global_default.return_value = {"exists": False}

        response = client.get("/api/settings/text-processor-default")

        assert response.status_code == 200
        assert response.json()["data"]["exists"] is False

    def test_put_global_default(self, client, mock_settings_service):
        """Write passes entries and provenance hash through."""
        mock_settings_service.write_global_default.return_value = {"exists": True}

        response = client.put(
            "/api/settings/text-processor-default",
            json={"entries": [SAMPLE_ENTRY], "based_on_default_sha256": "abc"},
        )

        assert response.status_code == 200
        assert response.json()["data"]["exists"] is True
        args = mock_settings_service.write_global_default.call_args
        assert args[0][1] == "abc"

    def test_delete_global_default(self, client, mock_settings_service):
        """Delete reports the removed state."""
        mock_settings_service.delete_global_default.return_value = {"exists": False}

        response = client.delete("/api/settings/text-processor-default")

        assert response.status_code == 200
        assert response.json()["data"]["exists"] is False


class TestPreviewEndpoint:
    """Tests for POST /api/project/text-processor-config/preview."""

    def test_preview_ok(self, client, mock_service):
        """Preview results pass through the envelope."""
        mock_service.run_preview_for_project.return_value = {
            "changed_chunk_count": 0,
            "changed_chunks": [],
        }

        response = client.post(
            "/api/project/text-processor-config/preview",
            params={"input_path": "/workspace/input/my_script"},
            json={},
        )

        assert response.status_code == 200
        assert response.json()["data"]["changed_chunk_count"] == 0
        mock_service.run_preview_for_project.assert_called_once_with(
            "/workspace/input/my_script", None, False, None
        )

    def test_preview_with_draft_entries(self, client, mock_service):
        """Draft entries and snapshot flag are forwarded to the service."""
        mock_service.run_preview_for_project.return_value = {"changed_chunks": []}

        response = client.post(
            "/api/project/text-processor-config/preview",
            params={"input_path": "/workspace/input/my_script"},
            json={
                "entries": [SAMPLE_ENTRY],
                "include_preprocessor_snapshots": True,
            },
        )

        assert response.status_code == 200
        args = mock_service.run_preview_for_project.call_args
        assert args[0][1][0]["name"] == "skip_empty"
        assert args[0][2] is True

    def test_preview_validation_error(self, client, mock_service):
        """Draft validation failures return the error list."""
        mock_service.run_preview_for_project.side_effect = ConfigValidationError(
            [{"entry_index": 0, "message": "Invalid configuration for skip_empty"}]
        )

        response = client.post(
            "/api/project/text-processor-config/preview",
            params={"input_path": "/workspace/input/my_script"},
            json={"entries": [SAMPLE_ENTRY]},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is False
        assert body["details"]["errors"]


class TestPreviewDiffEndpoint:
    """Tests for POST /api/project/text-processor-config/preview-diff."""

    def test_preview_diff_ok(self, client, mock_service):
        """Draft/baseline entries and the cap are forwarded to the service."""
        mock_service.run_preview_diff_for_project.return_value = {
            "alignment": "index",
            "changed_chunk_count": 0,
            "changed_chunks": [],
        }

        response = client.post(
            "/api/project/text-processor-config/preview-diff",
            params={"input_path": "/workspace/input/my_script"},
            json={
                "draft_entries": [SAMPLE_ENTRY],
                "baseline_entries": [SAMPLE_ENTRY],
                "max_changed_chunks": 25,
            },
        )

        assert response.status_code == 200
        assert response.json()["data"]["alignment"] == "index"
        args = mock_service.run_preview_diff_for_project.call_args
        assert args[0][0] == "/workspace/input/my_script"
        assert args[0][1][0]["name"] == "skip_empty"
        assert args[0][2][0]["name"] == "skip_empty"
        assert args[0][3] == 25

    def test_preview_diff_baseline_defaults_to_disk(self, client, mock_service):
        """Omitting baseline_entries resolves the baseline from disk."""
        mock_service.run_preview_diff_for_project.return_value = {
            "alignment": "index",
            "changed_chunk_count": 0,
            "changed_chunks": [],
        }

        response = client.post(
            "/api/project/text-processor-config/preview-diff",
            params={"input_path": "/workspace/input/my_script"},
            json={"draft_entries": [SAMPLE_ENTRY]},
        )

        assert response.status_code == 200
        args = mock_service.run_preview_diff_for_project.call_args
        assert args[0][2] is None
        assert args[0][3] == 50  # default cap

    def test_preview_diff_validation_error(self, client, mock_service):
        """Validation failures return the error list."""
        mock_service.run_preview_diff_for_project.side_effect = ConfigValidationError(
            [{"entry_index": 0, "message": "Invalid configuration"}]
        )

        response = client.post(
            "/api/project/text-processor-config/preview-diff",
            params={"input_path": "/workspace/input/my_script"},
            json={"draft_entries": [SAMPLE_ENTRY]},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is False
        assert body["details"]["errors"]
