"""Audiobook generation API routes."""

from typing import List

from fastapi import APIRouter, HTTPException

from ..models import (
    AudiobookGenerationProgress,
    AudiobookGenerationRequest,
    AudiobookGenerationResult,
    AudiobookTaskResponse,
    TaskStatus,
)
from ..services.audiobook_generation_service import audiobook_generation_service

router = APIRouter()


@router.post("/audiobook/generate", response_model=AudiobookTaskResponse)
async def create_audiobook_task(
    request: AudiobookGenerationRequest,
) -> AudiobookTaskResponse:
    """Create a new audiobook generation task.

    This starts the audio generation pipeline in the background.
    Use the /audiobook/status/{task_id} endpoint to poll for progress.

    Args:
        request: AudiobookGenerationRequest with input paths and generation options

    Returns:
        AudiobookTaskResponse with the new task ID
    """
    try:
        task_id = audiobook_generation_service.create_task(request)
        return AudiobookTaskResponse(
            task_id=task_id,
            status=TaskStatus.PENDING.value,
            message="Audiobook generation task created",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create audiobook task: {str(e)}"
        )


@router.get("/audiobook/status/{task_id}", response_model=AudiobookGenerationProgress)
async def get_audiobook_status(task_id: str) -> AudiobookGenerationProgress:
    """Get the current progress of an audiobook generation task.

    This endpoint should be polled to track generation progress.
    During the GENERATING phase, it includes detailed clip-level statistics.

    Args:
        task_id: The unique task identifier

    Returns:
        AudiobookGenerationProgress with phase, progress, and stats
    """
    try:
        progress = audiobook_generation_service.get_progress(task_id)
        if not progress:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        return progress
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get task status: {str(e)}"
        )


@router.get("/audiobook/result/{task_id}", response_model=AudiobookGenerationResult)
async def get_audiobook_result(task_id: str) -> AudiobookGenerationResult:
    """Get the final result of a completed audiobook generation task.

    Only available after the task reaches COMPLETED status.
    Includes output file path, final statistics, and any issues detected.

    Args:
        task_id: The unique task identifier

    Returns:
        AudiobookGenerationResult with output file and statistics
    """
    try:
        result = audiobook_generation_service.get_result(task_id)
        if not result:
            # Check if task exists but isn't completed
            progress = audiobook_generation_service.get_progress(task_id)
            if not progress:
                raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Task {task_id} is not completed (status: {progress.status.value})",
                )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get task result: {str(e)}"
        )


@router.get("/audiobook/tasks", response_model=List[AudiobookGenerationProgress])
async def get_all_audiobook_tasks() -> List[AudiobookGenerationProgress]:
    """Get status of all audiobook generation tasks.

    Returns a list of all tracked generation tasks with their current progress.

    Returns:
        List of AudiobookGenerationProgress for all tasks
    """
    try:
        return audiobook_generation_service.get_all_tasks()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get audiobook tasks: {str(e)}"
        )


@router.delete("/audiobook/cleanup")
async def cleanup_old_audiobook_tasks(max_age_hours: int = 24) -> dict:
    """Clean up old completed audiobook generation tasks.

    Removes tasks from memory that have been completed for longer
    than the specified age. Does not delete any generated files.

    Args:
        max_age_hours: Maximum age in hours before cleanup (default: 24)

    Returns:
        Dictionary with count of removed tasks
    """
    try:
        removed_count = audiobook_generation_service.cleanup_old_tasks(max_age_hours)
        return {"message": f"Cleaned up {removed_count} old audiobook tasks"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to cleanup audiobook tasks: {str(e)}"
        )
