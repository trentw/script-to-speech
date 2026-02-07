"""Pydantic models for API requests and responses."""

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from script_to_speech.audio_generation.constants import DEFAULT_SILENCE_THRESHOLD


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
        serialize_by_alias=True,  # Output camelCase in JSON responses
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


class Id3TagConfig(CamelModel):
    """ID3 tag configuration for audiobook metadata."""

    title: str = ""
    screenplay_author: str = ""
    date: str = ""


class Id3TagConfigUpdate(CamelModel):
    """Request body for updating ID3 tag configuration (partial update)."""

    title: Optional[str] = None
    screenplay_author: Optional[str] = None
    date: Optional[str] = None


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


class NewProjectResponse(CamelModel):
    """Response from creating a new project."""

    input_path: str
    output_path: str
    screenplay_name: str
    # Header/footer detection results (for popover display)
    auto_removed_patterns: Optional[List["DetectedPatternResponse"]] = None
    suggested_patterns: Optional[List["DetectedPatternResponse"]] = None


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
    EXPORTING = "exporting"
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
    silence_threshold: Optional[float] = (
        DEFAULT_SILENCE_THRESHOLD  # dBFS, None to disable
    )
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


# Audio Review Models


class ProblemClipInfo(CamelModel):
    """Information about a problem audio clip (silent or cache miss)."""

    cache_filename: str  # Cache filename for reference
    speaker: str  # e.g., "NORMA" or "(default)"
    voice_id: str  # Cache filename component (for display only)
    provider: str  # TTS provider identifier
    text: str  # Full dialogue text
    dbfs_level: Optional[float] = None  # For silent clips, the detected dBFS level
    speaker_config: Dict[str, Any] = {}  # Full speaker config for regeneration
    # Human-readable voice library identifier (e.g., "sarah" instead of "9BWtsMINqrJLrRacOk9x")
    # Only available for voices defined in the voice library; None for custom voices
    sts_id: Optional[str] = None


class CacheMissesResponse(CamelModel):
    """Response containing cache misses for a project."""

    cache_misses: List[ProblemClipInfo]
    cache_misses_capped: bool = False  # True if cache misses were capped
    total_cache_misses: int = 0  # Total count before capping
    cache_folder: str  # Path to cache folder for audio serving
    scanned_at: str  # ISO timestamp of when scan was performed


class SilentClipsResponse(CamelModel):
    """Response containing silent clips for a project."""

    silent_clips: List[ProblemClipInfo]
    total_clips_scanned: int = 0  # Number of cached clips scanned
    cache_folder: str  # Path to cache folder for audio serving
    scanned_at: Optional[str] = (
        None  # ISO timestamp of when scan was performed (None if never scanned)
    )


class CommitVariantRequest(BaseModel):
    """Request to commit a variant to the project cache."""

    source_path: str  # Path to variant in standalone_speech
    target_cache_filename: str  # Destination cache filename
    project_name: str


class CommitVariantResponse(CamelModel):
    """Response from committing a variant."""

    success: bool
    target_path: str
    message: str


class DeleteVariantRequest(BaseModel):
    """Request to delete a variant file."""

    file_path: str  # Path to file in standalone_speech


# Header/Footer Detection Models

# Threshold constants for auto-apply vs suggestion
AUTO_APPLY_THRESHOLD = 40.0  # Patterns >= 40% are auto-applied
SUGGESTION_THRESHOLD = 20.0  # Patterns 20-40% are suggestions


class DetectedPatternResponse(CamelModel):
    """A detected header/footer pattern from the detector."""

    text: str
    position: str  # "header" or "footer"
    occurrence_count: int
    total_pages: int
    occurrence_percentage: float
    is_blacklisted: bool
    example_full_lines: List[str]  # Show context for user verification
    variations: List[str]
    is_auto_applied: bool  # True if >= AUTO_APPLY_THRESHOLD
    is_suggestion: bool  # True if SUGGESTION_THRESHOLD <= % < AUTO_APPLY_THRESHOLD


class DetectionResultResponse(CamelModel):
    """Complete detection results from header/footer analysis."""

    patterns: List[DetectedPatternResponse]
    pdf_path: str
    total_pages: int
    lines_scanned: int
    auto_applied_patterns: List[DetectedPatternResponse]
    suggested_patterns: List[DetectedPatternResponse]


class ReparseRequest(BaseModel):
    """Request to re-parse a screenplay with header/footer removal options."""

    input_path: str  # Path to project input directory
    screenplay_name: str  # Name of the screenplay
    strings_to_remove: List[str]  # Patterns to remove
    remove_lines: int = 2  # Number of lines from top/bottom to check for removal
    global_replace: bool = (
        False  # If true, replace throughout document (sets remove_lines=0)
    )


class ReparseResponse(CamelModel):
    """Response from re-parsing a screenplay."""

    success: bool
    message: str
    removal_metadata: Optional[Dict[str, Any]] = None  # Details about what was removed


# Rebuild models to resolve forward references
NewProjectResponse.model_rebuild()
