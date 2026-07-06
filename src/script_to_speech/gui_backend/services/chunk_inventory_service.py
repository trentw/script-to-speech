"""Service for computing the chunk inventory of a project.

The inventory maps every post-preprocessed screenplay chunk to its
audio-cache state: resolved cache filename, cached/missing status,
user-modified flag, and which other chunks share the same audio file.

Everything is recomputed from the on-disk sources of truth by running the
same planning phase the generation pipeline uses (``plan_audio_generation``).
Results are cached in memory per project and deliberately cleared on
mutations (variant commit, re-parse, config changes) rather than kept in
sync.
"""

import logging
import threading
from datetime import datetime, timezone
from typing import Dict, List, Literal, Optional

from script_to_speech.audio_generation.processing import plan_audio_generation

from ..models import ChunkInventoryEntry, ChunkInventoryResponse, ChunkSpeakerConfig
from .project_loader import load_project_analysis_context

logger = logging.getLogger(__name__)


class ChunkInventoryService:
    """Service for computing and caching per-project chunk inventories."""

    def __init__(self) -> None:
        self._cache: Dict[str, ChunkInventoryResponse] = {}
        self._lock = threading.Lock()

    def get_inventory(
        self, project_name: str, refresh: bool = False
    ) -> ChunkInventoryResponse:
        """Get the chunk inventory for a project.

        Args:
            project_name: Name of the project
            refresh: When True, bypass the in-memory cache and recompute

        Returns:
            ChunkInventoryResponse for the project
        """
        if not refresh:
            with self._lock:
                cached = self._cache.get(project_name)
            if cached is not None:
                logger.info(f"Returning cached chunk inventory for '{project_name}'")
                return cached

        inventory = self._compute_inventory(project_name)
        with self._lock:
            self._cache[project_name] = inventory
        return inventory

    def invalidate(self, project_name: Optional[str] = None) -> None:
        """Drop cached inventories so the next request recomputes from disk.

        Args:
            project_name: Project to invalidate, or None for all projects
        """
        with self._lock:
            if project_name is None:
                self._cache.clear()
            else:
                self._cache.pop(project_name, None)
        logger.info(f"Invalidated chunk inventory cache for: {project_name or 'all'}")

    def _compute_inventory(self, project_name: str) -> ChunkInventoryResponse:
        """Compute the inventory by running the planning phase."""
        logger.info(f"Computing chunk inventory for project: {project_name}")

        dialogues, tts_manager, processor, cache_folder = load_project_analysis_context(
            project_name
        )

        tasks, _ = plan_audio_generation(
            dialogues=dialogues,
            tts_provider_manager=tts_manager,
            processor=processor,
            cache_folder=str(cache_folder),
            cache_overrides_dir=None,
        )

        # Identical text+speaker chunks share one cache file; group task idxs
        # by cache filepath so every entry knows its co-owners.
        occurrences: Dict[str, List[int]] = {}
        for task in tasks:
            occurrences.setdefault(task.cache_filepath, []).append(task.idx)

        # One config lookup per distinct speaker (not per chunk)
        speaker_configs: Dict[str, ChunkSpeakerConfig] = {}
        for task in tasks:
            speaker_key = task.speaker or "default"
            if speaker_key in speaker_configs:
                continue
            config: Dict = {}
            try:
                config = tts_manager.get_speaker_configuration(speaker_key)
            except Exception as e:
                logger.warning(f"Could not get speaker config for '{speaker_key}': {e}")
            provider_id = task.provider_id or ""
            voice_id = task.speaker_id or ""
            sts_id = None
            if provider_id and voice_id:
                sts_id = tts_manager.get_library_sts_id_for_voice(provider_id, voice_id)
            speaker_configs[speaker_key] = ChunkSpeakerConfig(
                provider=provider_id,
                voice_id=voice_id,
                speaker_config=config,
                sts_id=sts_id,
            )

        entries: List[ChunkInventoryEntry] = []
        for task in tasks:
            status: Literal["cached", "missing", "expected_silence"]
            if task.expected_silence:
                status = "expected_silence"
            elif task.is_cache_hit:
                status = "cached"
            else:
                status = "missing"
            entries.append(
                ChunkInventoryEntry(
                    idx=task.idx,
                    chunk_type=task.processed_dialogue.get("type", ""),
                    speaker=task.speaker,
                    speaker_display=task.speaker_display,
                    original_text=task.original_dialogue.get("text", ""),
                    processed_text=task.text_to_speak,
                    cache_filename=task.cache_filename,
                    status=status,
                    user_modified=task.user_modified_flag,
                    occurrences=occurrences[task.cache_filepath],
                )
            )

        cached_count = sum(1 for e in entries if e.status == "cached")
        missing_count = sum(1 for e in entries if e.status == "missing")
        user_modified_count = sum(1 for e in entries if e.user_modified is not None)

        logger.info(
            f"Chunk inventory for '{project_name}': {len(entries)} chunks, "
            f"{cached_count} cached ({user_modified_count} user-modified), "
            f"{missing_count} missing"
        )

        return ChunkInventoryResponse(
            project_name=project_name,
            entries=entries,
            speaker_configs=speaker_configs,
            total_chunks=len(entries),
            cached_count=cached_count,
            missing_count=missing_count,
            user_modified_count=user_modified_count,
            cache_folder=str(cache_folder),
            generated_at=datetime.now(timezone.utc).isoformat(),
        )


# Singleton instance
chunk_inventory_service = ChunkInventoryService()
