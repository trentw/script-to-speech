"""Text processor configuration API routes."""

import logging

from fastapi import APIRouter, HTTPException, Query

from ..models import (
    ApiResponse,
    TextProcessorConfigUpdate,
    TextProcessorPreviewDiffRequest,
    TextProcessorPreviewRequest,
    TextProcessorResetRequest,
    TextProcessorValidateRequest,
)
from ..services.text_processor_config_service import (
    ConfigConflictError,
    ConfigValidationError,
    text_processor_config_service,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/text-processors/registry")
async def get_text_processor_registry() -> ApiResponse:
    """List available processors/preprocessors with schemas and chunk metadata."""
    try:
        data = text_processor_config_service.get_registry()
        return ApiResponse(ok=True, data=data)
    except Exception as e:
        logger.error(f"Failed to build text processor registry: {e}")
        return ApiResponse(
            ok=False,
            error="Failed to build text processor registry",
            details={"error_message": str(e)},
        )


@router.post("/text-processors/validate")
async def validate_text_processor_entries(
    body: TextProcessorValidateRequest,
) -> ApiResponse:
    """Validate config entries against their processor implementations."""
    try:
        entries = [entry.model_dump() for entry in body.entries]
        data = text_processor_config_service.validate_entries(entries)
        return ApiResponse(ok=True, data=data)
    except Exception as e:
        logger.error(f"Failed to validate text processor entries: {e}")
        return ApiResponse(
            ok=False,
            error="Failed to validate text processor entries",
            details={"error_message": str(e)},
        )


@router.get("/project/text-processor-config")
async def get_text_processor_config(
    input_path: str = Query(..., description="Path to the project's input directory"),
) -> ApiResponse:
    """Get a project's text processor config.

    Auto-creates the config (seeded from defaults) if it doesn't exist.
    """
    try:
        data = text_processor_config_service.read_config(input_path)
        return ApiResponse(ok=True, data=data)
    except ValueError as e:
        logger.warning(f"Invalid project path {input_path}: {e}")
        return ApiResponse(
            ok=False,
            error="Invalid project path",
            details={"path": input_path, "error_message": str(e)},
        )
    except Exception as e:
        logger.error(f"Failed to get text processor config for {input_path}: {e}")
        return ApiResponse(
            ok=False,
            error="Failed to get text processor configuration",
            details={"path": input_path, "error_message": str(e)},
        )


@router.put("/project/text-processor-config")
async def update_text_processor_config(
    body: TextProcessorConfigUpdate,
    input_path: str = Query(..., description="Path to the project's input directory"),
) -> ApiResponse:
    """Write a project's text processor config from structured entries.

    Requires base_file_hash from the last read; returns 409 when the file
    changed out from under the editor (CLI edit, another window, etc.).
    """
    try:
        entries = [entry.model_dump() for entry in body.entries]
        data = text_processor_config_service.write_config(
            input_path, entries, body.base_file_hash
        )
        return ApiResponse(ok=True, data=data)
    except ConfigConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ConfigValidationError as e:
        return ApiResponse(
            ok=False,
            error="Text processor config validation failed",
            details={"errors": e.errors},
        )
    except ValueError as e:
        logger.warning(f"Invalid project path {input_path}: {e}")
        return ApiResponse(
            ok=False,
            error="Invalid project path",
            details={"path": input_path, "error_message": str(e)},
        )
    except Exception as e:
        logger.error(f"Failed to update text processor config for {input_path}: {e}")
        return ApiResponse(
            ok=False,
            error="Failed to update text processor configuration",
            details={"path": input_path, "error_message": str(e)},
        )


@router.post("/project/text-processor-config/preview")
def preview_text_processor_config(
    body: TextProcessorPreviewRequest,
    input_path: str = Query(..., description="Path to the project's input directory"),
) -> ApiResponse:
    """Preview a pipeline's effect on the project's screenplay chunks.

    Synchronous by design: the pipeline is in-memory text processing over a
    few thousand small chunks (sub-second). Declared as a plain `def` so
    FastAPI runs it in the threadpool without blocking the event loop.
    """
    try:
        entries = (
            [entry.model_dump() for entry in body.entries]
            if body.entries is not None
            else None
        )
        data = text_processor_config_service.run_preview_for_project(
            input_path,
            entries,
            body.include_preprocessor_snapshots,
            body.max_changed_chunks,
        )
        return ApiResponse(ok=True, data=data)
    except ConfigValidationError as e:
        return ApiResponse(
            ok=False,
            error="Text processor config validation failed",
            details={"errors": e.errors},
        )
    except ValueError as e:
        logger.warning(f"Preview failed for {input_path}: {e}")
        return ApiResponse(
            ok=False,
            error="Failed to preview text processors",
            details={"path": input_path, "error_message": str(e)},
        )
    except Exception as e:
        logger.error(f"Failed to preview text processors for {input_path}: {e}")
        return ApiResponse(
            ok=False,
            error="Failed to preview text processors",
            details={"path": input_path, "error_message": str(e)},
        )


@router.post("/project/text-processor-config/preview-diff")
def preview_diff_text_processor_config(
    body: TextProcessorPreviewDiffRequest,
    input_path: str = Query(..., description="Path to the project's input directory"),
) -> ApiResponse:
    """Diff a draft pipeline against a baseline over the project's chunks.

    Powers the "what do my unsaved changes add" preview: only chunks whose
    final output differs between the two runs are returned. Synchronous plain
    `def` for the same reasons as the preview endpoint.
    """
    try:
        draft_entries = [entry.model_dump() for entry in body.draft_entries]
        baseline_entries = (
            [entry.model_dump() for entry in body.baseline_entries]
            if body.baseline_entries is not None
            else None
        )
        data = text_processor_config_service.run_preview_diff_for_project(
            input_path,
            draft_entries,
            baseline_entries,
            body.max_changed_chunks,
        )
        return ApiResponse(ok=True, data=data)
    except ConfigValidationError as e:
        return ApiResponse(
            ok=False,
            error="Text processor config validation failed",
            details={"errors": e.errors},
        )
    except ValueError as e:
        logger.warning(f"Preview diff failed for {input_path}: {e}")
        return ApiResponse(
            ok=False,
            error="Failed to preview text processor changes",
            details={"path": input_path, "error_message": str(e)},
        )
    except Exception as e:
        logger.error(f"Failed to preview text processor diff for {input_path}: {e}")
        return ApiResponse(
            ok=False,
            error="Failed to preview text processor changes",
            details={"path": input_path, "error_message": str(e)},
        )


@router.post("/project/text-processor-config/convert")
async def convert_text_processor_config(
    input_path: str = Query(..., description="Path to the project's input directory"),
) -> ApiResponse:
    """Convert a legacy additive config into an equivalent standalone config."""
    try:
        data = text_processor_config_service.convert_legacy_to_standalone(input_path)
        return ApiResponse(ok=True, data=data)
    except ValueError as e:
        logger.warning(f"Invalid project path {input_path}: {e}")
        return ApiResponse(
            ok=False,
            error="Invalid project path",
            details={"path": input_path, "error_message": str(e)},
        )
    except Exception as e:
        logger.error(f"Failed to convert text processor config for {input_path}: {e}")
        return ApiResponse(
            ok=False,
            error="Failed to convert text processor configuration",
            details={"path": input_path, "error_message": str(e)},
        )


@router.post("/project/text-processor-config/reset")
async def reset_text_processor_config(
    body: TextProcessorResetRequest,
    input_path: str = Query(..., description="Path to the project's input directory"),
) -> ApiResponse:
    """Overwrite a project's config by re-seeding from shipped or user defaults."""
    try:
        data = text_processor_config_service.reset_config(input_path, body.source)
        return ApiResponse(ok=True, data=data)
    except ValueError as e:
        logger.warning(f"Failed reset for {input_path}: {e}")
        return ApiResponse(
            ok=False,
            error="Failed to reset text processor configuration",
            details={"path": input_path, "error_message": str(e)},
        )
    except FileNotFoundError as e:
        return ApiResponse(
            ok=False,
            error="Seed source not found",
            details={"path": input_path, "error_message": str(e)},
        )
    except Exception as e:
        logger.error(f"Failed to reset text processor config for {input_path}: {e}")
        return ApiResponse(
            ok=False,
            error="Failed to reset text processor configuration",
            details={"path": input_path, "error_message": str(e)},
        )
