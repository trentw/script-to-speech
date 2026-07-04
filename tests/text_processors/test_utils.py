"""Unit tests for text_processors.utils (config path resolution)."""

from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from script_to_speech.text_processors.utils import (
    DEFAULT_TEXT_PROCESSOR_CONFIG,
    get_text_processor_configs,
    is_standalone_config,
)

STANDALONE_YAML = """
sts_metadata:
  mode: standalone
  seeded_from: shipped_default
processors:
  - name: skip_empty
    config:
      skip_types:
        - page_number
"""

LEGACY_YAML = """
processors:
  - name: skip_empty
    config:
      skip_types:
        - page_number
"""


class TestIsStandaloneConfig:
    """Tests for the is_standalone_config function."""

    def test_standalone_marker_detected(self):
        """A config with sts_metadata.mode == standalone is standalone."""
        with patch("builtins.open", mock_open(read_data=STANDALONE_YAML)):
            assert is_standalone_config(Path("/fake/config.yaml")) is True

    def test_config_without_metadata_is_not_standalone(self):
        """A legacy config with no sts_metadata block is not standalone."""
        with patch("builtins.open", mock_open(read_data=LEGACY_YAML)):
            assert is_standalone_config(Path("/fake/config.yaml")) is False

    def test_metadata_with_other_mode_is_not_standalone(self):
        """A config with a different sts_metadata.mode is not standalone."""
        yaml_content = "sts_metadata:\n  mode: user_default\nprocessors: []\n"
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            assert is_standalone_config(Path("/fake/config.yaml")) is False

    def test_metadata_not_a_mapping_is_not_standalone(self):
        """A config whose sts_metadata is not a mapping is not standalone."""
        yaml_content = "sts_metadata: standalone\nprocessors: []\n"
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            assert is_standalone_config(Path("/fake/config.yaml")) is False

    def test_non_mapping_config_is_not_standalone(self):
        """A config that is not a YAML mapping is not standalone."""
        with patch("builtins.open", mock_open(read_data="- just\n- a\n- list\n")):
            assert is_standalone_config(Path("/fake/config.yaml")) is False

    def test_unreadable_file_is_not_standalone(self):
        """A file that cannot be read is treated as legacy (not standalone)."""
        with patch("builtins.open", side_effect=OSError("cannot read")):
            assert is_standalone_config(Path("/fake/config.yaml")) is False

    def test_malformed_yaml_is_not_standalone(self):
        """A file with invalid YAML is treated as legacy (not standalone)."""
        with patch("builtins.open", mock_open(read_data="foo: [unclosed")):
            assert is_standalone_config(Path("/fake/config.yaml")) is False


class TestGetTextProcessorConfigs:
    """Tests for the get_text_processor_configs function."""

    def test_command_line_configs_used_exclusively(self):
        """Command line configs are returned as-is, replacing everything else."""
        cmd_configs = [Path("/custom/one.yaml"), Path("/custom/two.yaml")]

        result = get_text_processor_configs(
            chunk_file_path=Path("/input/script/script.json"),
            cmd_line_configs=cmd_configs,
        )

        assert result == cmd_configs

    def test_no_chunk_file_returns_default_only(self):
        """With no chunk file path, only the default config is used."""
        result = get_text_processor_configs()

        assert result == [DEFAULT_TEXT_PROCESSOR_CONFIG]

    def test_no_sibling_config_returns_default_only(self):
        """With no matching sibling config file, only the default is used."""
        with patch.object(Path, "exists", return_value=False):
            result = get_text_processor_configs(
                chunk_file_path=Path("/input/script/script.json")
            )

        assert result == [DEFAULT_TEXT_PROCESSOR_CONFIG]

    def test_standalone_sibling_config_replaces_default(self):
        """A standalone sibling config is used as a complete replacement."""
        chunk_path = Path("/input/script/script.json")
        expected_config = Path("/input/script/script_text_processor_config.yaml")

        with (
            patch.object(Path, "exists", return_value=True),
            patch("builtins.open", mock_open(read_data=STANDALONE_YAML)),
        ):
            result = get_text_processor_configs(chunk_file_path=chunk_path)

        assert result == [expected_config]

    def test_legacy_sibling_config_chains_after_default(self):
        """A legacy (unmarked) sibling config chains after the default."""
        chunk_path = Path("/input/script/script.json")
        expected_config = Path("/input/script/script_text_processor_config.yaml")

        with (
            patch.object(Path, "exists", return_value=True),
            patch("builtins.open", mock_open(read_data=LEGACY_YAML)),
        ):
            result = get_text_processor_configs(chunk_file_path=chunk_path)

        assert result == [DEFAULT_TEXT_PROCESSOR_CONFIG, expected_config]

    def test_malformed_sibling_config_chains_after_default(self):
        """A sibling config that fails to parse falls back to legacy chaining."""
        chunk_path = Path("/input/script/script.json")
        expected_config = Path("/input/script/script_text_processor_config.yaml")

        with (
            patch.object(Path, "exists", return_value=True),
            patch("builtins.open", mock_open(read_data="foo: [unclosed")),
        ):
            result = get_text_processor_configs(chunk_file_path=chunk_path)

        assert result == [DEFAULT_TEXT_PROCESSOR_CONFIG, expected_config]
