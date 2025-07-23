"""Tests for screenplay service layer."""

import json
import tempfile
import uuid
from datetime import datetime
from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import UploadFile

from script_to_speech.gui_backend.models import TaskStatus
from script_to_speech.gui_backend.services.screenplay_service import (
    ScreenplayParsingTask,
    ScreenplayService,
)


class TestScreenplayParsingTask:
    """Tests for ScreenplayParsingTask model."""

    def test_task_creation(self):
        """Test creating a new parsing task."""
        # Arrange
        task_id = str(uuid.uuid4())
        filename = "test.pdf"

        # Act
        task = ScreenplayParsingTask(task_id, filename)

        # Assert
        assert task.task_id == task_id
        assert task.filename == filename
        assert task.original_filename == filename
        assert task.text_only is False
        assert task.status == TaskStatus.PENDING
        assert task.progress == 0.0
        assert task.message == "Task created"
        assert task.result is None
        assert task.error is None
        assert task.temp_file_path is None
        assert task.output_dir is None
        assert isinstance(task.created_at, datetime)

    def test_task_creation_with_text_only(self):
        """Test creating a task with text_only flag."""
        # Arrange
        task_id = str(uuid.uuid4())
        filename = "test.pdf"

        # Act
        task = ScreenplayParsingTask(task_id, filename, text_only=True)

        # Assert
        assert task.text_only is True


class TestScreenplayService:
    """Tests for ScreenplayService class."""

    @pytest.fixture
    def service(self, mock_file_system):
        """Create a fresh ScreenplayService instance."""
        return ScreenplayService()

    @pytest.fixture
    def mock_upload_file(self):
        """Create a mock UploadFile for testing."""
        content = b"Sample screenplay content"
        file_obj = BytesIO(content)
        upload_file = UploadFile(filename="test.pdf", file=file_obj, size=len(content))
        return upload_file

    @pytest.mark.asyncio
    async def test_create_parsing_task_success(
        self, service, mock_upload_file, mock_file_system, mock_asyncio_create_task
    ):
        """Test successful creation of a parsing task."""
        # Act
        response = await service.create_parsing_task(mock_upload_file, text_only=False)

        # Assert
        assert response.status == TaskStatus.PENDING
        assert response.message == "Parsing task created"
        assert response.task_id is not None

        # Verify task was stored
        assert response.task_id in service._tasks
        task = service._tasks[response.task_id]
        assert task.filename == "test.pdf"
        assert task.text_only is False

    @pytest.mark.asyncio
    async def test_create_parsing_task_with_text_only(
        self, service, mock_upload_file, mock_file_system, mock_asyncio_create_task
    ):
        """Test creating a parsing task with text_only flag."""
        # Act
        response = await service.create_parsing_task(mock_upload_file, text_only=True)

        # Assert
        assert response.status == TaskStatus.PENDING
        task = service._tasks[response.task_id]
        assert task.text_only is True

    @pytest.mark.asyncio
    async def test_create_parsing_task_file_write_error(
        self, service, mock_upload_file, mock_asyncio_create_task
    ):
        """Test handling of file write errors during task creation."""
        # Arrange
        with patch("tempfile.NamedTemporaryFile") as mock_temp:
            mock_temp.side_effect = OSError("Disk full")

            # Act & Assert
            with pytest.raises(OSError, match="Disk full"):
                await service.create_parsing_task(mock_upload_file)

    def test_get_task_status_existing(self, service):
        """Test getting status of an existing task."""
        # Arrange
        task_id = str(uuid.uuid4())
        task = ScreenplayParsingTask(task_id, "test.pdf")
        service._tasks[task_id] = task

        # Act
        status = service.get_task_status(task_id)

        # Assert
        assert status is not None
        assert status.task_id == task_id
        assert status.status == TaskStatus.PENDING
        assert status.message == "Task created"
        assert status.progress == 0.0

    def test_get_task_status_not_found(self, service):
        """Test getting status of a non-existent task."""
        # Arrange
        task_id = "non-existent-task"

        # Act
        status = service.get_task_status(task_id)

        # Assert
        assert status is None

    def test_get_all_tasks(self, service):
        """Test getting all tasks."""
        # Arrange
        task1_id = str(uuid.uuid4())
        task2_id = str(uuid.uuid4())
        task1 = ScreenplayParsingTask(task1_id, "test1.pdf")
        task2 = ScreenplayParsingTask(task2_id, "test2.pdf")
        service._tasks[task1_id] = task1
        service._tasks[task2_id] = task2

        # Act
        all_tasks = service.get_all_tasks()

        # Assert
        assert len(all_tasks) == 2
        task_ids = [task.task_id for task in all_tasks]
        assert task1_id in task_ids
        assert task2_id in task_ids

    def test_get_all_tasks_empty(self, service):
        """Test getting all tasks when no tasks exist."""
        # Act
        all_tasks = service.get_all_tasks()

        # Assert
        assert all_tasks == []

    def test_get_parsing_result_completed_task(self, service, mock_file_system):
        """Test getting parsing result for a completed task."""
        # Arrange
        task_id = str(uuid.uuid4())
        task = ScreenplayParsingTask(task_id, "test.pdf")
        task.status = TaskStatus.COMPLETED
        task.result = {
            "files": {"json": "/fake/path/test.json"},
            "screenplay_name": "test",
            "analysis": {"total_chunks": 5},
        }
        service._tasks[task_id] = task

        # Mock file reading
        mock_chunks = [{"speaker": "JOHN", "text": "Hello world"}]
        with patch("builtins.open", mock_open_json(mock_chunks)):
            # Act
            result = service.get_parsing_result(task_id)

        # Assert
        assert result is not None
        assert "chunks" in result
        assert result["chunks"] == mock_chunks
        assert result["screenplay_name"] == "test"

    def test_get_parsing_result_not_completed(self, service):
        """Test getting parsing result for a task that's not completed."""
        # Arrange
        task_id = str(uuid.uuid4())
        task = ScreenplayParsingTask(task_id, "test.pdf")
        task.status = TaskStatus.PROCESSING
        service._tasks[task_id] = task

        # Act
        result = service.get_parsing_result(task_id)

        # Assert
        assert result is None

    def test_get_parsing_result_not_found(self, service):
        """Test getting parsing result for non-existent task."""
        # Act
        result = service.get_parsing_result("non-existent-task")

        # Assert
        assert result is None

    def test_get_recent_screenplays(self, service):
        """Test getting recent screenplays."""
        # Arrange
        task1_id = str(uuid.uuid4())
        task2_id = str(uuid.uuid4())

        # Create completed tasks
        task1 = ScreenplayParsingTask(task1_id, "old.pdf")
        task1.status = TaskStatus.COMPLETED
        task1.created_at = datetime(2023, 1, 1, 10, 0, 0)
        task1.completed_at = datetime(2023, 1, 1, 10, 1, 0)
        task1.result = {"screenplay_name": "old_screenplay", "analysis": {}}

        task2 = ScreenplayParsingTask(task2_id, "new.pdf")
        task2.status = TaskStatus.COMPLETED
        task2.created_at = datetime(2023, 1, 1, 11, 0, 0)
        task2.completed_at = datetime(2023, 1, 1, 11, 1, 0)
        task2.result = {"screenplay_name": "new_screenplay", "analysis": {}}

        service._tasks[task1_id] = task1
        service._tasks[task2_id] = task2

        # Act
        recent = service.get_recent_screenplays(limit=2)

        # Assert
        assert len(recent) == 2
        # Should be ordered by creation time, most recent first
        assert recent[0]["screenplay_name"] == "new_screenplay"
        assert recent[1]["screenplay_name"] == "old_screenplay"

    def test_get_recent_screenplays_with_limit(self, service):
        """Test getting recent screenplays with a limit."""
        # Arrange - Create 3 tasks but request only 1
        for i in range(3):
            task_id = str(uuid.uuid4())
            task = ScreenplayParsingTask(task_id, f"test{i}.pdf")
            task.status = TaskStatus.COMPLETED
            task.created_at = datetime(2023, 1, 1, 10, i, 0)
            task.completed_at = datetime(2023, 1, 1, 10, i, 1)
            task.result = {"screenplay_name": f"screenplay{i}", "analysis": {}}
            service._tasks[task_id] = task

        # Act
        recent = service.get_recent_screenplays(limit=1)

        # Assert
        assert len(recent) == 1

    def test_get_recent_screenplays_only_completed(self, service):
        """Test that get_recent_screenplays only returns completed tasks."""
        # Arrange
        completed_task_id = str(uuid.uuid4())
        pending_task_id = str(uuid.uuid4())

        completed_task = ScreenplayParsingTask(completed_task_id, "completed.pdf")
        completed_task.status = TaskStatus.COMPLETED
        completed_task.result = {"screenplay_name": "completed", "analysis": {}}

        pending_task = ScreenplayParsingTask(pending_task_id, "pending.pdf")
        pending_task.status = TaskStatus.PENDING

        service._tasks[completed_task_id] = completed_task
        service._tasks[pending_task_id] = pending_task

        # Act
        recent = service.get_recent_screenplays()

        # Assert
        assert len(recent) == 1
        assert recent[0]["screenplay_name"] == "completed"

    def test_delete_task_success(self, service, mock_file_system):
        """Test successful task deletion."""
        # Arrange
        task_id = str(uuid.uuid4())
        task = ScreenplayParsingTask(task_id, "test.pdf")
        task.output_dir = "/fake/output/dir"
        task.temp_file_path = "/fake/temp/file.pdf"
        service._tasks[task_id] = task

        # Act
        result = service.delete_task(task_id, delete_files=False)

        # Assert
        assert result is True
        assert task_id not in service._tasks

    def test_delete_task_with_files(self, service, mock_file_system):
        """Test task deletion with file cleanup."""
        # Arrange
        task_id = str(uuid.uuid4())
        task = ScreenplayParsingTask(task_id, "test.pdf")
        task.output_dir = "/fake/output/dir"
        service._tasks[task_id] = task

        with (
            patch("shutil.rmtree") as mock_rmtree,
            patch("os.path.exists", return_value=True),
        ):

            # Act
            result = service.delete_task(task_id, delete_files=True)

            # Assert
            assert result is True
            mock_rmtree.assert_called_once_with("/fake/output/dir")

    def test_delete_task_not_found(self, service):
        """Test deleting a non-existent task."""
        # Act
        result = service.delete_task("non-existent-task")

        # Assert
        assert result is False

    def test_cleanup_old_tasks(self, service):
        """Test cleaning up old tasks."""
        # Arrange
        old_task_id = str(uuid.uuid4())
        recent_task_id = str(uuid.uuid4())

        # Create old completed task
        old_task = ScreenplayParsingTask(old_task_id, "old.pdf")
        old_task.status = TaskStatus.COMPLETED
        old_task.completed_at = datetime(2022, 1, 1, 10, 0, 0)  # Very old

        # Create recent completed task
        recent_task = ScreenplayParsingTask(recent_task_id, "recent.pdf")
        recent_task.status = TaskStatus.COMPLETED
        recent_task.completed_at = datetime.now()  # Recent

        service._tasks[old_task_id] = old_task
        service._tasks[recent_task_id] = recent_task

        # Act
        removed_count = service.cleanup_old_tasks(max_age_hours=24)

        # Assert
        assert removed_count == 1
        assert old_task_id not in service._tasks
        assert recent_task_id in service._tasks

    def test_cleanup_old_tasks_no_completed_tasks(self, service):
        """Test cleanup when there are no completed tasks."""
        # Arrange
        task_id = str(uuid.uuid4())
        task = ScreenplayParsingTask(task_id, "pending.pdf")
        task.status = TaskStatus.PENDING
        service._tasks[task_id] = task

        # Act
        removed_count = service.cleanup_old_tasks(max_age_hours=24)

        # Assert
        assert removed_count == 0
        assert task_id in service._tasks


class TestProcessingTask:
    """Tests for background processing functionality."""

    @pytest.fixture
    def service(self, mock_file_system):
        """Create a fresh ScreenplayService instance."""
        return ScreenplayService()

    @pytest.mark.asyncio
    async def test_process_parsing_task_success(self, service, mock_process_screenplay):
        """Test successful background processing of a parsing task."""
        # Arrange
        task_id = str(uuid.uuid4())
        task = ScreenplayParsingTask(task_id, "test.pdf")
        task.temp_file_path = "/fake/temp/file.pdf"
        service._tasks[task_id] = task

        # Act
        await service._process_parsing_task(task)

        # Assert
        assert task.status == TaskStatus.COMPLETED
        assert task.progress == 1.0
        assert task.message == "Screenplay parsing completed successfully"
        assert task.result is not None
        assert task.completed_at is not None
        mock_process_screenplay.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_parsing_task_failure(self, service):
        """Test handling of processing failures."""
        # Arrange
        task_id = str(uuid.uuid4())
        task = ScreenplayParsingTask(task_id, "test.pdf")
        task.temp_file_path = "/fake/temp/file.pdf"
        service._tasks[task_id] = task

        with patch(
            "script_to_speech.parser.process.process_screenplay"
        ) as mock_process:
            mock_process.side_effect = Exception("Processing failed")

            # Act
            await service._process_parsing_task(task)

        # Assert
        assert task.status == TaskStatus.FAILED
        assert task.error == "Processing failed"
        assert "Parsing failed" in task.message
        assert task.completed_at is not None

    @pytest.mark.asyncio
    async def test_process_parsing_task_sanitizes_filename(
        self, service, mock_process_screenplay
    ):
        """Test that filenames are properly sanitized during processing."""
        # Arrange
        task_id = str(uuid.uuid4())
        task = ScreenplayParsingTask(task_id, "My Script!@#$%^&*().pdf")
        task.temp_file_path = "/fake/temp/file.pdf"
        service._tasks[task_id] = task

        with patch(
            "script_to_speech.gui_backend.services.screenplay_service.sanitize_name"
        ) as mock_sanitize:
            mock_sanitize.return_value = "My_Script"

            # Act
            await service._process_parsing_task(task)

        # Assert
        mock_sanitize.assert_called_once_with("My Script!@#$%^&*()")

    @pytest.mark.asyncio
    async def test_process_parsing_task_cleans_temp_file(
        self, service, mock_process_screenplay
    ):
        """Test that temporary files are cleaned up after processing."""
        # Arrange
        task_id = str(uuid.uuid4())
        task = ScreenplayParsingTask(task_id, "test.pdf")
        task.temp_file_path = "/fake/temp/file.pdf"
        service._tasks[task_id] = task

        with (
            patch("os.path.exists", return_value=True),
            patch("os.unlink") as mock_unlink,
        ):

            # Act
            await service._process_parsing_task(task)

        # Assert
        mock_unlink.assert_called_once_with("/fake/temp/file.pdf")


def mock_open_json(data):
    """Helper to mock opening JSON files."""
    from unittest.mock import mock_open

    return mock_open(read_data=json.dumps(data))
