"""Project discovery and status API routes."""

import logging
import tempfile
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from ..models import (
    ApiResponse,
    NewProjectRequest,
    NewProjectResponse,
    ProjectMeta,
    ProjectStatus,
)
from ..services.project_service import project_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/projects/discover")
async def discover_projects(
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of projects to return"
    ),
    cursor: Optional[str] = Query(
        None, description="Optional cursor for pagination (not implemented yet)"
    ),
) -> ApiResponse:
    """Discover existing projects in the workspace.

    Returns projects sorted by last modified date (most recent first).
    """
    try:
        projects = project_service.discover_projects(limit=limit, cursor=cursor)

        return ApiResponse(ok=True, data=projects)

    except Exception as e:
        logger.error(f"Failed to discover projects: {e}")
        return ApiResponse(
            ok=False,
            error="Failed to discover projects",
            details={"error_message": str(e)},
        )


@router.get("/project/status")
async def get_project_status(
    input_path: str = Query(..., description="Path to the project's input directory")
) -> ApiResponse:
    """Get detailed status for a specific project.

    Includes file existence checks, metadata extraction, and error detection
    for corrupted JSON/YAML files.
    """
    try:
        status = project_service.get_project_status(input_path)

        return ApiResponse(ok=True, data=status)

    except ValueError as e:
        # Client error - invalid path or project not found
        logger.warning(f"Invalid project path {input_path}: {e}")
        return ApiResponse(
            ok=False,
            error="Invalid project path",
            details={"path": input_path, "error_message": str(e)},
        )

    except Exception as e:
        # Server error
        logger.error(f"Failed to get project status for {input_path}: {e}")
        return ApiResponse(
            ok=False,
            error="Failed to get project status",
            details={"path": input_path, "error_message": str(e)},
        )


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)) -> ApiResponse:
    """Upload a file to temporary storage.

    Used for new project creation workflow.
    """
    try:
        # Validate file size (50MB limit)
        MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB in bytes
        if file.size and file.size > MAX_FILE_SIZE:
            return ApiResponse(
                ok=False,
                error="File too large",
                details={
                    "max_size_mb": 50,
                    "file_size_mb": file.size / (1024 * 1024) if file.size else 0,
                },
            )

        # Validate file type
        if not file.filename:
            return ApiResponse(ok=False, error="No filename provided")

        file_extension = file.filename.lower().split(".")[-1]
        if file_extension not in ["pdf", "txt"]:
            return ApiResponse(
                ok=False,
                error="Invalid file type",
                details={
                    "allowed_types": ["pdf", "txt"],
                    "provided_type": file_extension,
                },
            )

        # Save to temporary file
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=f".{file_extension}"
        ) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name

        logger.info(f"Uploaded file {file.filename} to temporary path: {temp_path}")

        return ApiResponse(ok=True, data={"tempPath": temp_path})

    except Exception as e:
        logger.error(f"Failed to upload file: {e}")
        return ApiResponse(
            ok=False, error="Failed to upload file", details={"error_message": str(e)}
        )


@router.post("/project/new")
async def create_new_project(request: NewProjectRequest) -> ApiResponse:
    """Create a new project from an uploaded screenplay file.

    Args:
        request: Request containing the temporary file path

    Returns:
        Project metadata with input/output paths
    """
    try:
        # Validate request
        if not request.sourceFile:
            return ApiResponse(ok=False, error="sourceFile is required")

        # Check if temp file exists
        temp_path = Path(request.sourceFile)
        if not temp_path.exists():
            return ApiResponse(
                ok=False,
                error="Temporary file not found",
                details={"source_file": request.sourceFile},
            )

        # Create project
        project_data = project_service.create_new_project_from_upload(
            request.sourceFile
        )

        # Clean up temp file
        try:
            temp_path.unlink()
        except Exception as e:
            logger.warning(f"Failed to clean up temp file {temp_path}: {e}")

        return ApiResponse(ok=True, data=project_data)

    except ValueError as e:
        # Client error - invalid input
        logger.warning(f"Invalid request for project creation: {e}")
        return ApiResponse(
            ok=False, error=str(e), details={"source_file": request.sourceFile}
        )

    except RuntimeError as e:
        # Server error - CLI parsing failed
        logger.error(f"CLI parsing failed for project creation: {e}")
        return ApiResponse(
            ok=False,
            error="Failed to parse screenplay",
            details={"error_message": str(e)},
        )

    except Exception as e:
        # Generic server error
        logger.error(f"Failed to create project: {e}")
        return ApiResponse(
            ok=False,
            error="Failed to create project",
            details={"error_message": str(e)},
        )
