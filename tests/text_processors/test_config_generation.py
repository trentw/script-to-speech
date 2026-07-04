"""Unit tests for text_processors.config_generation (seeded config files)."""

from pathlib import Path
from unittest.mock import mock_open, patch

import pytest
import yaml

from script_to_speech._version import __version__
from script_to_speech.text_processors import config_generation
from script_to_speech.text_processors.config_generation import (
    MODE_STANDALONE,
    SEEDED_FROM_SHIPPED,
    SEEDED_FROM_USER,
    USER_DEFAULT_CONFIG_PATH,
    build_seeded_config_text,
    compute_pipeline_hash,
    generate_text_processor_config,
    get_text_processor_config_path,
    is_config_stale,
)
from script_to_speech.text_processors.utils import DEFAULT_TEXT_PROCESSOR_CONFIG

SHIPPED_YAML = """\
preprocessors:
  - name: skip_and_merge
    config:
      skip_types:
        - page_number

processors:
  # Blank out page numbers so they are not read aloud
  - name: skip_empty
    config:
      skip_types:
        - page_number
"""

USER_DEFAULT_YAML = """\
sts_metadata:
  mode: user_default
  seeded_by_version: 2.0.0
  default_config_sha256: carried123
preprocessors:
  - name: skip_and_merge
    config:
      skip_types:
        - page_number
processors: []
"""


def _open_router(path_contents, written):
    """Build a builtins.open side effect serving per-path content and capturing writes.

    Args:
        path_contents: Dict of str(path) -> file content for reads
        written: Dict that will collect str(path) -> written text
    """

    def _side_effect(path, mode="r", *args, **kwargs):
        path_str = str(path)
        if "w" in mode:
            handle = mock_open()()
            original_write = handle.write

            def _capture(text, _path=path_str):
                written[_path] = written.get(_path, "") + text
                return original_write(text)

            handle.write = _capture
            return handle
        if path_str in path_contents:
            return mock_open(read_data=path_contents[path_str])()
        raise FileNotFoundError(path_str)

    return _side_effect


class TestComputePipelineHash:
    """Tests for the compute_pipeline_hash function."""

    def test_hash_ignores_non_pipeline_keys(self):
        """Only preprocessors/processors sections contribute to the hash."""
        pipeline = {"preprocessors": [{"name": "dual_dialogue"}], "processors": []}
        with_metadata = {**pipeline, "sts_metadata": {"mode": "standalone"}}

        assert compute_pipeline_hash(pipeline) == compute_pipeline_hash(with_metadata)

    def test_hash_changes_with_pipeline_content(self):
        """Changing the pipeline changes the hash."""
        config_a = {"processors": [{"name": "skip_empty"}]}
        config_b = {"processors": [{"name": "text_substitution"}]}

        assert compute_pipeline_hash(config_a) != compute_pipeline_hash(config_b)

    def test_hash_of_none_is_stable(self):
        """A missing config hashes consistently."""
        assert compute_pipeline_hash(None) == compute_pipeline_hash({})

    def test_hash_ignores_notes(self):
        """Documentary `notes` keys must not affect the pipeline hash."""
        without_notes = {
            "processors": [
                {
                    "name": "pattern_replace",
                    "config": {
                        "replacements": [{"match_field": "type", "match_pattern": "x"}]
                    },
                }
            ]
        }
        with_notes = {
            "processors": [
                {
                    "name": "pattern_replace",
                    "config": {
                        "replacements": [
                            {
                                "match_field": "type",
                                "match_pattern": "x",
                                "notes": "explanatory text that should be ignored",
                            }
                        ]
                    },
                    "notes": "top-level note",
                }
            ]
        }

        assert compute_pipeline_hash(without_notes) == compute_pipeline_hash(with_notes)


class TestIsConfigStale:
    """Tests for the is_config_stale function."""

    def test_matching_hash_is_not_stale(self):
        """A config recording the current default hash is fresh."""
        config = {"sts_metadata": {"default_config_sha256": "abc"}}

        with patch.object(
            config_generation, "get_current_default_hash", return_value="abc"
        ):
            assert is_config_stale(config) is False

    def test_differing_hash_is_stale(self):
        """A config recording an old default hash is stale."""
        config = {"sts_metadata": {"default_config_sha256": "old"}}

        with patch.object(
            config_generation, "get_current_default_hash", return_value="new"
        ):
            assert is_config_stale(config) is True

    def test_config_without_metadata_is_not_stale(self):
        """Configs without provenance metadata are never flagged stale."""
        assert is_config_stale({"processors": []}) is False

    def test_metadata_without_hash_is_not_stale(self):
        """Metadata without a recorded hash is never flagged stale."""
        assert is_config_stale({"sts_metadata": {"mode": "standalone"}}) is False

    def test_non_mapping_config_is_not_stale(self):
        """Non-mapping configs are never flagged stale."""
        assert is_config_stale(None) is False


class TestGetTextProcessorConfigPath:
    """Tests for the get_text_processor_config_path function."""

    def test_path_derivation(self):
        """The config path is a sibling of the JSON file."""
        result = get_text_processor_config_path("/input/script/my_script.json")

        assert result == str(Path("/input/script/my_script_text_processor_config.yaml"))


class TestBuildSeededConfigText:
    """Tests for the build_seeded_config_text function."""

    def test_metadata_inserted_first_with_header(self):
        """The seeded config starts with a header comment and sts_metadata."""
        metadata = {"mode": MODE_STANDALONE, "seeded_from": SEEDED_FROM_SHIPPED}

        result = build_seeded_config_text(SHIPPED_YAML, metadata)

        lines = result.splitlines()
        assert lines[0].startswith("# Text processor configuration")
        data = yaml.safe_load(result)
        assert list(data.keys())[0] == "sts_metadata"
        assert data["sts_metadata"]["mode"] == MODE_STANDALONE

    def test_source_comments_preserved(self):
        """Inline comments from the source config survive seeding."""
        result = build_seeded_config_text(SHIPPED_YAML, {"mode": MODE_STANDALONE})

        assert "# Blank out page numbers so they are not read aloud" in result

    def test_pipeline_content_preserved(self):
        """The seeded pipeline is semantically identical to the source."""
        result = build_seeded_config_text(SHIPPED_YAML, {"mode": MODE_STANDALONE})

        assert compute_pipeline_hash(yaml.safe_load(result)) == compute_pipeline_hash(
            yaml.safe_load(SHIPPED_YAML)
        )

    def test_existing_metadata_replaced(self):
        """An sts_metadata block in the source is replaced, not duplicated."""
        metadata = {"mode": MODE_STANDALONE, "seeded_from": SEEDED_FROM_USER}

        result = build_seeded_config_text(USER_DEFAULT_YAML, metadata)

        data = yaml.safe_load(result)
        assert data["sts_metadata"] == metadata

    def test_non_mapping_source_raises(self):
        """A source that is not a YAML mapping is rejected."""
        with pytest.raises(ValueError):
            build_seeded_config_text("- just\n- a list\n", {"mode": MODE_STANDALONE})


class TestGenerateTextProcessorConfig:
    """Tests for the generate_text_processor_config function."""

    def test_existing_config_not_overwritten(self):
        """An existing config file is returned untouched."""
        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open") as mock_file_open,
        ):
            result = generate_text_processor_config("/input/script/my_script.json")

        assert result == str(Path("/input/script/my_script_text_processor_config.yaml"))
        mock_file_open.assert_not_called()

    def test_seeds_from_shipped_default(self):
        """Without a user default, the shipped default seeds the config."""
        written = {}
        contents = {str(DEFAULT_TEXT_PROCESSOR_CONFIG): SHIPPED_YAML}

        with (
            patch("os.path.exists", return_value=False),
            patch("builtins.open", side_effect=_open_router(contents, written)),
        ):
            result = generate_text_processor_config("/input/script/my_script.json")

        config_path = str(Path("/input/script/my_script_text_processor_config.yaml"))
        assert result == config_path
        data = yaml.safe_load(written[config_path])
        assert data["sts_metadata"]["mode"] == MODE_STANDALONE
        assert data["sts_metadata"]["seeded_from"] == SEEDED_FROM_SHIPPED
        assert data["sts_metadata"]["seeded_by_version"] == __version__
        assert data["sts_metadata"]["default_config_sha256"] == compute_pipeline_hash(
            yaml.safe_load(SHIPPED_YAML)
        )
        # Comments from the shipped default survive
        assert "# Blank out page numbers" in written[config_path]

    def test_seeds_from_user_default_with_carried_hash(self):
        """A user default seeds the config, carrying its recorded default hash."""
        written = {}
        contents = {str(USER_DEFAULT_CONFIG_PATH): USER_DEFAULT_YAML}

        def _exists(path):
            return str(path) == str(USER_DEFAULT_CONFIG_PATH)

        with (
            patch("os.path.exists", side_effect=_exists),
            patch("builtins.open", side_effect=_open_router(contents, written)),
        ):
            result = generate_text_processor_config("/input/script/my_script.json")

        config_path = str(Path("/input/script/my_script_text_processor_config.yaml"))
        data = yaml.safe_load(written[config_path])
        assert data["sts_metadata"]["mode"] == MODE_STANDALONE
        assert data["sts_metadata"]["seeded_from"] == SEEDED_FROM_USER
        assert data["sts_metadata"]["default_config_sha256"] == "carried123"
        # Pipeline content comes from the user default
        assert data["processors"] == []

    def test_unreadable_user_default_falls_back_to_shipped(self):
        """An unparseable user default falls back to the shipped default."""
        written = {}
        contents = {
            str(USER_DEFAULT_CONFIG_PATH): "foo: [unclosed",
            str(DEFAULT_TEXT_PROCESSOR_CONFIG): SHIPPED_YAML,
        }

        def _exists(path):
            return str(path) == str(USER_DEFAULT_CONFIG_PATH)

        with (
            patch("os.path.exists", side_effect=_exists),
            patch("builtins.open", side_effect=_open_router(contents, written)),
        ):
            generate_text_processor_config("/input/script/my_script.json")

        config_path = str(Path("/input/script/my_script_text_processor_config.yaml"))
        data = yaml.safe_load(written[config_path])
        assert data["sts_metadata"]["seeded_from"] == SEEDED_FROM_SHIPPED
