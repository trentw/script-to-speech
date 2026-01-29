"""Audiobook generation service wrapping the core audio generation pipeline."""

import asyncio
import logging
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from script_to_speech.audio_generation.download_manager import AudioDownloadManager
from script_to_speech.audio_generation.log_messages import (
    PipelinePhase,
    log_completion,
    log_phase,
)
from script_to_speech.audio_generation.models import AudioGenerationTask
from script_to_speech.audio_generation.models import TaskStatus as CoreTaskStatus
from script_to_speech.audio_generation.processing import (
    SilenceCheckProgressTracker,
    apply_cache_overrides,
    check_for_silence,
    plan_audio_generation,
    update_cache_duplicate_state,
)
from script_to_speech.audio_generation.reporting import (
    ReportingState,
    print_unified_report,
    recheck_audio_files,
)
from script_to_speech.audio_generation.utils import (
    ConcatenationProgressTracker,
    concatenate_tasks_batched,
    load_json_chunks,
)
from script_to_speech.text_processors.processor_manager import TextProcessorManager
from script_to_speech.text_processors.utils import get_text_processor_configs
from script_to_speech.tts_providers.tts_provider_manager import TTSProviderManager
from script_to_speech.utils.audio_utils import configure_ffmpeg
from script_to_speech.utils.file_system_utils import (
    create_output_folders,
    save_processed_dialogues,
)
from script_to_speech.utils.id3_tag_utils import set_id3_tags_from_config
from script_to_speech.utils.logging import (
    get_screenplay_logger,
    setup_screenplay_logging,
)

from ..config import settings
from ..models import (
    AudiobookGenerationMode,
    AudiobookGenerationPhase,
    AudiobookGenerationProgress,
    AudiobookGenerationRequest,
    AudiobookGenerationResult,
    AudiobookGenerationStats,
    ProblemClipInfo,
    SilentClipsResponse,
    TaskStatus,
)

logger = get_screenplay_logger("audiobook_generation_service")

# Phase weights for progress calculation (start, end percentages)
PHASE_WEIGHTS = {
    AudiobookGenerationPhase.PENDING: (0.0, 0.0),
    AudiobookGenerationPhase.PLANNING: (0.0, 0.05),
    AudiobookGenerationPhase.APPLYING_OVERRIDES: (0.05, 0.08),
    AudiobookGenerationPhase.CHECKING_SILENCE: (0.08, 0.12),
    AudiobookGenerationPhase.GENERATING: (0.12, 0.90),
    AudiobookGenerationPhase.CONCATENATING: (0.90, 0.96),
    AudiobookGenerationPhase.EXPORTING: (0.96, 0.98),
    AudiobookGenerationPhase.FINALIZING: (0.98, 1.0),
    AudiobookGenerationPhase.COMPLETED: (1.0, 1.0),
    AudiobookGenerationPhase.FAILED: (0.0, 0.0),
}


class AudiobookGenerationTask:
    """Represents an audiobook generation task."""

    def __init__(self, task_id: str, request: AudiobookGenerationRequest):
        self.task_id = task_id
        self.request = request
        self.status = TaskStatus.PENDING
        self.phase = AudiobookGenerationPhase.PENDING
        self.phase_progress = 0.0
        self.message = "Task created"

        # Results
        self.stats = AudiobookGenerationStats()
        self.output_file: Optional[str] = None
        self.cache_folder: Optional[str] = None
        self.log_file: Optional[str] = None
        self.cache_misses: List[Dict[str, Any]] = []
        self.silent_clips: List[Dict[str, Any]] = []

        # Error tracking
        self.error: Optional[str] = None

        # Timestamps
        self.created_at = datetime.now(timezone.utc)
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None

        # References for progress polling (snapshot-based)
        self._download_manager: Optional[AudioDownloadManager] = None
        self._silence_tracker: Optional[SilenceCheckProgressTracker] = None
        self._concat_tracker: Optional[ConcatenationProgressTracker] = None

    def get_overall_progress(self) -> float:
        """Calculate overall progress based on phase and phase_progress."""
        start, end = PHASE_WEIGHTS.get(self.phase, (0.0, 0.0))
        return start + (end - start) * self.phase_progress

    def set_download_manager(self, manager: Optional[AudioDownloadManager]) -> None:
        """Set reference to download manager for progress polling."""
        self._download_manager = manager

    def set_silence_tracker(
        self, tracker: Optional[SilenceCheckProgressTracker]
    ) -> None:
        """Set reference to silence check progress tracker."""
        self._silence_tracker = tracker

    def set_concat_tracker(
        self, tracker: Optional[ConcatenationProgressTracker]
    ) -> None:
        """Set reference to concatenation progress tracker."""
        self._concat_tracker = tracker

    def get_progress_snapshot(self) -> Optional[Dict[str, Any]]:
        """Get progress snapshot from download manager if available."""
        if self._download_manager is not None:
            return self._download_manager.get_progress_snapshot()
        return None

    def get_silence_progress_snapshot(self) -> Optional[Dict[str, Any]]:
        """Get progress snapshot from silence tracker if available."""
        if self._silence_tracker is not None:
            return self._silence_tracker.get_progress_snapshot()
        return None

    def get_concat_progress_snapshot(self) -> Optional[Dict[str, Any]]:
        """Get progress snapshot from concatenation tracker if available."""
        if self._concat_tracker is not None:
            return self._concat_tracker.get_progress_snapshot()
        return None


class AudiobookGenerationService:
    """Service for managing audiobook generation tasks."""

    def __init__(self, workspace_dir: Optional[Path] = None) -> None:
        """Initialize the audiobook generation service.

        Args:
            workspace_dir: Root directory for project workspace. If None, uses settings.WORKSPACE_DIR.
        """
        self._tasks: Dict[str, AudiobookGenerationTask] = {}
        self._lock = threading.Lock()

        # Cache of silent clips by project name (shared with review service)
        self._silent_clips_cache: Dict[str, SilentClipsResponse] = {}

        # Use provided workspace_dir or fall back to settings
        if workspace_dir is None:
            workspace_dir = settings.WORKSPACE_DIR

        if workspace_dir is None:
            raise ValueError(
                "Workspace directory is not configured. Set STS_WORKSPACE_DIR environment variable."
            )

        self.workspace_dir = Path(workspace_dir)

    def get_cached_silent_clips(
        self, project_name: str
    ) -> Optional[SilentClipsResponse]:
        """Get cached silent clips for a project (if available).

        This cache is populated after audio generation completes and can be
        used by the review service to avoid re-scanning audio files.

        Args:
            project_name: Name of the project

        Returns:
            SilentClipsResponse if cached, None otherwise
        """
        return self._silent_clips_cache.get(project_name)

    def set_cached_silent_clips(
        self, project_name: str, data: SilentClipsResponse
    ) -> None:
        """Update cached silent clips for a project.

        Called by review service after a manual rescan to keep cache fresh.

        Args:
            project_name: Name of the project
            data: The silent clips response to cache
        """
        self._silent_clips_cache[project_name] = data
        logger.info(
            f"Updated silent clips cache for '{project_name}': "
            f"{len(data.silent_clips)} clips"
        )

    def create_task(self, request: AudiobookGenerationRequest) -> str:
        """Create a new audiobook generation task.

        Args:
            request: The generation request parameters

        Returns:
            task_id: The unique identifier for this task
        """
        task_id = str(uuid.uuid4())
        task = AudiobookGenerationTask(task_id, request)

        with self._lock:
            self._tasks[task_id] = task

        # Start the generation in the background
        asyncio.create_task(self._process_task(task))

        return task_id

    def get_progress(self, task_id: str) -> Optional[AudiobookGenerationProgress]:
        """Get the current progress of a generation task.

        Args:
            task_id: The task identifier

        Returns:
            AudiobookGenerationProgress or None if task not found
        """
        with self._lock:
            task = self._tasks.get(task_id)

        if not task:
            return None

        # Poll silence tracker if in CHECKING_SILENCE phase
        if task.phase == AudiobookGenerationPhase.CHECKING_SILENCE:
            snapshot = task.get_silence_progress_snapshot()
            if snapshot:
                task.phase_progress = snapshot.get("progress", 0.0)

        # Poll concatenation tracker if in CONCATENATING phase
        # (also check for phase transition to EXPORTING based on tracker stage)
        if task.phase == AudiobookGenerationPhase.CONCATENATING:
            snapshot = task.get_concat_progress_snapshot()
            if snapshot:
                stage = snapshot.get("stage", "clips")
                if stage == "exporting":
                    # Transition to EXPORTING phase
                    task.phase = AudiobookGenerationPhase.EXPORTING
                    task.phase_progress = 0.5  # Exporting is in progress
                    task.message = "Exporting final audiobook"
                else:
                    task.phase_progress = snapshot.get("progress", 0.0)
                    if stage == "clips":
                        task.message = "Processing audio clips"
                    elif stage == "batches":
                        task.message = "Concatenating batches"

        # Poll concatenation tracker for EXPORTING phase progress
        if task.phase == AudiobookGenerationPhase.EXPORTING:
            # EXPORTING phase progress stays at 0.5 until export completes
            # (export is a single blocking operation)
            pass

        # Build stats from download manager snapshot if available
        stats = task.stats
        if task.phase == AudiobookGenerationPhase.GENERATING:
            snapshot = task.get_progress_snapshot()
            if snapshot:
                by_status = snapshot.get("by_status", {})
                stats = AudiobookGenerationStats(
                    total_clips=snapshot.get("total_tasks", 0),
                    cached_clips=by_status.get("cached", 0),
                    generated_clips=by_status.get("generated", 0),
                    failed_clips=(
                        by_status.get("failed_rate_limit", 0)
                        + by_status.get("failed_other", 0)
                    ),
                    skipped_duplicate_clips=by_status.get("skipped_duplicate", 0),
                    silent_clips=0,  # Silent info comes from ReportingState, not TaskStatus
                    rate_limited_clips=by_status.get("failed_rate_limit", 0),
                    by_status=by_status,
                    rate_limited_providers=snapshot.get("rate_limited_providers"),
                )

                # Update phase progress based on generation completion
                total = snapshot.get("total_tasks", 0)
                completed = snapshot.get("completed_count", 0)
                if total > 0:
                    task.phase_progress = completed / total

        return AudiobookGenerationProgress(
            task_id=task_id,
            status=task.status,
            phase=task.phase,
            phase_progress=task.phase_progress,
            overall_progress=task.get_overall_progress(),
            message=task.message,
            stats=stats,
            created_at=task.created_at.isoformat() if task.created_at else None,
            started_at=task.started_at.isoformat() if task.started_at else None,
            completed_at=task.completed_at.isoformat() if task.completed_at else None,
            error=task.error,
        )

    def get_result(self, task_id: str) -> Optional[AudiobookGenerationResult]:
        """Get the final result of a completed generation task.

        Args:
            task_id: The task identifier

        Returns:
            AudiobookGenerationResult or None if task not found or not completed
        """
        with self._lock:
            task = self._tasks.get(task_id)

        if not task or task.status != TaskStatus.COMPLETED:
            return None

        return AudiobookGenerationResult(
            output_file=task.output_file,
            cache_folder=task.cache_folder or "",
            log_file=task.log_file,
            stats=task.stats,
            cache_misses=task.cache_misses,
            silent_clips=task.silent_clips,
        )

    def get_all_tasks(self) -> List[AudiobookGenerationProgress]:
        """Get progress of all tasks."""
        with self._lock:
            task_ids = list(self._tasks.keys())

        return [
            progress
            for task_id in task_ids
            if (progress := self.get_progress(task_id)) is not None
        ]

    def cleanup_old_tasks(self, max_age_hours: int = 24) -> int:
        """Clean up old completed tasks.

        Args:
            max_age_hours: Maximum age in hours before cleanup

        Returns:
            Number of tasks removed
        """
        cutoff_time = datetime.now(timezone.utc).timestamp() - (max_age_hours * 3600)
        removed_count = 0

        with self._lock:
            task_ids_to_remove = [
                task_id
                for task_id, task in self._tasks.items()
                if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)
                and task.completed_at
                and task.completed_at.timestamp() < cutoff_time
            ]

            for task_id in task_ids_to_remove:
                del self._tasks[task_id]
                removed_count += 1

        return removed_count

    async def _process_task(self, task: AudiobookGenerationTask) -> None:
        """Process a generation task in the background."""
        try:
            task.status = TaskStatus.PROCESSING
            task.started_at = datetime.now(timezone.utc)
            task.message = "Starting audiobook generation"

            # Run the blocking generation in a thread pool
            await asyncio.to_thread(self._run_generation, task)

            task.status = TaskStatus.COMPLETED
            task.phase = AudiobookGenerationPhase.COMPLETED
            task.phase_progress = 1.0
            task.completed_at = datetime.now(timezone.utc)
            task.message = "Audiobook generation completed"

        except Exception as e:
            logger.error(
                f"Error processing audiobook generation task {task.task_id}: {e}",
                exc_info=True,
            )
            task.status = TaskStatus.FAILED
            task.phase = AudiobookGenerationPhase.FAILED
            task.error = str(e)
            task.message = f"Generation failed: {str(e)}"
            task.completed_at = datetime.now(timezone.utc)

    def _run_generation(self, task: AudiobookGenerationTask) -> None:
        """Run the audiobook generation pipeline (blocking).

        This method orchestrates the core generation phases:
        1. Planning
        2. Apply cache overrides (optional)
        3. Check for silence (optional)
        4. Fetch/generate audio (not in dry-run)
        5. Concatenate (full mode only)
        6. Finalize with ID3 tags (full mode only)
        """
        request = task.request

        # Determine run mode
        is_dry_run = request.mode == AudiobookGenerationMode.DRY_RUN
        is_populate_cache = request.mode == AudiobookGenerationMode.POPULATE_CACHE

        run_mode = (
            "dry-run"
            if is_dry_run
            else "populate-cache" if is_populate_cache else "generate-output"
        )

        logger.info(f"Starting {run_mode.upper()} mode for task {task.task_id}")

        # === SETUP ===
        task.phase = AudiobookGenerationPhase.PLANNING
        task.phase_progress = 0.0
        task.message = "Setting up generation environment"

        # Configure ffmpeg
        configure_ffmpeg()

        # Create output folders (use workspace_dir for correct prod/dev paths)
        main_output_folder, cache_folder, logs_folder, log_file = create_output_folders(
            request.input_json_path,
            run_mode,
            dummy_provider_override=False,
            base_path=self.workspace_dir,
        )

        task.cache_folder = str(cache_folder)
        task.log_file = str(log_file) if log_file else None

        # Set up file logging (creates the actual log file)
        if log_file:
            setup_screenplay_logging(str(log_file))

        # Build output file path
        input_path = Path(request.input_json_path)
        base_name = input_path.stem
        output_file = main_output_folder / f"{base_name}.mp3"

        # Load voice config
        with open(request.voice_config_path, "r", encoding="utf-8") as f:
            tts_config_data = yaml.safe_load(f)

        # Initialize TTS provider manager
        tts_manager = TTSProviderManager(
            config_data=tts_config_data,
            overall_provider=None,
            dummy_tts_provider_override=False,
        )

        # Initialize text processor
        text_processor_configs = get_text_processor_configs(
            input_path,
            (
                [Path(p) for p in request.text_processor_configs]
                if request.text_processor_configs
                else None
            ),
        )
        processor = TextProcessorManager(text_processor_configs)

        # Load dialogues
        dialogues = load_json_chunks(request.input_json_path)

        task.phase_progress = 0.5
        task.message = f"Loaded {len(dialogues)} dialogue chunks"

        # Create combined reporting state for CLI-parity logging
        combined_reporting_state = ReportingState()

        # === PHASE 1: PLANNING ===
        log_phase(logger, PipelinePhase.PLANNING)
        task.message = "Planning audio generation"
        all_tasks, plan_reporting_state = plan_audio_generation(
            dialogues=dialogues,
            tts_provider_manager=tts_manager,
            processor=processor,
            cache_folder=str(cache_folder),
            cache_overrides_dir=request.cache_overrides_dir,
        )

        # Merge planning report state into combined state
        combined_reporting_state.cache_misses.update(plan_reporting_state.cache_misses)

        # Store cache misses for API response (simplified format)
        task.cache_misses = [
            {"speaker": clip.speaker_display or "Unknown", "text": clip.text[:50]}
            for clip in plan_reporting_state.cache_misses.values()
        ]

        task.stats.total_clips = len(all_tasks)
        task.stats.cached_clips = sum(
            1 for t in all_tasks if t.cache_filepath and Path(t.cache_filepath).exists()
        )

        # Save processed dialogues JSON (like CLI does)
        modified_dialogues = [t.processed_dialogue for t in all_tasks]
        save_processed_dialogues(modified_dialogues, main_output_folder, base_name)

        task.phase_progress = 1.0

        # === PHASE 2: APPLY CACHE OVERRIDES ===
        if not is_dry_run and request.cache_overrides_dir:
            log_phase(logger, PipelinePhase.OVERRIDES)
            task.phase = AudiobookGenerationPhase.APPLYING_OVERRIDES
            task.phase_progress = 0.0
            task.message = "Applying cache overrides"

            apply_cache_overrides(
                tasks=all_tasks,
                cache_overrides_dir=request.cache_overrides_dir,
                cache_folder=str(cache_folder),
            )

            task.phase_progress = 1.0

        # === PHASE 3: CHECK FOR SILENCE ===
        if request.silence_threshold is not None:
            log_phase(logger, PipelinePhase.SILENCE)
            task.phase = AudiobookGenerationPhase.CHECKING_SILENCE
            task.phase_progress = 0.0
            task.message = "Checking for silent audio files"

            # Create tracker for GUI polling (snapshot-based)
            silence_tracker = SilenceCheckProgressTracker()
            task.set_silence_tracker(silence_tracker)

            silence_reporting_state = check_for_silence(
                tasks=all_tasks,
                silence_threshold=request.silence_threshold,
                progress_tracker=silence_tracker,
            )

            # Clear tracker reference after completion
            task.set_silence_tracker(None)

            # Merge silence report state into combined state
            combined_reporting_state.silent_clips.update(
                silence_reporting_state.silent_clips
            )

            # Store silent clips for API response (simplified format)
            task.silent_clips = [
                {"speaker": clip.speaker_display or "Unknown", "text": clip.text[:50]}
                for clip in silence_reporting_state.silent_clips.values()
            ]
            task.stats.silent_clips = len(task.silent_clips)

            task.phase_progress = 1.0

        # === PHASE 4: FETCH/GENERATE AUDIO ===
        if not is_dry_run:
            log_phase(logger, PipelinePhase.FETCH)
            task.phase = AudiobookGenerationPhase.GENERATING
            task.phase_progress = 0.0
            task.message = "Generating audio files"

            # Prepare tasks (same as fetch_and_cache_audio does internally)
            update_cache_duplicate_state(all_tasks)
            for t in all_tasks:
                if t.is_cache_hit:
                    t.status = CoreTaskStatus.CACHED
                elif t.expected_cache_duplicate:
                    t.status = CoreTaskStatus.SKIPPED_DUPLICATE
                else:
                    t.status = CoreTaskStatus.PENDING

            # Create download manager directly for progress polling (pull-based)
            download_manager = AudioDownloadManager(
                tasks=all_tasks,
                tts_provider_manager=tts_manager,
                global_max_workers=request.max_workers,
                initial_backoff_seconds=10.0,
                backoff_factor=2.0,
                max_retries=3,
                silence_threshold=request.silence_threshold,
            )

            # Set reference for progress polling (enables real-time stats)
            task.set_download_manager(download_manager)

            # Run generation (blocking)
            fetch_reporting_state = download_manager.run()

            # Clear reference after completion
            task.set_download_manager(None)

            # Merge fetch report state into combined state
            combined_reporting_state.silent_clips.update(
                fetch_reporting_state.silent_clips
            )

            # Update stats from fetch results
            task.stats.generated_clips = sum(
                1
                for t in all_tasks
                if t.cache_filepath and Path(t.cache_filepath).exists()
            )
            task.stats.failed_clips = sum(
                1
                for t in all_tasks
                if not t.cache_filepath or not Path(t.cache_filepath).exists()
            )

            # Merge any newly detected silent clips for API response
            for clip in fetch_reporting_state.silent_clips.values():
                speaker = clip.speaker_display or "Unknown"
                text = clip.text[:50]
                if (speaker, text) not in [
                    (s["speaker"], s["text"]) for s in task.silent_clips
                ]:
                    task.silent_clips.append({"speaker": speaker, "text": text})
                    task.stats.silent_clips = len(task.silent_clips)

            # Recheck file status after potential generation/overrides
            log_phase(logger, PipelinePhase.RECHECK)
            recheck_audio_files(
                combined_reporting_state,
                str(cache_folder),
                request.silence_threshold or -40.0,
                logger,
            )

            task.phase_progress = 1.0

        # === PHASE 5: CONCATENATE ===
        if not is_dry_run and not is_populate_cache:
            log_phase(logger, PipelinePhase.CONCAT)
            task.phase = AudiobookGenerationPhase.CONCATENATING
            task.phase_progress = 0.0
            task.message = "Concatenating audio files"

            # Create tracker for GUI polling (snapshot-based)
            concat_tracker = ConcatenationProgressTracker()
            task.set_concat_tracker(concat_tracker)

            concatenate_tasks_batched(
                tasks=all_tasks,
                output_file=str(output_file),
                batch_size=250,
                gap_duration_ms=request.gap_ms,
                progress_tracker=concat_tracker,
            )

            # Clear tracker reference after completion
            task.set_concat_tracker(None)

            # === PHASE 6: FINALIZE ===
            # (Ensure we're in FINALIZING phase - may have transitioned to EXPORTING during concat)
            task.phase = AudiobookGenerationPhase.FINALIZING
            task.phase_progress = 0.0
            task.message = "Setting ID3 tags"

            # Look for optional config
            optional_config_path = self._find_optional_config(request.input_json_path)
            if optional_config_path:
                set_id3_tags_from_config(str(output_file), optional_config_path)

            task.output_file = str(output_file)
            task.phase_progress = 1.0

        # === FINAL REPORT ===
        log_phase(logger, PipelinePhase.FINAL_REPORT)
        print_unified_report(
            reporting_state=combined_reporting_state,
            logger=logger,
            tts_provider_manager=tts_manager,
            silence_checking_enabled=request.silence_threshold is not None,
            max_misses_to_report=20,
            max_text_length=30,
        )

        # === CACHE SILENT CLIPS FOR REVIEW SERVICE ===
        # Populate in-memory cache so review page can read without re-scanning
        self._cache_silent_clips(
            project_name=request.project_name,
            reporting_state=combined_reporting_state,
            tts_manager=tts_manager,
            total_clips=len(all_tasks),
            cache_folder=cache_folder,
        )

        # === COMPLETION ===
        log_completion(
            logger,
            run_mode,
            log_file,
            cache_folder,
            output_file if not is_dry_run and not is_populate_cache else None,
        )

    def _find_optional_config(self, input_file_path: str) -> Optional[str]:
        """Find the optional config file for ID3 tags."""
        input_path = Path(input_file_path)
        base_name = input_path.stem
        default_config_path = input_path.parent / f"{base_name}_optional_config.yaml"

        if default_config_path.exists():
            return str(default_config_path)
        return None

    def _cache_silent_clips(
        self,
        project_name: str,
        reporting_state: ReportingState,
        tts_manager: TTSProviderManager,
        total_clips: int,
        cache_folder: Path,
    ) -> None:
        """Cache silent clips data for the review service.

        This populates an in-memory cache that the review service can read
        to avoid re-scanning audio files for silence.

        Args:
            project_name: Name of the project
            reporting_state: Combined reporting state with silent clips
            tts_manager: TTS provider manager for speaker config lookup
            total_clips: Total number of clips scanned
            cache_folder: Path to the cache folder
        """
        clips = []
        for filename, clip in reporting_state.silent_clips.items():
            # Get speaker config for regeneration
            speaker_key = clip.speaker or "default"
            try:
                speaker_config = tts_manager.get_speaker_configuration(speaker_key)
            except Exception as e:
                logger.warning(f"Could not get speaker config for '{speaker_key}': {e}")
                speaker_config = {}

            # Look up human-readable sts_id from voice library (for display purposes)
            # This is a reverse lookup from provider voice_id -> library sts_id
            sts_id = None
            provider_id = clip.provider_id or ""
            voice_id = clip.speaker_id or ""
            if provider_id and voice_id:
                try:
                    sts_id = tts_manager.get_library_sts_id_for_voice(provider_id, voice_id)
                except Exception as e:
                    logger.warning(f"Could not look up sts_id for '{provider_id}/{voice_id}': {e}")

            clips.append(
                ProblemClipInfo(
                    cache_filename=filename,
                    speaker=clip.speaker_display or "(default)",
                    voice_id=voice_id,
                    provider=provider_id,
                    text=clip.text,
                    dbfs_level=clip.dbfs_level,
                    speaker_config=speaker_config,
                    sts_id=sts_id,
                )
            )

        self._silent_clips_cache[project_name] = SilentClipsResponse(
            silent_clips=clips,
            total_clips_scanned=total_clips,
            cache_folder=str(cache_folder),
            scanned_at=datetime.now(timezone.utc).isoformat(),
        )
        logger.info(f"Cached {len(clips)} silent clips for project '{project_name}'")


# Global service instance
audiobook_generation_service = AudiobookGenerationService()
