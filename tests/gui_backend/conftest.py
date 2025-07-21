"""Shared fixtures and configuration for GUI backend tests."""

import tempfile
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from script_to_speech.gui_backend.main import app
from script_to_speech.gui_backend.services.screenplay_service import screenplay_service
from script_to_speech.gui_backend.models import TaskStatus, TaskStatusResponse


@pytest.fixture
def client() -> TestClient:
    """Create a TestClient for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_screenplay_service() -> Generator[MagicMock, None, None]:
    """Mock the screenplay service singleton."""
    with patch('script_to_speech.gui_backend.routers.screenplay.screenplay_service') as mock:
        # Set up async methods as AsyncMock by default
        mock.create_parsing_task = AsyncMock()
        yield mock


@pytest.fixture
def mock_process_screenplay() -> Generator[MagicMock, None, None]:
    """Mock the process_screenplay function."""
    with patch('script_to_speech.parser.process.process_screenplay') as mock:
        mock.return_value = {
            "output_dir": "/fake/output/test_screenplay",
            "files": {
                "json": "/fake/output/test_screenplay/test_screenplay.json",
                "text": "/fake/output/test_screenplay/test_screenplay.txt"
            },
            "screenplay_name": "test_screenplay",
            "analysis": {
                "total_chunks": 10,
                "total_characters": 5,
                "estimated_duration": "5 minutes"
            }
        }
        yield mock


@pytest.fixture
def mock_file_system() -> Generator[None, None, None]:
    """Mock file system operations."""
    with patch('pathlib.Path.exists', return_value=True), \
         patch('pathlib.Path.mkdir'), \
         patch('shutil.copy2'), \
         patch('shutil.rmtree'), \
         patch('os.unlink'), \
         patch('tempfile.NamedTemporaryFile') as mock_temp:
        
        # Configure temp file mock
        mock_temp_file = MagicMock()
        mock_temp_file.name = "/tmp/test_upload.pdf"
        mock_temp.__enter__.return_value = mock_temp_file
        mock_temp.return_value = mock_temp_file
        
        yield


@pytest.fixture
def mock_asyncio_create_task() -> Generator[AsyncMock, None, None]:
    """Mock the _process_parsing_task method to prevent unawaited coroutine warnings."""
    with patch('script_to_speech.gui_backend.services.screenplay_service.ScreenplayService._process_parsing_task', new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
def sample_task_id() -> str:
    """Generate a sample task ID."""
    return str(uuid.uuid4())


@pytest.fixture
def sample_upload_file():
    """Create a sample upload file for testing."""
    from io import BytesIO
    from fastapi import UploadFile
    
    content = b"Sample PDF content for testing"
    file_obj = BytesIO(content)
    return UploadFile(filename="test_screenplay.pdf", file=file_obj, size=len(content))


@pytest.fixture
def sample_task_status(sample_task_id: str) -> TaskStatusResponse:
    """Create a sample task status response."""
    return TaskStatusResponse(
        task_id=sample_task_id,
        status=TaskStatus.COMPLETED,
        message="Parsing completed successfully",
        progress=1.0,
        result={
            "files": {
                "json": "/fake/output/test_screenplay/test_screenplay.json",
                "text": "/fake/output/test_screenplay/test_screenplay.txt"
            },
            "analysis": {
                "total_chunks": 10,
                "total_characters": 5,
                "estimated_duration": "5 minutes"
            },
            "screenplay_name": "test_screenplay",
            "original_filename": "test_screenplay.pdf"
        },
        error=None,
        created_at="2023-01-01T12:00:00",
        completed_at="2023-01-01T12:01:00"
    )


@pytest.fixture(autouse=True)
def reset_screenplay_service():
    """Reset the screenplay service state between tests."""
    # Clear any existing tasks
    screenplay_service._tasks.clear()
    yield
    # Clean up after test
    screenplay_service._tasks.clear()