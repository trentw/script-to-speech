"""Screenplay parsing API routes."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from script_to_speech.utils.dialogue_stats_utils import get_speaker_statistics
from script_to_speech.utils.file_system_utils import PathSecurityValidator

from ..config import settings
from ..models import TaskResponse, TaskStatusResponse
from ..services.screenplay_service import screenplay_service

router = APIRouter()


@router.post("/parse", response_model=TaskResponse)
async def upload_and_parse_screenplay(
    file: UploadFile = File(...), text_only: bool = Form(False)
) -> TaskResponse:
    """Upload a screenplay file (PDF or TXT) and parse it to JSON chunks.

    Args:
        file: The screenplay file to upload
        text_only: If True, only extract text without parsing (PDF only)

    Returns:
        TaskResponse with the parsing task ID
    """
    try:
        # Validate file size (50MB limit)
        MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB in bytes
        if file.size and file.size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size allowed is {MAX_FILE_SIZE // (1024 * 1024)}MB.",
            )

        # Validate file type
        file_extension = file.filename.lower().split(".")[-1] if file.filename else ""
        if file_extension not in ["pdf", "txt"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Only PDF and TXT files are allowed.",
            )

        # Create parsing task
        return await screenplay_service.create_parsing_task(file, text_only)
    except HTTPException:
        # Re-raise HTTPExceptions with their original status codes
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create parsing task: {str(e)}"
        )


@router.get("/tasks", response_model=List[TaskStatusResponse])
async def get_all_parsing_tasks() -> List[TaskStatusResponse]:
    """Get status of all screenplay parsing tasks."""
    try:
        return screenplay_service.get_all_tasks()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get parsing tasks: {str(e)}"
        )


@router.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_parsing_task_status(task_id: str) -> TaskStatusResponse:
    """Get the status of a specific parsing task."""
    try:
        status = screenplay_service.get_task_status(task_id)
        if not status:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        return status
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get task status: {str(e)}"
        )


@router.get("/result/{task_id}")
async def get_parsing_result(task_id: str) -> Optional[Dict[str, Any]]:
    """Get the parsed JSON result and analysis for a completed task.

    Returns:
        JSON object containing:
        - chunks: The parsed screenplay chunks
        - analysis: Statistics about the screenplay
        - files: Generated file paths
    """
    try:
        result = screenplay_service.get_parsing_result(task_id)
        if not result:
            raise HTTPException(
                status_code=404, detail=f"Task {task_id} not found or not completed"
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get parsing result: {str(e)}"
        )


@router.get("/result-from-path")
async def get_screenplay_result_from_path(
    input_path: str = Query(..., description="Path to the project input directory"),
    screenplay_name: str = Query(
        ..., description="Name of the screenplay without extension"
    ),
) -> Dict[str, Any]:
    """Load and analyze screenplay from project path.

    Args:
        input_path: Path to the project's input directory
        screenplay_name: Name of the screenplay (without extension)

    Returns:
        ScreenplayResult compatible object with analysis and file paths
    """
    try:
        # Use existing PathSecurityValidator
        validator = PathSecurityValidator(settings.STS_ROOT_DIR)

        # Validate the input path
        safe_input_path = validator.validate_existing_path(Path(input_path))

        # Build paths
        json_path = safe_input_path / f"{screenplay_name}.json"
        text_path = safe_input_path / f"{screenplay_name}.txt"

        # Check if JSON file exists
        if not json_path.exists():
            raise HTTPException(
                status_code=404, detail=f"Screenplay JSON file not found at {json_path}"
            )

        # Read and parse JSON file
        with open(json_path, "r", encoding="utf-8") as f:
            chunks = json.load(f)

        # Analyze the screenplay using existing utilities
        if not isinstance(chunks, list):
            raise HTTPException(
                status_code=400,
                detail="Invalid screenplay JSON format - expected list of chunks",
            )

        # Get speaker statistics
        stats = get_speaker_statistics(chunks) if chunks else {}

        # Build analysis object
        analysis: Dict[str, Any] = {
            "total_chunks": len(chunks),
            "total_distinct_speakers": len(stats.get("speakers", {})),
            "total_lines": len(chunks),
            "speaker_counts": stats.get("speakers", {}),
            "chunk_type_counts": {},
        }

        # Count chunk types
        chunk_types: Dict[str, int] = {}
        for chunk in chunks:
            chunk_type = chunk.get("type", "unknown")
            chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1
        analysis["chunk_type_counts"] = chunk_types

        # Build result object
        result = {
            "screenplay_name": screenplay_name,
            "original_filename": f"{screenplay_name}.pdf",
            "analysis": analysis,
            "files": {
                "json": str(json_path),
                "text": str(text_path) if text_path.exists() else None,
            },
            "text_only": False,
            "chunks": (
                chunks[:10] if chunks else []
            ),  # Include first 10 chunks as preview
        }

        # Add log file path if it exists
        output_log_path = (
            Path(input_path).parent.parent
            / "output"
            / screenplay_name
            / "logs"
            / f"{screenplay_name}.log"
        )
        if output_log_path.exists():
            result["log_file"] = str(output_log_path)

        return result

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to load screenplay from path: {str(e)}"
        )


@router.get("/recent")
async def get_recent_screenplays(limit: int = 10) -> List[Dict[str, Any]]:
    """Get list of recently parsed screenplays.

    Args:
        limit: Maximum number of recent screenplays to return

    Returns:
        List of recent screenplay parsing tasks with their metadata
    """
    try:
        return screenplay_service.get_recent_screenplays(limit)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get recent screenplays: {str(e)}"
        )


@router.delete("/cleanup")
async def cleanup_old_parsing_tasks(max_age_hours: int = 24) -> dict:
    """Clean up old completed parsing tasks.

    Args:
        max_age_hours: Maximum age in hours for tasks to keep

    Returns:
        Number of tasks cleaned up
    """
    try:
        removed_count = screenplay_service.cleanup_old_tasks(max_age_hours)
        return {"message": f"Cleaned up {removed_count} old parsing tasks"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to cleanup tasks: {str(e)}"
        )


@router.delete("/{task_id}")
async def delete_parsing_task(task_id: str, delete_files: bool = False) -> dict:
    """Delete a parsing task and optionally its associated files.

    Args:
        task_id: The task ID to delete
        delete_files: If True, also delete the generated files

    Returns:
        Success message
    """
    try:
        success = screenplay_service.delete_task(task_id, delete_files)
        if not success:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        return {"message": f"Task {task_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete task: {str(e)}")


@router.get("/download/{task_id}/{file_type}")
async def download_screenplay_file(task_id: str, file_type: str) -> FileResponse:
    """Download a specific file from a completed screenplay parsing task.

    Args:
        task_id: The parsing task ID
        file_type: Type of file to download ('json', 'text', 'log')

    Returns:
        FileResponse with the requested file
    """
    try:
        # Get the parsing result to find file paths
        result = screenplay_service.get_parsing_result(task_id)
        if not result:
            raise HTTPException(
                status_code=404, detail=f"Task {task_id} not found or not completed"
            )

        # Determine the file path based on file type
        file_path = None
        filename = None

        if file_type == "json" and result.get("files", {}).get("json"):
            file_path = result["files"]["json"]
            filename = f"{result.get('screenplay_name', 'screenplay')}.json"
        elif file_type == "text" and result.get("files", {}).get("text"):
            file_path = result["files"]["text"]
            filename = f"{result.get('screenplay_name', 'screenplay')}.txt"
        elif file_type == "log" and result.get("log_file"):
            file_path = result["log_file"]
            filename = f"{result.get('screenplay_name', 'screenplay')}_log.txt"
        else:
            raise HTTPException(
                status_code=404,
                detail=f"File type '{file_type}' not found for task {task_id}",
            )

        # Verify file exists
        path_obj = Path(file_path)
        if not path_obj.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

        # Return the file
        return FileResponse(
            path=file_path, filename=filename, media_type="application/octet-stream"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to download file: {str(e)}"
        )
