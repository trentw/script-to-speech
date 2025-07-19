"""Provider API routes."""

from typing import List
from fastapi import APIRouter, HTTPException

from ..models import ProviderInfo, ValidationResult
from ..services.provider_service import provider_service

router = APIRouter()


@router.get("/providers", response_model=List[str])
async def get_available_providers() -> List[str]:
    """Get list of available TTS providers."""
    try:
        return provider_service.get_available_providers()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get providers: {str(e)}"
        )


@router.get("/providers/info", response_model=List[ProviderInfo])
async def get_all_providers_info() -> List[ProviderInfo]:
    """Get detailed information about all providers."""
    try:
        return provider_service.get_all_providers()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get provider info: {str(e)}"
        )


@router.get("/providers/{provider}", response_model=ProviderInfo)
async def get_provider_info(provider: str) -> ProviderInfo:
    """Get detailed information about a specific provider."""
    try:
        return provider_service.get_provider_info(provider)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get provider info: {str(e)}"
        )


@router.post("/providers/{provider}/validate", response_model=ValidationResult)
async def validate_provider_config(provider: str, config: dict) -> ValidationResult:
    """Validate a provider configuration."""
    try:
        return provider_service.validate_config(provider, config)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to validate config: {str(e)}"
        )
