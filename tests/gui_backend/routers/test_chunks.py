"""Tests for the chunk inventory router."""

from unittest.mock import patch

from script_to_speech.gui_backend.models import (
    AnchorRect,
    ChunkAnchor,
    ChunkAnchorsResponse,
    ChunkInventoryResponse,
    PdfPageInfo,
)


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
        chunk_layout_revision="layout-rev-1",
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


def _fake_anchors() -> ChunkAnchorsResponse:
    return ChunkAnchorsResponse(
        project_name="proj",
        pages=[PdfPageInfo(page=0, width=612.0, height=792.0)],
        anchors=[
            ChunkAnchor(
                idx=0,
                rects=[AnchorRect(page=0, x0=100.0, top=72.0, x1=200.0, bottom=82.0)],
                match_ratio=1.0,
            )
        ],
        unanchored_idxs=[3],
        total_chunks=2,
        anchored_count=1,
        chunk_layout_revision="layout-rev-1",
        unsupported_geometry_pages=[],
        generated_at="2026-07-06T00:00:00+00:00",
    )


class TestPdfAnchorsRoute:
    """Tests for GET /api/chunks/{project}/pdf-anchors."""

    def test_returns_anchors(self, client):
        with patch(
            "script_to_speech.gui_backend.routers.chunks.pdf_anchor_service"
        ) as mock_service:
            mock_service.get_anchors.return_value = _fake_anchors()

            response = client.get("/api/chunks/proj/pdf-anchors")

        assert response.status_code == 200
        data = response.json()
        # CamelModel serialization
        assert data["projectName"] == "proj"
        assert data["anchoredCount"] == 1
        assert data["chunkLayoutRevision"] == "layout-rev-1"
        assert data["unsupportedGeometryPages"] == []
        assert data["unanchoredIdxs"] == [3]
        assert data["anchors"][0]["matchRatio"] == 1.0
        assert data["anchors"][0]["rects"][0]["top"] == 72.0
        mock_service.get_anchors.assert_called_once_with("proj", refresh=False)

    def test_refresh_param_forwarded(self, client):
        with patch(
            "script_to_speech.gui_backend.routers.chunks.pdf_anchor_service"
        ) as mock_service:
            mock_service.get_anchors.return_value = _fake_anchors()

            response = client.get("/api/chunks/proj/pdf-anchors?refresh=true")

        assert response.status_code == 200
        mock_service.get_anchors.assert_called_once_with("proj", refresh=True)

    def test_missing_pdf_returns_404(self, client):
        with patch(
            "script_to_speech.gui_backend.routers.chunks.pdf_anchor_service"
        ) as mock_service:
            mock_service.get_anchors.side_effect = FileNotFoundError(
                "No source PDF found for project: proj"
            )

            response = client.get("/api/chunks/proj/pdf-anchors")

        assert response.status_code == 404


class TestSourcePdfRoute:
    """Tests for GET /api/chunks/{project}/source-pdf."""

    def test_serves_pdf(self, client, tmp_path):
        pdf_file = tmp_path / "proj.pdf"
        pdf_file.write_bytes(b"%PDF-1.4\ntest\n")

        with patch(
            "script_to_speech.gui_backend.routers.chunks.resolve_project_pdf_path"
        ) as mock_resolve:
            mock_resolve.return_value = pdf_file

            response = client.get("/api/chunks/proj/source-pdf")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"

    def test_missing_pdf_returns_404(self, client):
        with patch(
            "script_to_speech.gui_backend.routers.chunks.resolve_project_pdf_path"
        ) as mock_resolve:
            mock_resolve.side_effect = FileNotFoundError(
                "No source PDF found for project: proj"
            )

            response = client.get("/api/chunks/proj/source-pdf")

        assert response.status_code == 404

    def test_resolver_not_found_is_404_without_path_leak(self, client):
        # The resolver reports both missing PDFs and path-security rejections
        # as FileNotFoundError with a path-free message; the route relays it
        with patch(
            "script_to_speech.gui_backend.routers.chunks.resolve_project_pdf_path"
        ) as mock_resolve:
            mock_resolve.side_effect = FileNotFoundError(
                "No source PDF found for project: proj"
            )

            response = client.get("/api/chunks/proj/source-pdf")

        assert response.status_code == 404
        assert "/Users/" not in response.json()["detail"]
