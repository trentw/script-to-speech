"""Tests for the chunk inventory service.

Covers inventory computation (entries, statuses, user-modified flags,
shared-audio occurrences, per-speaker configs) and the explicit
cache/invalidate lifecycle. Planning itself is mocked; it is covered by
tests/audio_generation/.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from script_to_speech.audio_generation.models import AudioGenerationTask
from script_to_speech.gui_backend.services.chunk_inventory_service import (
    ChunkInventoryService,
)

CACHE_FOLDER = "/tmp/cache"


def _make_task(
    idx,
    text,
    speaker=None,
    cache_filename="",
    is_cache_hit=False,
    user_modified_flag=None,
    expected_silence=False,
):
    return AudioGenerationTask(
        idx=idx,
        original_dialogue={"type": "dialogue", "speaker": speaker or "", "text": text},
        processed_dialogue={
            "type": "dialogue",
            "speaker": speaker or "",
            "text": text.upper(),
        },
        text_to_speak=text.upper(),
        speaker=speaker,
        provider_id="openai",
        speaker_id="nova_tts-1",
        speaker_display=speaker or "(default)",
        cache_filename=cache_filename,
        cache_filepath=os.path.join(CACHE_FOLDER, cache_filename),
        is_cache_hit=is_cache_hit,
        user_modified_flag=user_modified_flag,
        expected_silence=expected_silence,
    )


@pytest.fixture
def mock_context():
    """Patch project loading and planning in the service module namespace."""
    tts_manager = MagicMock()
    tts_manager.get_speaker_configuration.return_value = {
        "provider": "openai",
        "voice": "nova",
    }
    tts_manager.get_library_sts_id_for_voice.return_value = "sarah"

    tasks = [
        _make_task(
            0,
            "Hello",
            speaker="JOHN",
            cache_filename="h1~~h2~~openai~~nova_tts-1.mp3",
            is_cache_hit=True,
        ),
        _make_task(
            1,
            "Goodbye",
            speaker="JOHN",
            cache_filename="h3~~h4~~openai~~nova_tts-1~~edit.mp3",
            is_cache_hit=True,
            user_modified_flag="edit",
        ),
        # Shares the same cache file as task 0 (identical text+speaker)
        _make_task(
            2,
            "Hello",
            speaker="JOHN",
            cache_filename="h1~~h2~~openai~~nova_tts-1.mp3",
            is_cache_hit=True,
        ),
        _make_task(
            3,
            "Never generated",
            cache_filename="h5~~h6~~openai~~nova_tts-1.mp3",
            is_cache_hit=False,
        ),
        _make_task(
            4,
            "",
            cache_filename="h7~~h8~~openai~~nova_tts-1.mp3",
            expected_silence=True,
        ),
    ]

    # Planning sets processor.preprocessed_chunks; the revision hashes that
    # full list (not the tasks, which may have dropped chunks)
    processor = MagicMock()
    processor.preprocessed_chunks = [task.original_dialogue for task in tasks]

    with (
        patch(
            "script_to_speech.gui_backend.services.chunk_inventory_service.load_project_analysis_context"
        ) as mock_load,
        patch(
            "script_to_speech.gui_backend.services.chunk_inventory_service.plan_audio_generation"
        ) as mock_plan,
    ):
        mock_load.return_value = ([], tts_manager, processor, CACHE_FOLDER)
        mock_plan.return_value = (tasks, MagicMock())
        yield mock_load, mock_plan


class TestChunkInventoryComputation:
    """Tests for inventory content."""

    def test_entries_statuses_and_flags(self, mock_context):
        service = ChunkInventoryService()
        inventory = service.get_inventory("proj")

        assert inventory.project_name == "proj"
        assert inventory.total_chunks == 5
        assert [e.status for e in inventory.entries] == [
            "cached",
            "cached",
            "cached",
            "missing",
            "expected_silence",
        ]
        assert inventory.entries[1].user_modified == "edit"
        assert inventory.entries[0].user_modified is None
        assert inventory.cached_count == 3
        assert inventory.missing_count == 1
        assert inventory.user_modified_count == 1
        assert len(inventory.chunk_layout_revision) == 64

    def test_occurrences_group_shared_audio(self, mock_context):
        service = ChunkInventoryService()
        inventory = service.get_inventory("proj")

        # Tasks 0 and 2 share one cache file
        assert inventory.entries[0].occurrences == [0, 2]
        assert inventory.entries[2].occurrences == [0, 2]
        assert inventory.entries[1].occurrences == [1]

    def test_texts_and_filenames(self, mock_context):
        service = ChunkInventoryService()
        inventory = service.get_inventory("proj")

        assert inventory.entries[0].original_text == "Hello"
        assert inventory.entries[0].processed_text == "HELLO"
        assert (
            inventory.entries[1].cache_filename
            == "h3~~h4~~openai~~nova_tts-1~~edit.mp3"
        )

    def test_speaker_configs_one_per_speaker(self, mock_context):
        service = ChunkInventoryService()
        inventory = service.get_inventory("proj")

        # Two distinct speaker keys: "JOHN" and default (None)
        assert set(inventory.speaker_configs.keys()) == {"JOHN", "default"}
        john = inventory.speaker_configs["JOHN"]
        assert john.provider == "openai"
        assert john.voice_id == "nova_tts-1"
        assert john.speaker_config == {"provider": "openai", "voice": "nova"}
        assert john.sts_id == "sarah"

    def test_revision_hashes_full_list_when_planning_drops_a_chunk(self):
        """Planning silently drops chunks whose planning raises. The revision
        must still hash the full preprocessed list so it always agrees with
        the PDF-anchor service's hash (else the frontend sees permanent skew).
        """
        from script_to_speech.gui_backend.services.project_analysis_cache import (
            compute_chunk_layout_revision,
        )

        chunks = [
            {"type": "dialogue", "speaker": "JOHN", "text": f"Line {i}"}
            for i in range(3)
        ]
        processor = MagicMock()
        processor.preprocessed_chunks = chunks
        tts_manager = MagicMock()
        tts_manager.get_speaker_configuration.return_value = {}
        tts_manager.get_library_sts_id_for_voice.return_value = None
        # Chunk 1 failed planning: only tasks 0 and 2 exist
        tasks = [_make_task(0, "Line 0"), _make_task(2, "Line 2")]

        with (
            patch(
                "script_to_speech.gui_backend.services.chunk_inventory_service.load_project_analysis_context"
            ) as mock_load,
            patch(
                "script_to_speech.gui_backend.services.chunk_inventory_service.plan_audio_generation"
            ) as mock_plan,
        ):
            mock_load.return_value = ([], tts_manager, processor, CACHE_FOLDER)
            mock_plan.return_value = (tasks, MagicMock())
            inventory = ChunkInventoryService().get_inventory("proj")

        assert inventory.chunk_layout_revision == compute_chunk_layout_revision(chunks)


class TestChunkInventoryCache:
    """Tests for the explicit cache/invalidate lifecycle."""

    def test_second_call_uses_cache(self, mock_context):
        _, mock_plan = mock_context
        service = ChunkInventoryService()

        first = service.get_inventory("proj")
        second = service.get_inventory("proj")

        assert mock_plan.call_count == 1
        assert second is first

    def test_refresh_bypasses_cache(self, mock_context):
        _, mock_plan = mock_context
        service = ChunkInventoryService()

        service.get_inventory("proj")
        service.get_inventory("proj", refresh=True)

        assert mock_plan.call_count == 2

    def test_invalidate_project(self, mock_context):
        _, mock_plan = mock_context
        service = ChunkInventoryService()

        service.get_inventory("proj")
        service.invalidate("proj")
        service.get_inventory("proj")

        assert mock_plan.call_count == 2

    def test_invalidate_all(self, mock_context):
        _, mock_plan = mock_context
        service = ChunkInventoryService()

        service.get_inventory("proj")
        service.invalidate()
        service.get_inventory("proj")

        assert mock_plan.call_count == 2

    def test_invalidate_other_project_keeps_cache(self, mock_context):
        _, mock_plan = mock_context
        service = ChunkInventoryService()

        service.get_inventory("proj")
        service.invalidate("other")
        service.get_inventory("proj")

        assert mock_plan.call_count == 1
