"""Service for audio review operations.

Provides functionality to detect problem clips (silent clips and cache misses)
and manage variant audio files for review and replacement.
"""

import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

import yaml

from script_to_speech.audio_generation.constants import DEFAULT_SILENCE_THRESHOLD
from script_to_speech.audio_generation.models import AudioClipInfo
from script_to_speech.audio_generation.processing import (
    check_for_silence,
    plan_audio_generation,
)
from script_to_speech.audio_generation.utils import load_json_chunks
from script_to_speech.text_processors.processor_manager import TextProcessorManager
from script_to_speech.text_processors.utils import get_text_processor_configs
from script_to_speech.tts_providers.tts_provider_manager import TTSProviderManager

from ..config import settings
from ..models import (
    CacheMissesResponse,
    ProblemClipInfo,
    SilentClipsResponse,
)

logger = logging.getLogger(__name__)

# Maximum number of cache misses to display in the UI
MAX_CACHE_MISSES_DISPLAY = 30


class ReviewService:
    """Service for audio review operations."""

    def __init__(self) -> None:
        self.workspace_dir = settings.WORKSPACE_DIR

    def _load_project_config(
        self, project_name: str
    ) -> Tuple[list, TTSProviderManager, TextProcessorManager, Path]:
        """Load project configuration for analysis.

        Args:
            project_name: Name of the project

        Returns:
            Tuple of (dialogues, tts_manager, processor, cache_folder)

        Raises:
            FileNotFoundError: If required files don't exist
        """
        # Build paths
        input_path = self.workspace_dir / "input" / project_name
        output_path = self.workspace_dir / "output" / project_name
        cache_folder = output_path / "cache"

        json_path = input_path / f"{project_name}.json"
        voice_config_path = input_path / f"{project_name}_voice_config.yaml"

        # Validate paths exist
        if not json_path.exists():
            raise FileNotFoundError(f"Screenplay JSON not found: {json_path}")
        if not voice_config_path.exists():
            raise FileNotFoundError(f"Voice config not found: {voice_config_path}")

        # Create cache folder if it doesn't exist
        cache_folder.mkdir(parents=True, exist_ok=True)

        # Load dialogues
        dialogues = load_json_chunks(str(json_path))
        logger.info(f"Loaded {len(dialogues)} dialogue chunks")

        # Load voice config
        with open(voice_config_path, "r") as f:
            tts_config_data = yaml.safe_load(f)

        # Initialize TTS provider manager
        tts_manager = TTSProviderManager(
            config_data=tts_config_data,
            overall_provider=None,
            dummy_tts_provider_override=False,
        )

        # Load text processor configs (project-specific or default)
        text_processor_configs = get_text_processor_configs(json_path, None)
        processor = TextProcessorManager(text_processor_configs)

        return dialogues, tts_manager, processor, cache_folder

    def get_cache_misses(self, project_name: str) -> CacheMissesResponse:
        """Get cache misses for a project (fast operation).

        This runs the planning phase to identify dialogue lines that don't have
        cached audio files.

        Args:
            project_name: Name of the project to analyze

        Returns:
            CacheMissesResponse with cache misses list and metadata
        """
        logger.info(f"Getting cache misses for project: {project_name}")

        dialogues, tts_manager, processor, cache_folder = self._load_project_config(
            project_name
        )

        # Run planning phase to identify cache misses
        all_tasks, plan_reporting_state = plan_audio_generation(
            dialogues=dialogues,
            tts_provider_manager=tts_manager,
            processor=processor,
            cache_folder=str(cache_folder),
            cache_overrides_dir=None,
        )
        logger.info(
            f"Planning complete: {len(all_tasks)} tasks, "
            f"{len(plan_reporting_state.cache_misses)} cache misses"
        )

        # Convert to ProblemClipInfo format
        cache_misses = self._convert_clips(
            plan_reporting_state.cache_misses,
            include_dbfs=False,
            tts_manager=tts_manager,
        )

        # Cap cache misses
        total_cache_misses = len(cache_misses)
        cache_misses_capped = total_cache_misses > MAX_CACHE_MISSES_DISPLAY
        if cache_misses_capped:
            cache_misses = cache_misses[:MAX_CACHE_MISSES_DISPLAY]
            logger.info(
                f"Capped cache misses from {total_cache_misses} to {MAX_CACHE_MISSES_DISPLAY}"
            )

        return CacheMissesResponse(
            cache_misses=cache_misses,
            cache_misses_capped=cache_misses_capped,
            total_cache_misses=total_cache_misses,
            cache_folder=str(cache_folder),
            scanned_at=datetime.now(timezone.utc).isoformat(),
        )

    def get_silent_clips(
        self, project_name: str, refresh: bool = False
    ) -> SilentClipsResponse:
        """Get silent clips for a project.

        Returns cached data if available. Only scans when refresh=True.
        If no cache and refresh=False, returns empty response.

        Args:
            project_name: Name of the project to analyze
            refresh: If True, force rescan of audio files

        Returns:
            SilentClipsResponse with silent clips list and metadata
        """
        # Import here to avoid circular import
        from .audiobook_generation_service import audiobook_generation_service

        # Check cache first (always)
        cached = audiobook_generation_service.get_cached_silent_clips(project_name)

        if not refresh:
            # Normal fetch: return cache or empty (never scan automatically)
            if cached is not None:
                logger.info(
                    f"Returning cached silent clips for project '{project_name}': "
                    f"{len(cached.silent_clips)} clips"
                )
                return cached

            # No cache and not refreshing - return empty response
            logger.info(
                f"No cached silent clips for project '{project_name}', "
                "returning empty (refresh not requested)"
            )
            return SilentClipsResponse(
                silent_clips=[],
                total_clips_scanned=0,
                cache_folder="",
                scanned_at=None,  # Indicates never scanned
            )

        # Refresh requested: scan audio files and update cache
        logger.info(f"Refreshing silent clips for project: {project_name}")
        result = self._scan_for_silent_clips(project_name)

        # Update cache with fresh scan results
        audiobook_generation_service.set_cached_silent_clips(project_name, result)

        return result

    def _scan_for_silent_clips(self, project_name: str) -> SilentClipsResponse:
        """Scan audio files for silence (slow operation).

        This is the fallback when no cached data is available from generation.

        Args:
            project_name: Name of the project to analyze

        Returns:
            SilentClipsResponse with silent clips list and metadata
        """
        dialogues, tts_manager, processor, cache_folder = self._load_project_config(
            project_name
        )

        # Run planning phase to get task list
        all_tasks, _ = plan_audio_generation(
            dialogues=dialogues,
            tts_provider_manager=tts_manager,
            processor=processor,
            cache_folder=str(cache_folder),
            cache_overrides_dir=None,
        )
        logger.info(f"Planning complete: {len(all_tasks)} tasks")

        # Count cached clips (those that will be scanned)
        cached_clips_count = sum(1 for t in all_tasks if t.is_cache_hit)

        # Check for silence in existing cached files
        silence_reporting_state = check_for_silence(
            tasks=all_tasks,
            silence_threshold=DEFAULT_SILENCE_THRESHOLD,
        )
        logger.info(
            f"Silence check complete: {len(silence_reporting_state.silent_clips)} silent clips"
        )

        # Convert to ProblemClipInfo format
        silent_clips = self._convert_clips(
            silence_reporting_state.silent_clips,
            include_dbfs=True,
            tts_manager=tts_manager,
        )

        return SilentClipsResponse(
            silent_clips=silent_clips,
            total_clips_scanned=cached_clips_count,
            cache_folder=str(cache_folder),
            scanned_at=datetime.now(timezone.utc).isoformat(),
        )

    def commit_variant(
        self, source_path: str, target_cache_filename: str, project_name: str
    ) -> Tuple[bool, str, str]:
        """Copy a variant from standalone_speech to the project cache.

        Args:
            source_path: Filename (or path) of the variant file in standalone_speech
            target_cache_filename: Target filename in the cache folder
            project_name: Name of the project

        Returns:
            Tuple of (success, target_path, message)
        """
        # Treat source_path as filename and construct full path
        # Using .name ensures we only use the filename (prevents path traversal)
        filename = Path(source_path).name
        source = settings.AUDIO_OUTPUT_DIR / filename

        # Validate source exists
        if not source.exists():
            return False, "", f"Source file not found: {filename}"

        # Build target path
        cache_folder = self.workspace_dir / "output" / project_name / "cache"
        cache_folder.mkdir(parents=True, exist_ok=True)
        target = cache_folder / target_cache_filename

        try:
            # Copy file (preserve metadata)
            shutil.copy2(source, target)
            logger.info(f"Committed variant: {source} -> {target}")
            return True, str(target), "Variant committed successfully"
        except Exception as e:
            logger.error(f"Failed to commit variant: {e}")
            return False, "", f"Failed to commit variant: {str(e)}"

    def delete_variant(self, file_path: str) -> bool:
        """Delete a variant file from standalone_speech.

        Args:
            file_path: Path to the file to delete

        Returns:
            True if deleted, False otherwise
        """
        path = Path(file_path)

        # Validate path is in standalone_speech directory (security check)
        try:
            path.resolve().relative_to(settings.AUDIO_OUTPUT_DIR.resolve())
        except ValueError:
            logger.warning(
                f"Attempted to delete file outside standalone_speech: {file_path}"
            )
            return False

        if path.exists():
            try:
                path.unlink()
                logger.info(f"Deleted variant: {file_path}")
                return True
            except Exception as e:
                logger.error(f"Failed to delete variant: {e}")
                return False

        return False

    def get_cache_audio_path(self, project_name: str, filename: str) -> Path:
        """Get the full path to a cache audio file.

        Args:
            project_name: Name of the project
            filename: Cache filename

        Returns:
            Full path to the cache file
        """
        return self.workspace_dir / "output" / project_name / "cache" / filename

    def _convert_clips(
        self,
        clips_dict: dict[str, AudioClipInfo],
        include_dbfs: bool,
        tts_manager: TTSProviderManager,
    ) -> List[ProblemClipInfo]:
        """Convert AudioClipInfo dict to ProblemClipInfo list.

        Args:
            clips_dict: Dictionary mapping cache filenames to AudioClipInfo
            include_dbfs: Whether to include dBFS level in output
            tts_manager: TTS provider manager to get speaker configurations

        Returns:
            List of ProblemClipInfo objects
        """
        result = []
        for cache_filename, clip_info in clips_dict.items():
            # Get full speaker config from tts_manager for regeneration
            # Use clip_info.speaker (the actual config key) for lookup
            speaker_config = {}
            speaker_key = clip_info.speaker or "default"
            try:
                speaker_config = tts_manager.get_speaker_configuration(speaker_key)
                logger.info(f"Got speaker config for '{speaker_key}': {speaker_config}")
            except Exception as e:
                logger.warning(f"Could not get speaker config for '{speaker_key}': {e}")

            result.append(
                ProblemClipInfo(
                    cache_filename=cache_filename,
                    speaker=clip_info.speaker_display or "(default)",
                    voice_id=clip_info.speaker_id or "",
                    provider=clip_info.provider_id or "",
                    text=clip_info.text,
                    dbfs_level=clip_info.dbfs_level if include_dbfs else None,
                    speaker_config=speaker_config,
                )
            )
        return result


# Singleton instance
review_service = ReviewService()
