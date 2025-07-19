"""Pydantic models for API requests and responses."""

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Task status enumeration."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FieldType(str, Enum):
    """Field type enumeration."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"


class ProviderField(BaseModel):
    """Provider field definition."""

    name: str
    type: FieldType
    required: bool
    description: Optional[str] = None
    default: Optional[Any] = None
    options: Optional[List[str]] = None  # For enum-like fields
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None


class ProviderInfo(BaseModel):
    """Provider information."""

    identifier: str
    name: str
    description: Optional[str] = None
    required_fields: List[ProviderField]
    optional_fields: List[ProviderField]
    max_threads: int = 1


class VoiceProperties(BaseModel):
    """Voice properties from voice library."""

    accent: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[float] = Field(None, ge=0.0, le=1.0)
    authority: Optional[float] = Field(None, ge=0.0, le=1.0)
    energy: Optional[float] = Field(None, ge=0.0, le=1.0)
    pace: Optional[float] = Field(None, ge=0.0, le=1.0)
    performative: Optional[float] = Field(None, ge=0.0, le=1.0)
    pitch: Optional[float] = Field(None, ge=0.0, le=1.0)
    quality: Optional[float] = Field(None, ge=0.0, le=1.0)
    range: Optional[float] = Field(None, ge=0.0, le=1.0)


class VoiceDescription(BaseModel):
    """Voice description from voice library."""

    provider_name: Optional[str] = None
    provider_description: Optional[str] = None
    provider_use_cases: Optional[str] = None
    custom_description: Optional[str] = None
    perceived_age: Optional[str] = None


class VoiceTags(BaseModel):
    """Voice tags from voice library."""

    provider_use_cases: Optional[List[str]] = None
    custom_tags: Optional[List[str]] = None
    character_types: Optional[List[str]] = None


class VoiceEntry(BaseModel):
    """Voice library entry."""

    sts_id: str
    provider: str
    config: Dict[str, Any]
    voice_properties: Optional[VoiceProperties] = None
    description: Optional[VoiceDescription] = None
    tags: Optional[VoiceTags] = None
    preview_url: Optional[str] = None


class VoiceDetails(BaseModel):
    """Detailed voice information."""

    sts_id: str
    provider: str
    config: Dict[str, Any]
    voice_properties: Optional[VoiceProperties] = None
    description: Optional[VoiceDescription] = None
    tags: Optional[VoiceTags] = None
    preview_url: Optional[str] = None
    expanded_config: Dict[str, Any]


class GenerationRequest(BaseModel):
    """Audio generation request."""

    provider: str
    config: Dict[str, Any]
    text: str
    sts_id: Optional[str] = None
    variants: int = Field(1, ge=1, le=10)
    output_filename: Optional[str] = None


class TaskResponse(BaseModel):
    """Task creation response."""

    task_id: str
    status: TaskStatus
    message: str


class TaskStatusResponse(BaseModel):
    """Task status response."""

    task_id: str
    status: TaskStatus
    message: str
    progress: Optional[float] = Field(None, ge=0.0, le=1.0)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    audio_urls: Optional[List[str]] = None  # Full HTTP URLs for audio files
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    request: Optional[Dict[str, Any]] = None


class GenerationResult(BaseModel):
    """Audio generation result."""

    files: List[str]
    provider: str
    voice_id: str
    text_preview: str
    duration_ms: Optional[int] = None


class ValidationResult(BaseModel):
    """Configuration validation result."""

    valid: bool
    errors: List[str] = []
    warnings: List[str] = []


class ErrorResponse(BaseModel):
    """Error response."""

    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
