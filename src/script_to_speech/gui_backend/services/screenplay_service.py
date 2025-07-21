"""Screenplay parsing service."""

import asyncio
import json
import logging
import os
import shutil
import tempfile
import uuid
from datetime import datetime, UTC
from pathlib import Path
from typing import Dict, Any, List, Optional
import threading

from fastapi import UploadFile

from script_to_speech.utils.file_system_utils import sanitize_name

from ..models import TaskResponse, TaskStatus, TaskStatusResponse
from ..config import settings

logger = logging.getLogger(__name__)


class ScreenplayParsingTask:
    """Represents a screenplay parsing task."""

    def __init__(self, task_id: str, filename: str, text_only: bool = False):
        self.task_id = task_id
        self.filename = filename
        self.original_filename = filename
        self.text_only = text_only
        self.status = TaskStatus.PENDING
        self.progress = 0.0
        self.message = "Task created"
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.created_at = datetime.now(UTC)
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.temp_file_path: Optional[str] = None
        self.output_dir: Optional[str] = None


class ScreenplayService:
    """Service for managing screenplay parsing tasks."""

    def __init__(self) -> None:
        """Initialize the screenplay service."""
        self._tasks: Dict[str, ScreenplayParsingTask] = {}
        self._lock = threading.Lock()

        # Ensure upload directory exists
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

        # Ensure source_screenplays directory exists - use absolute path
        self.source_screenplays_dir = Path.cwd() / "source_screenplays"
        self.source_screenplays_dir.mkdir(parents=True, exist_ok=True)

    async def create_parsing_task(
        self, file: UploadFile, text_only: bool = False
    ) -> TaskResponse:
        """Create a new screenplay parsing task.

        Args:
            file: The uploaded screenplay file
            text_only: If True, only extract text without parsing (PDF only)

        Returns:
            TaskResponse with the new task ID
        """
        task_id = str(uuid.uuid4())
        task = ScreenplayParsingTask(task_id, file.filename or "screenplay", text_only)

        # Save uploaded file to temporary location
        temp_file = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=Path(file.filename).suffix if file.filename else ".pdf",
            dir=str(self.upload_dir),
        )

        try:
            # Save uploaded file
            content = await file.read()
            temp_file.write(content)
            temp_file.flush()
            task.temp_file_path = temp_file.name

            with self._lock:
                self._tasks[task_id] = task

            # Start the parsing in the background
            asyncio.create_task(self._process_parsing_task(task))

            return TaskResponse(
                task_id=task_id,
                status=TaskStatus.PENDING,
                message="Parsing task created",
            )
        except Exception as e:
            # Clean up temp file on error
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
            raise
        finally:
            temp_file.close()

    async def _process_parsing_task(self, task: ScreenplayParsingTask) -> None:
        """Process a screenplay parsing task in the background."""
        try:
            task.status = TaskStatus.PROCESSING
            task.started_at = datetime.now(UTC)
            task.message = "Processing screenplay..."
            task.progress = 0.1

            # Get sanitized name from original filename
            original_name = Path(task.original_filename).stem
            sanitized_name = sanitize_name(original_name)

            # First, copy the file to source_screenplays directory
            if task.temp_file_path is None:
                raise ValueError("Temporary file path is None")
            file_ext = Path(task.temp_file_path).suffix.lower()
            source_screenplay_path = (
                self.source_screenplays_dir / f"{sanitized_name}{file_ext}"
            )
            shutil.copy2(task.temp_file_path, source_screenplay_path)

            task.progress = 0.3
            task.message = "Processing screenplay..."

            # Use the secure process_screenplay function with base_path
            from script_to_speech.parser.process import process_screenplay

            # Set the working directory as the base path for security validation
            base_path = Path.cwd()

            try:
                # Process the screenplay using the secure function
                result = process_screenplay(
                    str(source_screenplay_path),
                    base_path=base_path,
                    text_only=task.text_only,
                )

                # Extract information from the structured result
                task.output_dir = result["output_dir"]

                # Store the analysis if available (not present in text_only mode)
                if result.get("analysis"):
                    analysis = result["analysis"]
                else:
                    analysis = None

            except Exception as e:
                logger.error(f"Error in screenplay processing: {str(e)}")
                logger.error(f"Error type: {type(e).__name__}")
                raise

            task.progress = 0.7

            # Find the most recent log file in the logs directory
            log_file_path = None
            if task.output_dir:
                logs_dir = Path(task.output_dir) / "logs"
                if logs_dir.exists():
                    log_files = sorted(logs_dir.glob("*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
                    if log_files:
                        log_file_path = str(log_files[0])

            # Prepare result using the structured data from process_screenplay
            task.result = {
                "files": result["files"],
                "analysis": analysis,
                "screenplay_name": result["screenplay_name"],
                "original_filename": task.original_filename,
                "text_only": result.get("text_only", False),
                "log_file": log_file_path,
            }

            task.progress = 0.9

            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now(UTC)
            task.message = "Screenplay parsing completed successfully"
            task.progress = 1.0

        except Exception as e:
            logger.error(
                f"Error processing screenplay parsing task {task.task_id}: {str(e)}",
                exc_info=True,
            )
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.message = f"Parsing failed: {str(e)}"
            task.completed_at = datetime.now(UTC)
        finally:
            # Clean up temporary file
            if task.temp_file_path and os.path.exists(task.temp_file_path):
                try:
                    os.unlink(task.temp_file_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temporary file: {e}")

    def get_task_status(self, task_id: str) -> Optional[TaskStatusResponse]:
        """Get the status of a parsing task."""
        with self._lock:
            task = self._tasks.get(task_id)

        if not task:
            return None

        return TaskStatusResponse(
            task_id=task_id,
            status=task.status,
            message=task.message,
            progress=task.progress,
            result=task.result,
            error=task.error,
            created_at=task.created_at.isoformat() if task.created_at else None,
            completed_at=task.completed_at.isoformat() if task.completed_at else None,
        )

    def get_all_tasks(self) -> List[TaskStatusResponse]:
        """Get status of all parsing tasks."""
        with self._lock:
            tasks = list(self._tasks.values())

        return [
            TaskStatusResponse(
                task_id=task.task_id,
                status=task.status,
                message=task.message,
                progress=task.progress,
                result=task.result,
                error=task.error,
                created_at=task.created_at.isoformat() if task.created_at else None,
                completed_at=(
                    task.completed_at.isoformat() if task.completed_at else None
                ),
            )
            for task in tasks
        ]

    def get_parsing_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the parsed result for a completed task.

        Returns the chunks and analysis data if the task is completed.
        """
        with self._lock:
            task = self._tasks.get(task_id)

        if not task or task.status != TaskStatus.COMPLETED or not task.result:
            return None

        result = task.result.copy()

        # Load the actual chunks if task is completed
        if "files" in result and "json" in result["files"] and not task.text_only:
            json_path = Path(result["files"]["json"])
            if json_path.exists():
                with open(json_path, "r", encoding="utf-8") as f:
                    result["chunks"] = json.load(f)

        # Dynamically check for log files if not already present
        if result.get("log_file") is None:
            # Try task.output_dir first
            logs_dir = None
            if task.output_dir:
                logs_dir = Path(task.output_dir) / "logs"
            
            # If task.output_dir doesn't work, try standard output path structure
            if not logs_dir or not logs_dir.exists():
                screenplay_name = result.get("screenplay_name", "unknown")
                potential_output_dir = Path.cwd() / "output" / screenplay_name
                logs_dir = potential_output_dir / "logs"
            
            if logs_dir and logs_dir.exists():
                log_files = sorted(logs_dir.glob("*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
                if log_files:
                    result["log_file"] = str(log_files[0])

        return result

    def get_recent_screenplays(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get list of recently parsed screenplays."""
        with self._lock:
            tasks = list(self._tasks.values())

        # Sort by creation time, most recent first
        tasks.sort(key=lambda t: t.created_at, reverse=True)

        # Filter completed tasks and limit
        recent = []
        for task in tasks[
            : limit * 2
        ]:  # Check more tasks in case some aren't completed
            if task.status == TaskStatus.COMPLETED and task.result:
                recent.append(
                    {
                        "task_id": task.task_id,
                        "filename": task.original_filename,
                        "screenplay_name": task.result.get(
                            "screenplay_name", "Unknown"
                        ),
                        "created_at": task.created_at.isoformat(),
                        "completed_at": (
                            task.completed_at.isoformat() if task.completed_at else None
                        ),
                        "analysis": task.result.get("analysis", {}),
                    }
                )
                if len(recent) >= limit:
                    break

        return recent

    def delete_task(self, task_id: str, delete_files: bool = False) -> bool:
        """Delete a parsing task and optionally its files."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False

            # Delete associated files if requested
            if delete_files and task.output_dir and os.path.exists(task.output_dir):
                try:
                    shutil.rmtree(task.output_dir)
                except Exception as e:
                    logger.warning(f"Failed to delete output directory: {e}")

            # Delete temporary file if it still exists
            if task.temp_file_path and os.path.exists(task.temp_file_path):
                try:
                    os.unlink(task.temp_file_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temporary file: {e}")

            # Remove task from memory
            del self._tasks[task_id]

        return True

    def cleanup_old_tasks(self, max_age_hours: int = 24) -> int:
        """Clean up old completed tasks."""
        cutoff_time = datetime.now(UTC).timestamp() - (max_age_hours * 3600)
        removed_count = 0

        with self._lock:
            task_ids_to_remove = []

            for task_id, task in self._tasks.items():
                if (
                    task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]
                    and task.completed_at
                    and task.completed_at.timestamp() < cutoff_time
                ):
                    task_ids_to_remove.append(task_id)

            # Perform cleanup within the same lock to avoid deadlock
            for task_id in task_ids_to_remove:
                task = self._tasks.get(task_id)
                if task:
                    # Clean up files (same logic as delete_task but without lock)
                    try:
                        # Delete temporary file if it still exists
                        if task.temp_file_path and os.path.exists(task.temp_file_path):
                            try:
                                os.unlink(task.temp_file_path)
                            except Exception as e:
                                logger.warning(f"Failed to delete temporary file: {e}")
                        
                        # Remove task from memory
                        del self._tasks[task_id]
                        removed_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to cleanup task {task_id}: {e}")

        return removed_count


# Create singleton instance
screenplay_service = ScreenplayService()
