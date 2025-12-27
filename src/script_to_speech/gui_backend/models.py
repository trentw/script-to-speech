"""Pydantic models for API requests and responses."""

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


def to_camel(string: str) -> str:
    """Convert snake_case to camelCase for frontend compatibility."""
    components = string.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


class CamelModel(BaseModel):
    """Base model that serializes to camelCase for frontend compatibility.

    Use this for models that are returned to the frontend API.
    Python code uses snake_case internally, but JSON responses use camelCase.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Accept both snake_case and camelCase input
    )


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


# Project Mode Models


class ApiResponse(BaseModel):
    """Standard API response envelope."""

    ok: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class ProjectMeta(BaseModel):
    """Project metadata for discovered projects."""

    name: str
    input_path: str
    output_path: str
    has_json: bool
    has_voice_config: bool
    last_modified: str


class ProjectStatus(BaseModel):
    """Detailed project status with file existence and parse errors."""

    # File existence checks
    has_pdf: bool
    has_json: bool
    has_voice_config: bool
    has_optional_config: bool
    has_output_mp3: bool

    # Derived states
    screenplay_parsed: bool
    voices_cast: bool
    audio_generated: bool

    # Metadata (if files exist)
    speaker_count: Optional[int] = None
    dialogue_chunks: Optional[int] = None
    voices_assigned: Optional[int] = None

    # Error states for corrupt files
    json_error: Optional[str] = None
    voice_config_error: Optional[str] = None


# Additional models for project creation API


class ProjectDiscovery(BaseModel):
    """Discovered project information."""

    name: str
    inputPath: str
    outputPath: str
    hasJson: bool = False
    hasVoiceConfig: bool = False
    lastModified: Optional[str] = None


class NewProjectRequest(BaseModel):
    """Request to create a new project."""

    sourceFile: str  # Path to uploaded temporary file
    originalFilename: Optional[str] = None  # Original filename from upload


class NewProjectResponse(BaseModel):
    """Response from creating a new project."""

    inputPath: str
    outputPath: str
    screenplayName: str


# Audiobook Generation Models


class AudiobookGenerationMode(str, Enum):
    """Audio generation run modes matching CLI options."""

    DRY_RUN = "dry-run"  # Plan only, no generation
    POPULATE_CACHE = "populate-cache"  # Generate clips, skip concatenation
    FULL = "full"  # Full generation with final MP3


class AudiobookGenerationPhase(str, Enum):
    """Phases of the audio generation pipeline."""

    PENDING = "pending"
    PLANNING = "planning"
    APPLYING_OVERRIDES = "applying_overrides"
    CHECKING_SILENCE = "checking_silence"
    GENERATING = "generating"
    CONCATENATING = "concatenating"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"


class AudiobookGenerationRequest(BaseModel):
    """Request to start audiobook generation."""

    project_name: str  # Name of the project
    input_json_path: str  # Path to parsed screenplay JSON
    voice_config_path: str  # Path to voice config YAML
    mode: AudiobookGenerationMode = AudiobookGenerationMode.FULL

    # Optional features
    silence_threshold: Optional[float] = -40.0  # dBFS, None to disable
    cache_overrides_dir: Optional[str] = None  # Path to override audio files
    text_processor_configs: Optional[List[str]] = None

    # Generation settings
    gap_ms: int = 500  # Gap between clips in ms
    max_workers: int = 12  # Concurrent download threads


class RateLimitedProvider(CamelModel):
    """Information about a rate-limited provider."""

    provider: str
    backoff_until: Optional[str] = None


class AudiobookGenerationStats(CamelModel):
    """Statistics from the generation process."""

    total_clips: int = 0
    cached_clips: int = 0
    generated_clips: int = 0
    failed_clips: int = 0
    skipped_duplicate_clips: int = 0
    silent_clips: int = 0
    rate_limited_clips: int = 0

    # Detailed status counts (from TaskStatus enum)
    by_status: Optional[Dict[str, int]] = None

    # Rate limit info
    rate_limited_providers: Optional[List[RateLimitedProvider]] = None


class AudiobookGenerationProgress(CamelModel):
    """Current progress of an audiobook generation task."""

    task_id: str
    status: TaskStatus  # Overall task status
    phase: AudiobookGenerationPhase
    phase_progress: float = Field(0.0, ge=0.0, le=1.0)  # 0.0-1.0 within current phase
    overall_progress: float = Field(0.0, ge=0.0, le=1.0)  # 0.0-1.0 across all phases
    message: str = ""

    # Statistics (populated during/after GENERATING phase)
    stats: Optional[AudiobookGenerationStats] = None

    # Timing
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    # Error info
    error: Optional[str] = None


class AudiobookTaskResponse(CamelModel):
    """Response from creating an audiobook generation task."""

    task_id: str
    status: str
    message: str


class AudiobookGenerationResult(CamelModel):
    """Final result of a completed audiobook generation."""

    output_file: Optional[str] = None  # Path to final MP3 (if full mode)
    cache_folder: str  # Path to cache folder
    log_file: Optional[str] = None  # Path to generation log

    # Final statistics
    stats: AudiobookGenerationStats

    # Issues detected (for dry-run or review)
    cache_misses: List[Dict[str, Any]] = []  # Clips that need generation
    silent_clips: List[Dict[str, Any]] = []  # Clips detected as silent
