"""Tests for the shared project-analysis invalidation helper.

Router/service tests patch ``invalidate_project_analysis`` itself, so this is
the one place that proves the helper really drops BOTH derived snapshots
(chunk inventory and PDF anchors) — the property that keeps their idxs from
drifting apart after a mutation.
"""

from unittest.mock import patch

from script_to_speech.gui_backend.services.project_analysis_cache import (
    compute_chunk_layout_revision,
    invalidate_project_analysis,
)


class TestChunkLayoutRevision:
    def test_is_stable_for_equivalent_chunks(self):
        chunks = [
            {
                "type": "dialogue",
                "speaker": "JOHN",
                "text": "Hello",
                "raw_text": "Hello",
                "unrelated_metadata": 1,
            }
        ]

        first = compute_chunk_layout_revision(chunks)
        second = compute_chunk_layout_revision([dict(chunks[0])])

        assert first == second
        assert len(first) == 64

    def test_changes_for_order_and_pdf_relevant_fields(self):
        first = {
            "type": "dialogue",
            "speaker": "JOHN",
            "text": "Hello",
            "raw_text": "Hello",
        }
        second = {
            "type": "action",
            "speaker": None,
            "text": "He leaves.",
            "raw_text": "He leaves.",
        }
        baseline = compute_chunk_layout_revision([first, second])

        assert compute_chunk_layout_revision([second, first]) != baseline
        assert (
            compute_chunk_layout_revision([{**first, "raw_text": "HELLO"}, second])
            != baseline
        )
        assert (
            compute_chunk_layout_revision(
                [{**first, "type": "dialogue_modifier"}, second]
            )
            != baseline
        )


class TestInvalidateProjectAnalysis:
    def test_fans_out_to_both_caches_for_one_project(self):
        with (
            patch(
                "script_to_speech.gui_backend.services.chunk_inventory_service.chunk_inventory_service.invalidate"
            ) as mock_inventory,
            patch(
                "script_to_speech.gui_backend.services.pdf_anchor_service.pdf_anchor_service.invalidate"
            ) as mock_anchors,
        ):
            invalidate_project_analysis("proj")

        mock_inventory.assert_called_once_with("proj")
        mock_anchors.assert_called_once_with("proj")

    def test_none_invalidates_all_projects_in_both_caches(self):
        with (
            patch(
                "script_to_speech.gui_backend.services.chunk_inventory_service.chunk_inventory_service.invalidate"
            ) as mock_inventory,
            patch(
                "script_to_speech.gui_backend.services.pdf_anchor_service.pdf_anchor_service.invalidate"
            ) as mock_anchors,
        ):
            invalidate_project_analysis()

        mock_inventory.assert_called_once_with(None)
        mock_anchors.assert_called_once_with(None)
