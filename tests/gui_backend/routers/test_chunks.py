"""Tests for the chunk inventory router."""

from unittest.mock import patch

from script_to_speech.gui_backend.models import ChunkInventoryResponse


def _fake_inventory() -> ChunkInventoryResponse:
    return ChunkInventoryResponse(
        project_name="proj",
        entries=[],
        speaker_configs={},
        total_chunks=0,
        cached_count=0,
        missing_count=0,
        user_modified_count=0,
        cache_folder="/tmp/cache",
        generated_at="2026-07-05T00:00:00+00:00",
    )


class TestChunkInventoryRoute:
    """Tests for GET /api/chunks/{project}/inventory."""

    def test_returns_inventory(self, client):
        with patch(
            "script_to_speech.gui_backend.routers.chunks.chunk_inventory_service"
        ) as mock_service:
            mock_service.get_inventory.return_value = _fake_inventory()

            response = client.get("/api/chunks/proj/inventory")

        assert response.status_code == 200
        data = response.json()
        # CamelModel serialization
        assert data["projectName"] == "proj"
        assert data["totalChunks"] == 0
        assert data["cacheFolder"] == "/tmp/cache"
        mock_service.get_inventory.assert_called_once_with("proj", refresh=False)

    def test_refresh_param_forwarded(self, client):
        with patch(
            "script_to_speech.gui_backend.routers.chunks.chunk_inventory_service"
        ) as mock_service:
            mock_service.get_inventory.return_value = _fake_inventory()

            response = client.get("/api/chunks/proj/inventory?refresh=true")

        assert response.status_code == 200
        mock_service.get_inventory.assert_called_once_with("proj", refresh=True)

    def test_missing_project_returns_404(self, client):
        with patch(
            "script_to_speech.gui_backend.routers.chunks.chunk_inventory_service"
        ) as mock_service:
            mock_service.get_inventory.side_effect = FileNotFoundError(
                "Screenplay JSON not found"
            )

            response = client.get("/api/chunks/missing/inventory")

        assert response.status_code == 404
