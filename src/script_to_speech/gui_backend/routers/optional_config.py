"""Optional config API routes (ID3 tags, etc.)."""

import logging

from fastapi import APIRouter, Query

from ..models import ApiResponse, Id3TagConfig, Id3TagConfigUpdate
from ..services.project_service import project_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/project/id3-config")
async def get_id3_tag_config(
    input_path: str = Query(..., description="Path to the project's input directory"),
) -> ApiResponse:
    """Get ID3 tag configuration for a project.

    Auto-creates the optional_config.yaml with defaults if it doesn't exist.
    """
    try:
        data = project_service.get_id3_tag_config(input_path)
        config = Id3TagConfig(**data)
        return ApiResponse(ok=True, data=config.model_dump(by_alias=True))

    except ValueError as e:
        logger.warning(f"Invalid project path {input_path}: {e}")
        return ApiResponse(
            ok=False,
            error="Invalid project path",
            details={"path": input_path, "error_message": str(e)},
        )

    except Exception as e:
        logger.error(f"Failed to get ID3 tag config for {input_path}: {e}")
        return ApiResponse(
            ok=False,
            error="Failed to get ID3 tag configuration",
            details={"path": input_path, "error_message": str(e)},
        )


@router.put("/project/id3-config")
async def update_id3_tag_config(
    body: Id3TagConfigUpdate,
    input_path: str = Query(..., description="Path to the project's input directory"),
) -> ApiResponse:
    """Update ID3 tag configuration for a project.

    Accepts partial updates — only non-null fields are applied.
    Auto-creates the optional_config.yaml with defaults if it doesn't exist.
    """
    try:
        updates = body.model_dump(exclude_none=True, by_alias=False)
        data = project_service.update_id3_tag_config(input_path, updates)
        config = Id3TagConfig(**data)
        return ApiResponse(ok=True, data=config.model_dump(by_alias=True))

    except ValueError as e:
        logger.warning(f"Invalid project path {input_path}: {e}")
        return ApiResponse(
            ok=False,
            error="Invalid project path",
            details={"path": input_path, "error_message": str(e)},
        )

    except Exception as e:
        logger.error(f"Failed to update ID3 tag config for {input_path}: {e}")
        return ApiResponse(
            ok=False,
            error="Failed to update ID3 tag configuration",
            details={"path": input_path, "error_message": str(e)},
        )
