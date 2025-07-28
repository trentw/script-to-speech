"""Voice casting API routes."""

import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from ..services.screenplay_service import screenplay_service
from ..services.voice_casting_service import (
    CharacterInfo,
    ExtractCharactersResponse,
    GenerateCharacterNotesPromptResponse,
    GenerateVoiceLibraryPromptResponse,
    GenerateYamlResponse,
    ParseYamlResponse,
    ValidateYamlResponse,
    VoiceAssignment,
    VoiceCastingSession,
    voice_casting_service,
)

router = APIRouter()

# Maximum file size: 50MB
MAX_FILE_SIZE = 50 * 1024 * 1024


class ExtractCharactersRequest(BaseModel):
    """Request to extract characters from screenplay JSON file."""

    screenplay_json_path: str = Field(..., description="Path to screenplay JSON file")


class ValidateYamlRequest(BaseModel):
    """Request to validate YAML against screenplay characters."""

    yaml_content: str = Field(..., description="YAML configuration content")
    screenplay_json_path: str = Field(..., description="Path to screenplay JSON file")


class GenerateYamlRequest(BaseModel):
    """Request to generate YAML from character assignments."""

    assignments: Dict[str, VoiceAssignment]
    character_info: Dict[str, CharacterInfo]
    include_comments: bool = Field(
        default=True, description="Include character stats and notes as comments"
    )


class ParseYamlRequest(BaseModel):
    """Request to parse YAML and extract assignments."""

    yaml_content: str


@router.post("/extract-characters", response_model=ExtractCharactersResponse)
async def extract_characters(
    request: ExtractCharactersRequest,
) -> ExtractCharactersResponse:
    """Extract characters from screenplay JSON file with their statistics."""
    try:
        return await voice_casting_service.extract_characters(
            request.screenplay_json_path
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to extract characters: {str(e)}"
        )


@router.post("/validate-yaml", response_model=ValidateYamlResponse)
async def validate_yaml(request: ValidateYamlRequest) -> ValidateYamlResponse:
    """Validate YAML configuration against screenplay characters."""
    try:
        return await voice_casting_service.validate_yaml(
            request.yaml_content, request.screenplay_json_path
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to validate YAML: {str(e)}"
        )


@router.post("/generate-yaml", response_model=GenerateYamlResponse)
async def generate_yaml(request: GenerateYamlRequest) -> GenerateYamlResponse:
    """Generate YAML configuration from character assignments."""
    try:
        return await voice_casting_service.generate_yaml(
            request.assignments, request.character_info, request.include_comments
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate YAML: {str(e)}"
        )


@router.post("/parse-yaml", response_model=ParseYamlResponse)
async def parse_yaml(request: ParseYamlRequest) -> ParseYamlResponse:
    """Parse YAML configuration and extract voice assignments."""
    try:
        return await voice_casting_service.parse_yaml(request.yaml_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse YAML: {str(e)}")


class GenerateCharacterNotesPromptRequest(BaseModel):
    """Request to generate character notes prompt for LLM."""

    session_id: str = Field(..., description="Voice casting session UUID")
    yaml_content: str = Field(..., description="Current YAML configuration content")
    custom_prompt_path: Optional[str] = Field(
        None, description="Optional custom prompt file path"
    )


class GenerateVoiceLibraryPromptRequest(BaseModel):
    """Request to generate voice library casting prompt for LLM."""

    yaml_content: str = Field(
        ..., description="Voice configuration YAML with character notes"
    )
    providers: List[str] = Field(
        ..., description="List of providers to include in prompt"
    )
    custom_prompt_path: Optional[str] = Field(
        None, description="Optional custom prompt file path"
    )


@router.post(
    "/generate-character-notes-prompt",
    response_model=GenerateCharacterNotesPromptResponse,
)
async def generate_character_notes_prompt(
    request: GenerateCharacterNotesPromptRequest,
) -> GenerateCharacterNotesPromptResponse:
    """Generate character notes prompt for LLM assistance."""
    try:
        return await voice_casting_service.generate_character_notes_prompt(
            request.session_id, request.yaml_content, request.custom_prompt_path
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate character notes prompt: {str(e)}",
        )


@router.post(
    "/generate-voice-library-prompt", response_model=GenerateVoiceLibraryPromptResponse
)
async def generate_voice_library_prompt(
    request: GenerateVoiceLibraryPromptRequest,
) -> GenerateVoiceLibraryPromptResponse:
    """Generate voice library casting prompt for LLM assistance."""
    try:
        return await voice_casting_service.generate_voice_library_prompt(
            request.yaml_content, request.providers, request.custom_prompt_path
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate voice library prompt: {str(e)}"
        )


@router.post("/upload-json", response_model=VoiceCastingSession)
async def upload_json(file: UploadFile = File(...)) -> VoiceCastingSession:
    """
    Upload a screenplay JSON file and create a voice casting session.

    Args:
        file: The uploaded JSON file

    Returns:
        VoiceCastingSession with session details

    Raises:
        HTTPException: If file is invalid or too large
    """
    # Validate file extension
    if not file.filename or not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Only JSON files are allowed")

    # Read file content and check size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File size exceeds maximum allowed size of {MAX_FILE_SIZE / (1024 * 1024)}MB",
        )

    # Validate JSON structure
    try:
        import json  # Keep import here to avoid circular imports

        json_data = json.loads(content)

        # Basic validation - check if it looks like a screenplay JSON
        if not isinstance(json_data, list):
            raise ValueError("Screenplay JSON must be a list of dialogue chunks")

        if json_data and not all(
            isinstance(chunk, dict) and "type" in chunk
            for chunk in json_data[:5]  # Check first 5 items
        ):
            raise ValueError("Invalid screenplay JSON structure")

    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON file: {str(e)}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Create uploads directory if it doesn't exist
    uploads_dir = Path("uploads")
    uploads_dir.mkdir(exist_ok=True)

    # Generate unique filename
    file_id = str(uuid.uuid4())
    file_extension = Path(file.filename or "").suffix
    saved_filename = f"{file_id}{file_extension}"
    file_path = uploads_dir / saved_filename

    # Save file
    try:
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to save uploaded file: {str(e)}"
        )

    # Create voice casting session
    try:
        session = await voice_casting_service.create_session(str(file_path))
        return session
    except Exception as e:
        # Clean up uploaded file on error
        file_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to create voice casting session: {str(e)}"
        )


class CreateSessionFromTaskRequest(BaseModel):
    """Request to create a session from an existing screenplay task."""

    task_id: str = Field(..., description="Screenplay parsing task ID")


@router.post("/create-session-from-task", response_model=VoiceCastingSession)
async def create_session_from_task(
    request: CreateSessionFromTaskRequest,
) -> VoiceCastingSession:
    """
    Create a voice casting session from an existing screenplay parsing task.

    Args:
        request: Contains the task_id of a completed screenplay parsing task

    Returns:
        VoiceCastingSession with session details

    Raises:
        HTTPException: If task not found or doesn't have a result path
    """
    # Get task details using screenplay service
    parsing_result = screenplay_service.get_parsing_result(request.task_id)
    if not parsing_result:
        raise HTTPException(
            status_code=404, detail=f"Task {request.task_id} not found or not completed"
        )

    # Extract JSON file path from the parsing result
    if "files" not in parsing_result or "json" not in parsing_result["files"]:
        raise HTTPException(
            status_code=400,
            detail=f"Task {request.task_id} does not have a JSON result file",
        )

    json_file_path = parsing_result["files"]["json"]

    # Create voice casting session using the task's parsing result
    try:
        session = await voice_casting_service.create_session_from_task(parsing_result)
        return session
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create voice casting session: {str(e)}"
        )


@router.get("/session/{session_id}", response_model=VoiceCastingSession)
async def get_session(session_id: str) -> VoiceCastingSession:
    """
    Retrieve voice casting session details.

    Args:
        session_id: The session UUID

    Returns:
        VoiceCastingSession if found

    Raises:
        HTTPException: If session not found
    """
    session = await voice_casting_service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=404, detail=f"Voice casting session {session_id} not found"
        )

    return session


@router.post(
    "/session/{session_id}/screenplay-source", response_model=VoiceCastingSession
)
async def upload_screenplay_source(
    session_id: str, file: UploadFile = File(...)
) -> VoiceCastingSession:
    """
    Upload an original screenplay file (PDF/TXT) to an existing voice casting session.

    Args:
        session_id: The session UUID
        file: The uploaded screenplay file (PDF or TXT)

    Returns:
        Updated VoiceCastingSession with screenplay source path

    Raises:
        HTTPException: If session not found, file is invalid, or upload fails
    """
    # Check if session exists
    session = await voice_casting_service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=404, detail=f"Voice casting session {session_id} not found"
        )

    # Validate file extension
    if not file.filename or not (
        file.filename.endswith(".pdf") or file.filename.endswith(".txt")
    ):
        raise HTTPException(
            status_code=400, detail="Only PDF and TXT files are allowed"
        )

    # Read file content and check size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File size exceeds maximum allowed size of {MAX_FILE_SIZE / (1024 * 1024)}MB",
        )

    # Validate file content based on type
    if file.filename.endswith(".txt"):
        try:
            # Validate that it's valid UTF-8 text
            content.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=400, detail="TXT file must be valid UTF-8 encoded text"
            )

    # Create uploads directory if it doesn't exist
    uploads_dir = Path("uploads")
    uploads_dir.mkdir(exist_ok=True)

    # Generate unique filename using session ID and timestamp
    file_extension = Path(file.filename).suffix
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    saved_filename = f"screenplay_{session_id}_{timestamp}{file_extension}"
    file_path = uploads_dir / saved_filename

    # Save file
    try:
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to save uploaded file: {str(e)}"
        )

    # Update session with screenplay source path
    try:
        updated_session = await voice_casting_service.update_session_screenplay_source(
            session_id, str(file_path)
        )
        if not updated_session:
            # Clean up uploaded file on error
            file_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=404, detail=f"Voice casting session {session_id} not found"
            )

        return updated_session
    except Exception as e:
        # Clean up uploaded file on error
        file_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to update session: {str(e)}"
        )
