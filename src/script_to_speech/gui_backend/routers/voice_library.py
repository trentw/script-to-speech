"""Voice library API routes."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query

from ..models import VoiceEntry, VoiceDetails
from ..services.voice_library_service import voice_library_service

router = APIRouter()


@router.get("/voice-library/providers", response_model=List[str])
async def get_voice_library_providers() -> List[str]:
    """Get list of providers with voice library data."""
    try:
        return voice_library_service.get_available_providers()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get providers: {str(e)}")


@router.get("/voice-library/{provider}", response_model=List[VoiceEntry])
async def get_provider_voices(provider: str) -> List[VoiceEntry]:
    """Get all voices for a specific provider."""
    try:
        voices = voice_library_service.get_provider_voices(provider)
        if not voices and provider not in voice_library_service.get_available_providers():
            raise HTTPException(status_code=404, detail=f"Provider {provider} not found")
        return voices
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get voices: {str(e)}")


@router.get("/voice-library/{provider}/{sts_id}", response_model=VoiceDetails)
async def get_voice_details(provider: str, sts_id: str) -> VoiceDetails:
    """Get detailed information about a specific voice."""
    try:
        voice_details = voice_library_service.get_voice_details(provider, sts_id)
        if not voice_details:
            raise HTTPException(status_code=404, detail=f"Voice {provider}/{sts_id} not found")
        return voice_details
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get voice details: {str(e)}")


@router.get("/voice-library/search", response_model=List[VoiceEntry])
async def search_voices(
    query: Optional[str] = Query(None, description="Search query"),
    provider: Optional[str] = Query(None, description="Provider filter"),
    gender: Optional[str] = Query(None, description="Gender filter"),
    tags: Optional[List[str]] = Query(None, description="Tags filter")
) -> List[VoiceEntry]:
    """Search voices based on criteria."""
    try:
        return voice_library_service.search_voices(
            query=query,
            provider=provider,
            gender=gender,
            tags=tags
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search voices: {str(e)}")


@router.get("/voice-library/stats")
async def get_voice_library_stats() -> dict:
    """Get statistics about the voice library."""
    try:
        return voice_library_service.get_voice_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.post("/voice-library/{provider}/{sts_id}/expand")
async def expand_sts_id(provider: str, sts_id: str) -> dict:
    """Expand an sts_id to full provider configuration."""
    try:
        config = voice_library_service.expand_sts_id(provider, sts_id)
        if not config:
            raise HTTPException(status_code=404, detail=f"Voice {provider}/{sts_id} not found")
        return config
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to expand sts_id: {str(e)}")