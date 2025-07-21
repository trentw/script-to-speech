"""Tests for screenplay router endpoints."""

import json
from io import BytesIO
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from fastapi.testclient import TestClient

from script_to_speech.gui_backend.models import TaskStatus


class TestScreenplayUpload:
    """Tests for screenplay upload endpoint."""

    def test_upload_valid_pdf_file(self, client: TestClient, mock_screenplay_service, mock_file_system):
        """Test uploading a valid PDF file."""
        # Arrange
        from script_to_speech.gui_backend.models import TaskResponse
        
        expected_response = TaskResponse(
            task_id="test-task-id",
            status=TaskStatus.PENDING,
            message="Parsing task created"
        )
        # Make the mock async
        mock_screenplay_service.create_parsing_task = AsyncMock(return_value=expected_response)
        
        file_content = b"Sample PDF content"
        files = {"file": ("test.pdf", BytesIO(file_content), "application/pdf")}
        data = {"text_only": False}
        
        # Act
        response = client.post("/api/screenplay/parse", files=files, data=data)
        
        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["task_id"] == "test-task-id"
        assert response_data["status"] == TaskStatus.PENDING
        assert response_data["message"] == "Parsing task created"
        
        # Verify service was called
        mock_screenplay_service.create_parsing_task.assert_called_once()

    def test_upload_valid_txt_file(self, client: TestClient, mock_screenplay_service, mock_file_system):
        """Test uploading a valid TXT file."""
        # Arrange
        from script_to_speech.gui_backend.models import TaskResponse
        
        expected_response = TaskResponse(
            task_id="test-task-id-txt",
            status=TaskStatus.PENDING,
            message="Parsing task created"
        )
        
        # Make the mock async
        mock_screenplay_service.create_parsing_task = AsyncMock(return_value=expected_response)
        
        file_content = b"Sample screenplay text"
        files = {"file": ("test.txt", BytesIO(file_content), "text/plain")}
        data = {"text_only": False}
        
        # Act
        response = client.post("/api/screenplay/parse", files=files, data=data)
        
        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["task_id"] == "test-task-id-txt"

    def test_upload_invalid_file_type(self, client: TestClient):
        """Test uploading an invalid file type."""
        # Arrange
        file_content = b"Some content"
        files = {"file": ("test.jpg", BytesIO(file_content), "image/jpeg")}
        data = {"text_only": False}
        
        # Act
        response = client.post("/api/screenplay/parse", files=files, data=data)
        
        # Assert
        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]

    def test_upload_oversized_file(self, client: TestClient):
        """Test uploading a file that exceeds size limit."""
        # Arrange - Create a large file (simulate 51MB)
        large_content = b"x" * (51 * 1024 * 1024)
        files = {"file": ("large.pdf", BytesIO(large_content), "application/pdf")}
        data = {"text_only": False}
        
        # Act
        response = client.post("/api/screenplay/parse", files=files, data=data)
        
        # Assert
        assert response.status_code == 413
        assert "File too large" in response.json()["detail"]

    def test_upload_with_text_only_flag(self, client: TestClient, mock_screenplay_service, mock_file_system):
        """Test uploading with text_only flag set to true."""
        # Arrange
        from script_to_speech.gui_backend.models import TaskResponse
        
        expected_response = TaskResponse(
            task_id="text-only-task",
            status=TaskStatus.PENDING,
            message="Parsing task created"
        )
        
        # Make the mock async
        mock_screenplay_service.create_parsing_task = AsyncMock(return_value=expected_response)
        
        file_content = b"Sample PDF content"
        files = {"file": ("test.pdf", BytesIO(file_content), "application/pdf")}
        data = {"text_only": True}
        
        # Act
        response = client.post("/api/screenplay/parse", files=files, data=data)
        
        # Assert
        assert response.status_code == 200
        # Note: with our mock function, we'd need to capture arguments if needed for verification
        # For now, we're just testing that the endpoint works with text_only=True

    def test_upload_service_error(self, client: TestClient, mock_screenplay_service, mock_file_system):
        """Test handling of service errors during upload."""
        # Arrange
        mock_screenplay_service.create_parsing_task.side_effect = Exception("Service error")
        
        file_content = b"Sample PDF content"
        files = {"file": ("test.pdf", BytesIO(file_content), "application/pdf")}
        data = {"text_only": False}
        
        # Act
        response = client.post("/api/screenplay/parse", files=files, data=data)
        
        # Assert
        assert response.status_code == 500
        assert "Failed to create parsing task" in response.json()["detail"]


class TestScreenplayTasks:
    """Tests for screenplay task management endpoints."""

    def test_get_all_tasks(self, client: TestClient, mock_screenplay_service, sample_task_status):
        """Test getting all parsing tasks."""
        # Arrange
        mock_screenplay_service.get_all_tasks.return_value = [sample_task_status]
        
        # Act
        response = client.get("/api/screenplay/tasks")
        
        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data) == 1
        assert response_data[0]["task_id"] == sample_task_status.task_id
        assert response_data[0]["status"] == sample_task_status.status

    def test_get_all_tasks_empty(self, client: TestClient, mock_screenplay_service):
        """Test getting all tasks when no tasks exist."""
        # Arrange
        mock_screenplay_service.get_all_tasks.return_value = []
        
        # Act
        response = client.get("/api/screenplay/tasks")
        
        # Assert
        assert response.status_code == 200
        assert response.json() == []

    def test_get_task_status_existing(self, client: TestClient, mock_screenplay_service, sample_task_status):
        """Test getting status of an existing task."""
        # Arrange
        task_id = sample_task_status.task_id
        mock_screenplay_service.get_task_status.return_value = sample_task_status
        
        # Act
        response = client.get(f"/api/screenplay/status/{task_id}")
        
        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["task_id"] == task_id
        assert response_data["status"] == sample_task_status.status

    def test_get_task_status_not_found(self, client: TestClient, mock_screenplay_service):
        """Test getting status of a non-existent task."""
        # Arrange
        task_id = "non-existent-task-id"
        mock_screenplay_service.get_task_status.return_value = None
        
        # Act
        response = client.get(f"/api/screenplay/status/{task_id}")
        
        # Assert
        assert response.status_code == 404
        assert f"Task {task_id} not found" in response.json()["detail"]

    def test_get_task_status_service_error(self, client: TestClient, mock_screenplay_service):
        """Test handling of service errors when getting task status."""
        # Arrange
        task_id = "error-task-id"
        mock_screenplay_service.get_task_status.side_effect = Exception("Database error")
        
        # Act
        response = client.get(f"/api/screenplay/status/{task_id}")
        
        # Assert
        assert response.status_code == 500
        assert "Failed to get task status" in response.json()["detail"]


class TestScreenplayResults:
    """Tests for screenplay result retrieval endpoints."""

    def test_get_parsing_result_success(self, client: TestClient, mock_screenplay_service):
        """Test getting parsing result for a completed task."""
        # Arrange
        task_id = "completed-task-id"
        expected_result = {
            "chunks": [{"speaker": "JOHN", "text": "Hello world"}],
            "analysis": {"total_chunks": 1, "total_characters": 1},
            "files": {
                "json": "/fake/output/test/test.json",
                "text": "/fake/output/test/test.txt"
            },
            "screenplay_name": "test_screenplay"
        }
        mock_screenplay_service.get_parsing_result.return_value = expected_result
        
        # Act
        response = client.get(f"/api/screenplay/result/{task_id}")
        
        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert response_data == expected_result

    def test_get_parsing_result_not_found(self, client: TestClient, mock_screenplay_service):
        """Test getting parsing result for non-existent or incomplete task."""
        # Arrange
        task_id = "non-existent-task-id"
        mock_screenplay_service.get_parsing_result.return_value = None
        
        # Act
        response = client.get(f"/api/screenplay/result/{task_id}")
        
        # Assert
        assert response.status_code == 404
        assert f"Task {task_id} not found or not completed" in response.json()["detail"]


class TestScreenplayRecent:
    """Tests for recent screenplays endpoint."""

    def test_get_recent_screenplays(self, client: TestClient, mock_screenplay_service):
        """Test getting recent screenplays."""
        # Arrange
        expected_recent = [
            {
                "task_id": "task1",
                "filename": "screenplay1.pdf",
                "screenplay_name": "Screenplay 1",
                "created_at": "2023-01-01T12:00:00",
                "completed_at": "2023-01-01T12:01:00"
            }
        ]
        mock_screenplay_service.get_recent_screenplays.return_value = expected_recent
        
        # Act
        response = client.get("/api/screenplay/recent")
        
        # Assert
        assert response.status_code == 200
        assert response.json() == expected_recent

    def test_get_recent_screenplays_with_limit(self, client: TestClient, mock_screenplay_service):
        """Test getting recent screenplays with custom limit."""
        # Arrange
        limit = 5
        mock_screenplay_service.get_recent_screenplays.return_value = []
        
        # Act
        response = client.get(f"/api/screenplay/recent?limit={limit}")
        
        # Assert
        assert response.status_code == 200
        # Verify limit was passed to service
        mock_screenplay_service.get_recent_screenplays.assert_called_once_with(limit)


class TestScreenplayTaskDeletion:
    """Tests for task deletion endpoints."""

    def test_delete_task_success(self, client: TestClient, mock_screenplay_service):
        """Test successful task deletion."""
        # Arrange
        task_id = "task-to-delete"
        mock_screenplay_service.delete_task.return_value = True
        
        # Act
        response = client.delete(f"/api/screenplay/{task_id}")
        
        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["message"] == f"Task {task_id} deleted successfully"
        mock_screenplay_service.delete_task.assert_called_once_with(task_id, False)

    def test_delete_task_with_files(self, client: TestClient, mock_screenplay_service):
        """Test task deletion with files."""
        # Arrange
        task_id = "task-to-delete"
        mock_screenplay_service.delete_task.return_value = True
        
        # Act
        response = client.delete(f"/api/screenplay/{task_id}?delete_files=true")
        
        # Assert
        assert response.status_code == 200
        mock_screenplay_service.delete_task.assert_called_once_with(task_id, True)

    def test_delete_task_not_found(self, client: TestClient, mock_screenplay_service):
        """Test deleting a non-existent task."""
        # Arrange
        task_id = "non-existent-task"
        mock_screenplay_service.delete_task.return_value = False
        
        # Act
        response = client.delete(f"/api/screenplay/{task_id}")
        
        # Assert
        assert response.status_code == 404
        assert f"Task {task_id} not found" in response.json()["detail"]


class TestScreenplayCleanup:
    """Tests for task cleanup endpoints."""

    def test_cleanup_old_tasks(self, client: TestClient, mock_screenplay_service):
        """Test cleaning up old tasks."""
        # Arrange
        removed_count = 3
        mock_screenplay_service.cleanup_old_tasks.return_value = removed_count
        
        # Act
        response = client.delete("/api/screenplay/cleanup")
        
        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["message"] == f"Cleaned up {removed_count} old parsing tasks"
        mock_screenplay_service.cleanup_old_tasks.assert_called_once_with(24)

    def test_cleanup_old_tasks_custom_age(self, client: TestClient, mock_screenplay_service):
        """Test cleaning up old tasks with custom max age."""
        # Arrange
        max_age_hours = 48
        mock_screenplay_service.cleanup_old_tasks.return_value = 1
        
        # Act
        response = client.delete(f"/api/screenplay/cleanup?max_age_hours={max_age_hours}")
        
        # Assert
        assert response.status_code == 200
        mock_screenplay_service.cleanup_old_tasks.assert_called_once_with(max_age_hours)


class TestScreenplayDownload:
    """Tests for file download endpoints."""

    def test_download_json_file(self, client: TestClient, mock_screenplay_service, mock_file_system):
        """Test downloading JSON file."""
        # Arrange
        task_id = "completed-task"
        mock_result = {
            "files": {"json": "/fake/path/screenplay.json"},
            "screenplay_name": "test_screenplay"
        }
        mock_screenplay_service.get_parsing_result.return_value = mock_result
        
        # Mock the FileResponse to avoid file system access
        with patch('script_to_speech.gui_backend.routers.screenplay.FileResponse') as mock_file_response:
            from fastapi.responses import JSONResponse
            # Return a simple JSON response to test the logic without file operations
            mock_file_response.return_value = JSONResponse(
                content={"message": "file download"},
                headers={"content-disposition": 'attachment; filename="test_screenplay.json"'}
            )
            
            # Act
            response = client.get(f"/api/screenplay/download/{task_id}/json")
            
            # Assert
            assert response.status_code == 200
            assert response.headers["content-disposition"] == 'attachment; filename="test_screenplay.json"'
            # Verify FileResponse was called with correct parameters
            mock_file_response.assert_called_once_with(
                path="/fake/path/screenplay.json",
                filename="test_screenplay.json",
                media_type='application/octet-stream'
            )

    def test_download_text_file(self, client: TestClient, mock_screenplay_service, mock_file_system):
        """Test downloading text file."""
        # Arrange
        task_id = "completed-task"
        mock_result = {
            "files": {"text": "/fake/path/screenplay.txt"},
            "screenplay_name": "test_screenplay"
        }
        mock_screenplay_service.get_parsing_result.return_value = mock_result
        
        # Mock the FileResponse to avoid file system access
        with patch('script_to_speech.gui_backend.routers.screenplay.FileResponse') as mock_file_response:
            from fastapi.responses import JSONResponse
            # Return a simple JSON response to test the logic without file operations
            mock_file_response.return_value = JSONResponse(
                content={"message": "file download"},
                headers={"content-disposition": 'attachment; filename="test_screenplay.txt"'}
            )
            
            # Act
            response = client.get(f"/api/screenplay/download/{task_id}/text")
            
            # Assert
            assert response.status_code == 200
            assert response.headers["content-disposition"] == 'attachment; filename="test_screenplay.txt"'
            # Verify FileResponse was called with correct parameters
            mock_file_response.assert_called_once_with(
                path="/fake/path/screenplay.txt",
                filename="test_screenplay.txt",
                media_type='application/octet-stream'
            )

    def test_download_file_task_not_found(self, client: TestClient, mock_screenplay_service):
        """Test downloading file for non-existent task."""
        # Arrange
        task_id = "non-existent-task"
        mock_screenplay_service.get_parsing_result.return_value = None
        
        # Act
        response = client.get(f"/api/screenplay/download/{task_id}/json")
        
        # Assert
        assert response.status_code == 404
        assert f"Task {task_id} not found or not completed" in response.json()["detail"]

    def test_download_invalid_file_type(self, client: TestClient, mock_screenplay_service):
        """Test downloading with invalid file type."""
        # Arrange
        task_id = "completed-task"
        mock_result = {
            "files": {"json": "/fake/path/screenplay.json"},
            "screenplay_name": "test_screenplay"
        }
        mock_screenplay_service.get_parsing_result.return_value = mock_result
        
        # Act
        response = client.get(f"/api/screenplay/download/{task_id}/invalid")
        
        # Assert
        assert response.status_code == 404
        assert "File type 'invalid' not found" in response.json()["detail"]

    @patch('pathlib.Path.exists', return_value=False)
    def test_download_file_not_exists(self, mock_exists, client: TestClient, mock_screenplay_service):
        """Test downloading when file doesn't exist on disk."""
        # Arrange
        task_id = "completed-task"
        mock_result = {
            "files": {"json": "/fake/path/screenplay.json"},
            "screenplay_name": "test_screenplay"
        }
        mock_screenplay_service.get_parsing_result.return_value = mock_result
        
        # Act
        response = client.get(f"/api/screenplay/download/{task_id}/json")
        
        # Assert
        assert response.status_code == 404
        assert "File not found" in response.json()["detail"]