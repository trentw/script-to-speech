"""Tests for GUI backend Pydantic models."""

import uuid
from datetime import datetime

import pytest
from pydantic import ValidationError

from script_to_speech.gui_backend.models import (
    TaskResponse,
    TaskStatus,
    TaskStatusResponse
)


class TestTaskStatus:
    """Tests for TaskStatus enum."""

    def test_task_status_values(self):
        """Test all TaskStatus enum values."""
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.PROCESSING == "processing"
        assert TaskStatus.COMPLETED == "completed"
        assert TaskStatus.FAILED == "failed"

    def test_task_status_comparison(self):
        """Test TaskStatus enum comparison."""
        assert TaskStatus.PENDING != TaskStatus.PROCESSING
        assert TaskStatus.COMPLETED == TaskStatus.COMPLETED


class TestTaskResponse:
    """Tests for TaskResponse model."""

    def test_task_response_valid_data(self):
        """Test creating TaskResponse with valid data."""
        # Arrange
        task_id = str(uuid.uuid4())
        status = TaskStatus.PENDING
        message = "Task created successfully"
        
        # Act
        response = TaskResponse(
            task_id=task_id,
            status=status,
            message=message
        )
        
        # Assert
        assert response.task_id == task_id
        assert response.status == status
        assert response.message == message

    def test_task_response_dict_conversion(self):
        """Test TaskResponse serialization to dict."""
        # Arrange
        task_id = str(uuid.uuid4())
        response = TaskResponse(
            task_id=task_id,
            status=TaskStatus.PROCESSING,
            message="Processing..."
        )
        
        # Act
        response_dict = response.model_dump()
        
        # Assert
        assert response_dict["task_id"] == task_id
        assert response_dict["status"] == TaskStatus.PROCESSING
        assert response_dict["message"] == "Processing..."

    def test_task_response_json_serialization(self):
        """Test TaskResponse JSON serialization."""
        # Arrange
        task_id = str(uuid.uuid4())
        response = TaskResponse(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            message="Completed"
        )
        
        # Act
        json_str = response.model_dump_json()
        
        # Assert
        assert task_id in json_str
        assert "completed" in json_str
        assert "Completed" in json_str

    def test_task_response_invalid_status(self):
        """Test TaskResponse with invalid status."""
        # Arrange
        task_id = str(uuid.uuid4())
        
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            TaskResponse(
                task_id=task_id,
                status="invalid_status",  # Invalid status
                message="Test message"
            )
        
        assert "Input should be" in str(exc_info.value)

    def test_task_response_missing_required_fields(self):
        """Test TaskResponse with missing required fields."""
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            TaskResponse()  # Missing all required fields
        
        errors = exc_info.value.errors()
        required_fields = {error["loc"][0] for error in errors}
        assert "task_id" in required_fields
        assert "status" in required_fields
        assert "message" in required_fields

    def test_task_response_empty_strings(self):
        """Test TaskResponse with empty string values."""
        # Act - TaskResponse allows empty strings
        response = TaskResponse(
            task_id="",  # Empty string allowed
            status=TaskStatus.PENDING,
            message=""  # Empty string allowed
        )
        
        # Assert
        assert response.task_id == ""
        assert response.message == ""


class TestTaskStatusResponse:
    """Tests for TaskStatusResponse model."""

    def test_task_status_response_minimal_valid_data(self):
        """Test creating TaskStatusResponse with minimal required data."""
        # Arrange
        task_id = str(uuid.uuid4())
        
        # Act
        response = TaskStatusResponse(
            task_id=task_id,
            status=TaskStatus.PENDING,
            message="Task created",
            progress=0.0
        )
        
        # Assert
        assert response.task_id == task_id
        assert response.status == TaskStatus.PENDING
        assert response.message == "Task created"
        assert response.progress == 0.0
        assert response.result is None
        assert response.error is None
        assert response.created_at is None
        assert response.completed_at is None

    def test_task_status_response_full_data(self):
        """Test creating TaskStatusResponse with all fields."""
        # Arrange
        task_id = str(uuid.uuid4())
        result = {
            "files": {"json": "/path/to/file.json"},
            "analysis": {"total_chunks": 10}
        }
        created_at = "2023-01-01T12:00:00"
        completed_at = "2023-01-01T12:01:00"
        
        # Act
        response = TaskStatusResponse(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            message="Completed successfully",
            progress=1.0,
            result=result,
            error=None,
            created_at=created_at,
            completed_at=completed_at
        )
        
        # Assert
        assert response.task_id == task_id
        assert response.status == TaskStatus.COMPLETED
        assert response.message == "Completed successfully"
        assert response.progress == 1.0
        assert response.result == result
        assert response.error is None
        assert response.created_at == created_at
        assert response.completed_at == completed_at

    def test_task_status_response_with_error(self):
        """Test TaskStatusResponse with error information."""
        # Arrange
        task_id = str(uuid.uuid4())
        error_message = "File processing failed"
        
        # Act
        response = TaskStatusResponse(
            task_id=task_id,
            status=TaskStatus.FAILED,
            message="Task failed",
            progress=0.5,
            error=error_message
        )
        
        # Assert
        assert response.status == TaskStatus.FAILED
        assert response.error == error_message
        assert response.result is None

    def test_task_status_response_progress_validation(self):
        """Test progress field validation."""
        task_id = str(uuid.uuid4())
        
        # Valid progress values
        for progress in [0.0, 0.5, 1.0]:
            response = TaskStatusResponse(
                task_id=task_id,
                status=TaskStatus.PROCESSING,
                message="Processing",
                progress=progress
            )
            assert response.progress == progress
        
        # Invalid progress values should be rejected (progress has constraints)
        with pytest.raises(ValidationError):
            TaskStatusResponse(
                task_id=task_id,
                status=TaskStatus.PROCESSING,
                message="Processing",
                progress=1.5  # Over 100% - should fail validation
            )

    def test_task_status_response_result_dict_structure(self):
        """Test that result field accepts various dict structures."""
        task_id = str(uuid.uuid4())
        
        # Simple result
        simple_result = {"status": "ok"}
        response = TaskStatusResponse(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            message="Done",
            progress=1.0,
            result=simple_result
        )
        assert response.result == simple_result
        
        # Complex nested result
        complex_result = {
            "files": {
                "json": "/path/to/file.json",
                "text": "/path/to/file.txt"
            },
            "analysis": {
                "total_chunks": 100,
                "characters": ["Alice", "Bob"],
                "metadata": {
                    "duration": "30 minutes",
                    "pages": 50
                }
            }
        }
        response = TaskStatusResponse(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            message="Done",
            progress=1.0,
            result=complex_result
        )
        assert response.result == complex_result

    def test_task_status_response_json_serialization(self):
        """Test JSON serialization of TaskStatusResponse."""
        # Arrange
        task_id = str(uuid.uuid4())
        response = TaskStatusResponse(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            message="Success",
            progress=1.0,
            result={"data": "test"},
            created_at="2023-01-01T12:00:00"
        )
        
        # Act
        json_str = response.model_dump_json()
        
        # Assert
        assert task_id in json_str
        assert "completed" in json_str
        assert "Success" in json_str
        assert "2023-01-01T12:00:00" in json_str

    def test_task_status_response_from_dict(self):
        """Test creating TaskStatusResponse from dictionary."""
        # Arrange
        task_id = str(uuid.uuid4())
        data = {
            "task_id": task_id,
            "status": "processing",
            "message": "In progress",
            "progress": 0.75,
            "result": None,
            "error": None,
            "created_at": "2023-01-01T12:00:00",
            "completed_at": None
        }
        
        # Act
        response = TaskStatusResponse(**data)
        
        # Assert
        assert response.task_id == task_id
        assert response.status == TaskStatus.PROCESSING
        assert response.progress == 0.75

    def test_task_status_response_invalid_datetime_string(self):
        """Test TaskStatusResponse with invalid datetime strings."""
        task_id = str(uuid.uuid4())
        
        # Note: The model expects string datetime, not datetime objects
        # Invalid datetime format should still be accepted as string
        response = TaskStatusResponse(
            task_id=task_id,
            status=TaskStatus.PENDING,
            message="Test",
            progress=0.0,
            created_at="invalid-datetime"
        )
        assert response.created_at == "invalid-datetime"

    def test_task_status_response_none_values(self):
        """Test TaskStatusResponse with None values for optional fields."""
        # Arrange
        task_id = str(uuid.uuid4())
        
        # Act
        response = TaskStatusResponse(
            task_id=task_id,
            status=TaskStatus.PENDING,
            message="Test",
            progress=0.0,
            result=None,
            error=None,
            created_at=None,
            completed_at=None
        )
        
        # Assert
        assert response.result is None
        assert response.error is None
        assert response.created_at is None
        assert response.completed_at is None

    def test_task_status_response_missing_required_fields(self):
        """Test TaskStatusResponse with missing required fields."""
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            TaskStatusResponse()
        
        errors = exc_info.value.errors()
        required_fields = {error["loc"][0] for error in errors}
        assert "task_id" in required_fields
        assert "status" in required_fields
        assert "message" in required_fields
        # progress is optional, so it should not be in required_fields
        assert "progress" not in required_fields

    def test_task_status_response_invalid_types(self):
        """Test TaskStatusResponse with invalid field types."""
        task_id = str(uuid.uuid4())
        
        # Invalid progress type
        with pytest.raises(ValidationError):
            TaskStatusResponse(
                task_id=task_id,
                status=TaskStatus.PENDING,
                message="Test",
                progress="invalid"  # Should be float
            )
        
        # Invalid task_id type
        with pytest.raises(ValidationError):
            TaskStatusResponse(
                task_id=123,  # Should be string
                status=TaskStatus.PENDING,
                message="Test",
                progress=0.0
            )