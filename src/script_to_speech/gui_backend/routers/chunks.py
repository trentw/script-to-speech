"""Chunk inventory API routes.

Exposes the per-project chunk inventory: every post-preprocessed screenplay
chunk with its audio-cache state (resolved filename, cached/missing status,
user-modified flag, shared-audio occurrences).
"""

from fastapi import APIRouter, HTTPException

from ..models import ChunkInventoryResponse
from ..services.chunk_inventory_service import chunk_inventory_service

router = APIRouter()


@router.get("/chunks/{project_name}/inventory", response_model=ChunkInventoryResponse)
async def get_chunk_inventory(
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
    try:
        return chunk_inventory_service.get_inventory(project_name, refresh=refresh)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get chunk inventory: {str(e)}"
        )
