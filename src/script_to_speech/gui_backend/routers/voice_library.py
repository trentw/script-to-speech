"""Voice library API routes."""

import mimetypes
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from ..config import settings
from ..models import (
    LLMRunImportRequest,
    LLMRunImportResponse,
    VoiceDetails,
    VoiceEntry,
    VoiceLibrarySchemaResponse,
    VoiceUpdateRequest,
)
from ..services.voice_library_service import voice_library_service

router = APIRouter()


@router.get("/voice-library/providers", response_model=List[str])
async def get_voice_library_providers() -> List[str]:
    """Get list of providers with voice library data."""
    try:
        return voice_library_service.get_available_providers()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get providers: {str(e)}"
        )


@router.get("/voice-library/search", response_model=List[VoiceEntry])
async def search_voices(
    query: Optional[str] = Query(None, description="Search query"),
    provider: Optional[str] = Query(None, description="Provider filter"),
    gender: Optional[str] = Query(None, description="Gender filter"),
    tags: Optional[List[str]] = Query(None, description="Tags filter"),
) -> List[VoiceEntry]:
    """Search voices based on criteria."""
    try:
        return voice_library_service.search_voices(
            query=query, provider=provider, gender=gender, tags=tags
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to search voices: {str(e)}"
        )


@router.get("/voice-library/schema", response_model=VoiceLibrarySchemaResponse)
async def get_voice_library_schema() -> VoiceLibrarySchemaResponse:
    """Get the voice library property schema."""
    try:
        return voice_library_service.get_schema()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get schema: {str(e)}")


@router.get("/voice-library/stats")
async def get_voice_library_stats() -> dict:
    """Get statistics about the voice library."""
    try:
        return voice_library_service.get_voice_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.get("/voice-library/llm-runs")
async def list_llm_runs() -> list:
    """List available LLM labeler run directories."""
    try:
        return voice_library_service.list_llm_runs()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to list LLM runs: {str(e)}"
        )


# Static path routes must come before parameterized {provider} routes
@router.post("/voice-library/import-llm-run", response_model=LLMRunImportResponse)
async def import_llm_run(request: LLMRunImportRequest) -> LLMRunImportResponse:
    """Import an LLM voice labeler run directory."""
    try:
        return voice_library_service.load_llm_run(request.run_dir)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to import LLM run: {str(e)}"
        )


@router.get("/voice-library/llm-run-audio/{run_id}/{filename}")
async def get_llm_run_audio(run_id: str, filename: str) -> FileResponse:
    """Serve an audio file from an LLM run output directory."""
    # Reject path traversal attempts
    if ".." in run_id or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid path component")
    if "/" in run_id or "\\" in run_id or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid path component")

    # Resolve against output directory
    output_dir = settings.WORKSPACE_DIR / "output"
    audio_path = (output_dir / run_id / "audio" / filename).resolve()

    # Ensure resolved path is within output directory
    if not str(audio_path).startswith(str(output_dir.resolve())):
        raise HTTPException(status_code=400, detail="Invalid path")

    # Reject symlinks
    if audio_path.is_symlink():
        raise HTTPException(status_code=400, detail="Symlinks not allowed")

    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")

    media_type = mimetypes.guess_type(filename)[0] or "audio/mpeg"
    return FileResponse(
        path=str(audio_path),
        media_type=media_type,
        filename=filename,
    )


# Parameterized routes below - order matters for FastAPI path matching


@router.get("/voice-library/{provider}", response_model=List[VoiceEntry])
async def get_provider_voices(provider: str) -> List[VoiceEntry]:
    """Get all voices for a specific provider."""
    try:
        voices = voice_library_service.get_provider_voices(provider)
        if (
            not voices
            and provider not in voice_library_service.get_available_providers()
        ):
            raise HTTPException(
                status_code=404, detail=f"Provider {provider} not found"
            )
        return voices
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get voices: {str(e)}")


@router.get("/voice-library/{provider}/{sts_id}", response_model=VoiceDetails)
async def get_voice_details(provider: str, sts_id: str) -> VoiceDetails:
    """Get detailed information about a specific voice."""
    try:
        voice_details = voice_library_service.get_voice_details(provider, sts_id)
        if not voice_details:
            raise HTTPException(
                status_code=404, detail=f"Voice {provider}/{sts_id} not found"
            )
        return voice_details
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get voice details: {str(e)}"
        )


@router.put("/voice-library/{provider}/{sts_id}", response_model=VoiceEntry)
async def update_voice(
    provider: str, sts_id: str, request: VoiceUpdateRequest
) -> VoiceEntry:
    """Update a voice's properties, description, or tags."""
    try:
        return voice_library_service.update_voice(provider, sts_id, request)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update voice: {str(e)}")


@router.post("/voice-library/{provider}/{sts_id}/expand")
async def expand_sts_id(provider: str, sts_id: str) -> dict:
    """Expand an sts_id to full provider configuration."""
    try:
        config = voice_library_service.expand_sts_id(provider, sts_id)
        if not config:
            raise HTTPException(
                status_code=404, detail=f"Voice {provider}/{sts_id} not found"
            )
        return config
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to expand sts_id: {str(e)}"
        )
