"""Screenplay parsing API routes."""

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from script_to_speech.parser.analyze import analyze_chunks
from script_to_speech.parser.header_footer.detector import HeaderFooterDetector
from script_to_speech.parser.header_footer.models import PatternPosition
from script_to_speech.parser.process import process_screenplay
from script_to_speech.utils.file_system_utils import PathSecurityValidator

from ..config import settings
from ..models import (
    AUTO_APPLY_THRESHOLD,
    SUGGESTION_THRESHOLD,
    DetectedPatternResponse,
    DetectionResultResponse,
    ReparseRequest,
    ReparseResponse,
    TaskResponse,
    TaskStatusResponse,
)
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
        validator = PathSecurityValidator(settings.WORKSPACE_DIR)

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

        # Use the same analysis function as manual mode for consistency (DRY)
        analysis = analyze_chunks(chunks, log_results=False) if chunks else {}

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


def _serve_screenplay_file(file_path: str, filename: str) -> FileResponse:
    """Helper function to serve a screenplay file with proper validation.

    Args:
        file_path: Full path to the file to serve
        filename: Filename to use in the download

    Returns:
        FileResponse with the requested file

    Raises:
        HTTPException: If file doesn't exist
    """
    # Verify file exists
    path_obj = Path(file_path)
    if not path_obj.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    # Return the file
    return FileResponse(
        path=file_path, filename=filename, media_type="application/octet-stream"
    )


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

        # Use helper to serve the file
        return _serve_screenplay_file(file_path, filename)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to download file: {str(e)}"
        )


@router.get("/download-from-path")
async def download_screenplay_file_from_path(
    file_path: str = Query(..., description="Full path to the screenplay file"),
    filename: str = Query(..., description="Filename to use for the download"),
) -> FileResponse:
    """Download a screenplay file from a known filesystem path (for project mode).

    Args:
        file_path: Full path to the screenplay file
        filename: Filename to use in the download

    Returns:
        FileResponse with the requested file
    """
    try:
        # Validate the file path for security
        validator = PathSecurityValidator(settings.WORKSPACE_DIR)
        safe_path = validator.validate_existing_path(Path(file_path))

        # Use helper to serve the file
        return _serve_screenplay_file(str(safe_path), filename)

    except ValueError as e:
        # Path validation failed
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to download file: {str(e)}"
        )


@router.post("/detect-headers", response_model=DetectionResultResponse)
async def detect_headers(
    pdf_path: str = Query(..., description="Path to the PDF file"),
    lines_to_scan: int = Query(
        2, ge=1, le=10, description="Lines from top/bottom to scan"
    ),
    min_occurrences: Optional[int] = Query(
        None,
        ge=1,
        description="Minimum occurrences to report (auto-adjusted for short scripts if not provided)",
    ),
    threshold: float = Query(
        SUGGESTION_THRESHOLD,
        ge=0,
        le=100,
        description="Minimum occurrence percentage to include",
    ),
) -> DetectionResultResponse:
    """Detect header/footer patterns in a PDF file.

    Args:
        pdf_path: Path to the PDF file to analyze
        lines_to_scan: Number of non-blank lines to scan from top/bottom of each page
        min_occurrences: Minimum page occurrences to report (auto-adjusted for short scripts)
        threshold: Minimum occurrence percentage to include in results

    Returns:
        DetectionResultResponse with classified patterns
    """
    try:
        # Validate the PDF path
        validator = PathSecurityValidator(settings.WORKSPACE_DIR)
        safe_path = validator.validate_existing_path(Path(pdf_path))

        if not safe_path.suffix.lower() == ".pdf":
            raise HTTPException(status_code=400, detail="File must be a PDF")

        # Create detector and run detection
        detector = HeaderFooterDetector(
            lines_to_scan=lines_to_scan,
            min_occurrences=min_occurrences or 10,  # Will be adjusted below
        )
        result = detector.detect(str(safe_path))

        # Auto-adjust min_occurrences for short scripts if not explicitly provided
        # For short scripts, 20% threshold might be less than default min_occurrences=10
        if min_occurrences is None and result.total_pages > 0:
            adjusted_min = max(2, math.floor(result.total_pages * 0.15))
            if adjusted_min < 10:
                # Re-run with adjusted min_occurrences
                detector = HeaderFooterDetector(
                    lines_to_scan=lines_to_scan,
                    min_occurrences=adjusted_min,
                )
                result = detector.detect(str(safe_path))

        # Convert patterns to response format and classify
        patterns: List[DetectedPatternResponse] = []
        auto_applied: List[DetectedPatternResponse] = []
        suggested: List[DetectedPatternResponse] = []

        for pattern in result.patterns:
            # Skip patterns below threshold
            if pattern.occurrence_percentage < threshold:
                continue

            # Determine classification
            is_auto_applied = pattern.occurrence_percentage >= AUTO_APPLY_THRESHOLD
            is_suggestion = (
                SUGGESTION_THRESHOLD
                <= pattern.occurrence_percentage
                < AUTO_APPLY_THRESHOLD
            )

            pattern_response = DetectedPatternResponse(
                text=pattern.text,
                position=pattern.position.value,
                occurrence_count=pattern.occurrence_count,
                total_pages=pattern.total_pages,
                occurrence_percentage=pattern.occurrence_percentage,
                is_blacklisted=pattern.is_blacklisted,
                example_full_lines=pattern.example_full_lines[
                    :3
                ],  # Limit to 3 examples
                variations=pattern.variations,
                is_auto_applied=is_auto_applied,
                is_suggestion=is_suggestion,
            )
            patterns.append(pattern_response)

            if is_auto_applied:
                auto_applied.append(pattern_response)
            elif is_suggestion:
                suggested.append(pattern_response)

        return DetectionResultResponse(
            patterns=patterns,
            pdf_path=str(safe_path),
            total_pages=result.total_pages,
            lines_scanned=lines_to_scan,
            auto_applied_patterns=auto_applied,
            suggested_patterns=suggested,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to detect headers/footers: {str(e)}"
        )


# Track which projects are currently being parsed to prevent concurrent parses
_parsing_locks: Dict[str, bool] = {}


@router.post("/reparse", response_model=ReparseResponse)
async def reparse_screenplay(request: ReparseRequest) -> ReparseResponse:
    """Re-parse a screenplay with header/footer removal options.

    Args:
        request: ReparseRequest with removal options

    Returns:
        ReparseResponse with success status and removal metadata
    """
    try:
        # Validate paths
        validator = PathSecurityValidator(settings.WORKSPACE_DIR)
        safe_input_path = validator.validate_existing_path(Path(request.input_path))

        # Find the source PDF
        pdf_path = safe_input_path / f"{request.screenplay_name}.pdf"
        if not pdf_path.exists():
            # Check source_screenplays directory
            source_dir = settings.WORKSPACE_DIR / "source_screenplays"
            pdf_path = source_dir / f"{request.screenplay_name}.pdf"
            if not pdf_path.exists():
                raise HTTPException(
                    status_code=404,
                    detail=f"PDF file not found for screenplay: {request.screenplay_name}",
                )

        # Check for concurrent parse lock
        lock_key = str(safe_input_path)
        if _parsing_locks.get(lock_key):
            raise HTTPException(
                status_code=409,
                detail="A parse operation is already in progress for this project",
            )

        try:
            # Set the lock
            _parsing_locks[lock_key] = True

            # Determine remove_lines value
            remove_lines = 0 if request.global_replace else request.remove_lines

            # Filter out empty strings and normalize entries
            strings_to_remove = [
                s.strip() for s in request.strings_to_remove if s.strip()
            ]

            # Run the parser with removal options
            result = process_screenplay(
                input_file=str(pdf_path),
                base_path=settings.WORKSPACE_DIR,
                text_only=False,
                strings_to_remove=strings_to_remove if strings_to_remove else None,
                remove_lines=remove_lines,
            )

            return ReparseResponse(
                success=True,
                message=f"Successfully re-parsed screenplay with {len(strings_to_remove)} patterns removed",
                removal_metadata=result.get("removal_metadata"),
            )

        finally:
            # Always release the lock
            _parsing_locks.pop(lock_key, None)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to re-parse screenplay: {str(e)}"
        )
