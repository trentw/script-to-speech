"""Tests for ReviewService.commit_variant with the user-modified convention.

Variants carry their provenance ("retake"/"edit") as a filename token set at
generation time; commit maps it to the matching cache flavor and removes
superseded siblings. Untagged variants commit to the plain name (fix
forward only).
"""

from unittest.mock import patch

import pytest

from script_to_speech.gui_backend.config import settings
from script_to_speech.gui_backend.services.review_service import ReviewService

PLAIN = "a" * 32 + "~~" + "b" * 32 + "~~openai~~nova_tts-1.mp3"
EDIT = "a" * 32 + "~~" + "b" * 32 + "~~openai~~nova_tts-1~~edit.mp3"
RETAKE = "a" * 32 + "~~" + "b" * 32 + "~~openai~~nova_tts-1~~retake.mp3"

UNTAGGED_VARIANT = "openai--nova_tts-1--Hello_world--20260101_120000.mp3"
EDIT_VARIANT = "openai--nova_tts-1--Hello_world--20260101_120000--edit.mp3"
RETAKE_VARIANT = "openai--nova_tts-1--Hello_world--20260101_120000--retake.mp3"


@pytest.fixture
def review_env(tmp_path):
    """ReviewService against a temp workspace, with inventory invalidation mocked."""
    standalone_dir = tmp_path / "standalone_speech"
    standalone_dir.mkdir()
    cache_folder = tmp_path / "output" / "proj" / "cache"
    cache_folder.mkdir(parents=True)

    with (
        # AUDIO_OUTPUT_DIR is derived from WORKSPACE_DIR (a property), so
        # patching the workspace root redirects both.
        patch.object(settings, "WORKSPACE_DIR", tmp_path),
        patch(
            "script_to_speech.gui_backend.services.chunk_inventory_service.chunk_inventory_service"
        ) as mock_inventory,
    ):
        service = ReviewService()
        yield service, standalone_dir, cache_folder, mock_inventory


class TestCommitVariant:
    """Tests for commit_variant."""

    def test_untagged_variant_commits_to_plain_name(self, review_env):
        service, standalone_dir, cache_folder, mock_inventory = review_env
        (standalone_dir / UNTAGGED_VARIANT).write_bytes(b"audio")

        success, target_path, message = service.commit_variant(
            UNTAGGED_VARIANT, PLAIN, "proj"
        )

        assert success is True
        assert target_path == str(cache_folder / PLAIN)
        assert (cache_folder / PLAIN).read_bytes() == b"audio"
        mock_inventory.invalidate.assert_called_once_with("proj")

    def test_edit_variant_commits_to_edit_flavor(self, review_env):
        service, standalone_dir, cache_folder, _ = review_env
        (standalone_dir / EDIT_VARIANT).write_bytes(b"edited audio")

        success, target_path, _ = service.commit_variant(EDIT_VARIANT, PLAIN, "proj")

        assert success is True
        assert target_path == str(cache_folder / EDIT)
        assert (cache_folder / EDIT).read_bytes() == b"edited audio"
        assert not (cache_folder / PLAIN).exists()

    def test_take_variant_commits_to_take_flavor(self, review_env):
        service, standalone_dir, cache_folder, _ = review_env
        (standalone_dir / RETAKE_VARIANT).write_bytes(b"take audio")

        success, target_path, _ = service.commit_variant(RETAKE_VARIANT, PLAIN, "proj")

        assert success is True
        assert target_path == str(cache_folder / RETAKE)
        assert (cache_folder / RETAKE).read_bytes() == b"take audio"

    def test_commit_removes_superseded_siblings(self, review_env):
        service, standalone_dir, cache_folder, _ = review_env
        # Pre-existing plain and take flavors
        (cache_folder / PLAIN).write_bytes(b"old plain")
        (cache_folder / RETAKE).write_bytes(b"old take")
        (standalone_dir / EDIT_VARIANT).write_bytes(b"new edit")

        success, _, _ = service.commit_variant(EDIT_VARIANT, PLAIN, "proj")

        assert success is True
        assert (cache_folder / EDIT).read_bytes() == b"new edit"
        assert not (cache_folder / PLAIN).exists()
        assert not (cache_folder / RETAKE).exists()

    def test_flagged_target_filename_is_normalized_to_base(self, review_env):
        """Clients may pass a flagged name (from a resolved clip); commit
        strips it to the base before applying the variant's own flavor."""
        service, standalone_dir, cache_folder, _ = review_env
        (cache_folder / EDIT).write_bytes(b"old edit")
        (standalone_dir / RETAKE_VARIANT).write_bytes(b"new take")

        success, target_path, _ = service.commit_variant(RETAKE_VARIANT, EDIT, "proj")

        assert success is True
        assert target_path == str(cache_folder / RETAKE)
        assert not (cache_folder / EDIT).exists()

    def test_untagged_commit_supersedes_flagged_siblings(self, review_env):
        service, standalone_dir, cache_folder, _ = review_env
        (cache_folder / EDIT).write_bytes(b"old edit")
        (standalone_dir / UNTAGGED_VARIANT).write_bytes(b"fresh audio")

        success, target_path, _ = service.commit_variant(
            UNTAGGED_VARIANT, PLAIN, "proj"
        )

        assert success is True
        assert target_path == str(cache_folder / PLAIN)
        assert not (cache_folder / EDIT).exists()

    def test_missing_source_fails(self, review_env):
        service, _, _, mock_inventory = review_env

        success, target_path, message = service.commit_variant(
            "nonexistent.mp3", PLAIN, "proj"
        )

        assert success is False
        assert "not found" in message
        mock_inventory.invalidate.assert_not_called()

    def test_invalid_target_filename_fails(self, review_env):
        service, standalone_dir, _, _ = review_env
        (standalone_dir / UNTAGGED_VARIANT).write_bytes(b"audio")

        success, _, message = service.commit_variant(
            UNTAGGED_VARIANT, "not-a-cache-name.mp3", "proj"
        )

        assert success is False
        assert "Invalid target cache filename" in message
