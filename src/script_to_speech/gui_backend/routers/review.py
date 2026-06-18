"""Audio review API routes.

Provides endpoints for reviewing and managing problem audio clips
(silent clips and cache misses) in a project.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..models import (
    CacheMissesResponse,
    CommitVariantRequest,
    CommitVariantResponse,
    DeleteVariantRequest,
    SilenceScanProgress,
    SilentClipsResponse,
)
from ..services.review_service import review_service

router = APIRouter()


@router.get("/review/cache-misses/{project_name}", response_model=CacheMissesResponse)
async def get_cache_misses(project_name: str) -> CacheMissesResponse:
    """Get cache misses for a project (fast operation).

    Runs the planning phase to identify dialogue lines that don't have
    cached audio files.

    Args:
        project_name: The project name

    Returns:
        CacheMissesResponse with cache misses list
    """
    try:
        return review_service.get_cache_misses(project_name)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get cache misses: {str(e)}"
        )


@router.get("/review/silent-clips/{project_name}", response_model=SilentClipsResponse)
async def get_silent_clips(project_name: str) -> SilentClipsResponse:
    """Get silent clips for a project from cache.

    Returns cached data populated by audio generation or a completed scan.
    To (re)scan, start a background scan via the scan endpoint and poll
    scan-progress; results land in this cache when the scan completes.

    Args:
        project_name: The project name

    Returns:
        SilentClipsResponse with silent clips list
    """
    try:
        return review_service.get_silent_clips(project_name)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get silent clips: {str(e)}"
        )


@router.post(
    "/review/silent-clips/{project_name}/scan",
    response_model=SilenceScanProgress,
)
async def start_silent_clips_scan(project_name: str) -> SilenceScanProgress:
    """Start a background silent-clips scan for a project.

    Returns immediately with the scan's initial progress. Poll the
    scan-progress endpoint to track completion; results are written to the
    silent-clips cache when the scan finishes. If a scan is already running
    (e.g. an in-flight generation run), this returns that scan's progress
    instead of starting a second one.

    Args:
        project_name: The project name

    Returns:
        SilenceScanProgress for the new or in-flight scan
    """
    try:
        return review_service.start_scan(project_name)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to start silent-clips scan: {str(e)}"
        )


@router.get(
    "/review/silent-clips/{project_name}/scan-progress",
    response_model=SilenceScanProgress,
)
async def get_silent_clips_scan_progress(project_name: str) -> SilenceScanProgress:
    """Get progress of a project's in-flight / most-recent silence scan.

    Args:
        project_name: The project name

    Returns:
        SilenceScanProgress (status="idle" if no scan has run)
    """
    try:
        return review_service.get_scan_progress(project_name)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get scan progress: {str(e)}"
        )


@router.post("/review/commit", response_model=CommitVariantResponse)
async def commit_variant(request: CommitVariantRequest) -> CommitVariantResponse:
    """Commit a generated variant to the project cache.

    Copies the file from standalone_speech to the project's cache directory,
    replacing any existing file with the same name.

    Args:
        request: CommitVariantRequest with source path and target filename

    Returns:
        CommitVariantResponse with success status and target path
    """
    try:
        success, target_path, message = review_service.commit_variant(
            source_path=request.source_path,
            target_cache_filename=request.target_cache_filename,
            project_name=request.project_name,
        )
        return CommitVariantResponse(
            success=success,
            target_path=target_path,
            message=message,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to commit variant: {str(e)}"
        )


@router.delete("/review/variant")
async def delete_variant(request: DeleteVariantRequest) -> dict:
    """Delete a variant file from standalone_speech.

    Args:
        request: DeleteVariantRequest with file path

    Returns:
        Dict with success status
    """
    try:
        success = review_service.delete_variant(request.file_path)
        return {"success": success}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete variant: {str(e)}"
        )


@router.get("/review/cache-audio/{project_name}/{filename}")
async def get_cache_audio(project_name: str, filename: str) -> FileResponse:
    """Serve an audio file from the project cache folder.

    This allows playing cached audio files (e.g., silent clips that exist
    but need review) without exposing the full filesystem.

    Args:
        project_name: The project name
        filename: The cache filename

    Returns:
        FileResponse with the audio file
    """
    try:
        file_path = review_service.get_cache_audio_path(project_name, filename)

        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {filename}")

        return FileResponse(
            path=file_path,
            media_type="audio/mpeg",
            filename=filename,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to serve audio file: {str(e)}"
        )
