"""Chunk inventory API routes.

Exposes the per-project chunk inventory: every post-preprocessed screenplay
chunk with its audio-cache state (resolved filename, cached/missing status,
user-modified flag, shared-audio occurrences).
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..models import ChunkAnchorsResponse, ChunkInventoryResponse
from ..services.chunk_inventory_service import chunk_inventory_service
from ..services.pdf_anchor_service import pdf_anchor_service, resolve_project_pdf_path

router = APIRouter()


@router.get("/chunks/{project_name}/inventory", response_model=ChunkInventoryResponse)
def get_chunk_inventory(
    project_name: str, refresh: bool = False
) -> ChunkInventoryResponse:
    """Get the chunk inventory for a project.

    Runs the audio-generation planning phase to map every chunk to its cache
    state. Results are cached in memory until a mutation (variant commit,
    re-parse, config change) invalidates them; pass ``refresh=true`` to force
    recomputation.

    Args:
        project_name: The project name
        refresh: Bypass the in-memory cache and recompute from disk

    Returns:
        ChunkInventoryResponse with entries and per-speaker configs
    """
    # Intentionally synchronous: planning is blocking work (per-chunk hashing
    # plus cache-dir stats), so FastAPI runs it in its worker threadpool
    # instead of stalling the application event loop.
    try:
        return chunk_inventory_service.get_inventory(project_name, refresh=refresh)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get chunk inventory: {str(e)}"
        )


@router.get("/chunks/{project_name}/pdf-anchors", response_model=ChunkAnchorsResponse)
def get_pdf_anchors(project_name: str, refresh: bool = False) -> ChunkAnchorsResponse:
    """Get chunk-to-PDF anchors for a project's overlay view.

    Matches every post-preprocessed chunk's text against the source PDF's word
    boxes and returns per-chunk line rectangles (idx-aligned with the chunk
    inventory). Chunks that can't be confidently anchored are omitted and
    listed in ``unanchoredIdxs``. Results are cached in memory until a
    re-parse or text-processor config change invalidates them; pass
    ``refresh=true`` to force recomputation.

    Args:
        project_name: The project name
        refresh: Bypass the in-memory cache and recompute from disk

    Returns:
        ChunkAnchorsResponse with per-chunk rects and page dimensions
    """
    # This route is intentionally synchronous: pdfplumber extraction and
    # matching are blocking work, so FastAPI runs it in its worker threadpool
    # instead of blocking the application event loop.
    try:
        return pdf_anchor_service.get_anchors(project_name, refresh=refresh)
    except FileNotFoundError:
        # Missing screenplay JSON or PDF (path-security rejections surface as
        # FileNotFoundError too): report not-found without echoing filesystem
        # paths back to the client
        raise HTTPException(
            status_code=404,
            detail=f"Project or source PDF not found: {project_name}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to compute PDF anchors: {str(e)}"
        )


@router.get("/chunks/{project_name}/source-pdf")
async def get_source_pdf(project_name: str) -> FileResponse:
    """Serve a project's source PDF for the overlay view.

    Args:
        project_name: The project name

    Returns:
        FileResponse with the PDF file
    """
    try:
        pdf_path = resolve_project_pdf_path(project_name)
        return FileResponse(
            path=pdf_path,
            media_type="application/pdf",
            filename=f"{project_name}.pdf",
        )
    except FileNotFoundError as e:
        # The resolver's messages are path-free by design (security rejections
        # included), so the detail is safe to relay
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to serve source PDF: {str(e)}"
        )
