"""Audio generation API routes."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException

from ..models import GenerationRequest, TaskResponse, TaskStatusResponse
from ..services.generation_service import generation_service

router = APIRouter()


@router.post("/generate", response_model=TaskResponse)
async def create_generation_task(request: GenerationRequest) -> TaskResponse:
    """Create a new audio generation task."""
    try:
        return await generation_service.create_generation_task(request)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create generation task: {str(e)}"
        )


@router.get("/generate/tasks", response_model=List[TaskStatusResponse])
async def get_all_tasks() -> List[TaskStatusResponse]:
    """Get status of all generation tasks."""
    try:
        return generation_service.get_all_tasks()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get tasks: {str(e)}")


@router.get("/generate/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str) -> TaskStatusResponse:
    """Get the status of a specific generation task."""
    try:
        status = generation_service.get_task_status(task_id)
        if not status:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        return status
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get task status: {str(e)}"
        )


@router.delete("/generate/cleanup")
async def cleanup_old_tasks(max_age_hours: int = 24) -> dict:
    """Clean up old completed tasks."""
    try:
        removed_count = generation_service.cleanup_old_tasks(max_age_hours)
        return {"message": f"Cleaned up {removed_count} old tasks"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to cleanup tasks: {str(e)}"
        )
