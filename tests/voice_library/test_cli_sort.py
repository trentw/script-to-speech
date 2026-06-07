"""Tests for the sts-sort-voice-library-data CLI."""

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from script_to_speech.voice_library.cli_sort import (
    main,
    sort_voices_file,
    sort_voices_text,
    split_voice_section,
)

# An unsorted voices file exercising formatting that a YAML round-trip would mangle:
# a quoted empty string, a nested list, inline punctuation, and a trailing newline.
UNSORTED_YAML = """voices:
  charming_queen:
    config:
      voice_id: English_CharmingQueen
    voice_properties:
      gender: feminine
      special_vocal_characteristics: ''
    tags:
      custom_tags:
      - bright
      - expressive
  abbess:
    config:
      voice_id: English_Abbess
    voice_properties:
      gender: feminine
      age: 0.6
    preview_url: https://example.com/abbess.mp3
  casual_podcaster:
    config:
      voice_id: English_causual_podcast_vv1
    description:
      provider_name: Casual Podcaster
"""

SORTED_KEYS = ["abbess", "casual_podcaster", "charming_queen"]

# A file with a second top-level section before `voices:` (like the elevenlabs files).
# `provider_metadata.cost_value` is also indent-2 and must NOT be treated as a voice.
UNSORTED_YAML_WITH_METADATA = """# ElevenLabs Voice Library
provider_metadata:
  cost_value: 0.3

voices:
  zelda:
    config:
      voice_id: z1
  aria:
    config:
      voice_id: a1
"""

# A file where each voice has a leading `# Name - ...` comment (like the openai files).
# The comment must travel with the voice it documents when the order changes.
UNSORTED_YAML_WITH_COMMENTS = """voices:

  # zelda - the last one
  zelda:
    config:
      voice_id: z1

  # aria - the first one
  aria:
    config:
      voice_id: a1
"""


class TestSplitVoiceSection:
    """Tests for split_voice_section."""

    def test_prefix_and_block_keys(self):
        prefix, blocks, suffix = split_voice_section(UNSORTED_YAML)
        assert prefix == "voices:\n"
        assert suffix == ""
        assert [key for key, _ in blocks] == [
            "charming_queen",
            "abbess",
            "casual_podcaster",
        ]

    def test_rejoining_reproduces_source_exactly(self):
        """prefix + every block_text + suffix must reproduce the input byte-for-byte."""
        prefix, blocks, suffix = split_voice_section(UNSORTED_YAML)
        assert prefix + "".join(text for _, text in blocks) + suffix == UNSORTED_YAML

    def test_no_voices_returns_all_prefix_no_blocks(self):
        text = "voices:\n"
        prefix, blocks, suffix = split_voice_section(text)
        assert prefix == text
        assert blocks == []
        assert suffix == ""

    def test_other_top_level_section_excluded_from_blocks(self):
        """provider_metadata's indent-2 child is not a voice; it stays in the prefix."""
        prefix, blocks, suffix = split_voice_section(UNSORTED_YAML_WITH_METADATA)
        assert [key for key, _ in blocks] == ["zelda", "aria"]
        assert "provider_metadata:" in prefix
        assert "cost_value" in prefix
        assert suffix == ""
        assert prefix + "".join(t for _, t in blocks) + suffix == (
            UNSORTED_YAML_WITH_METADATA
        )


class TestSortVoicesText:
    """Tests for the pure text-sorting function."""

    def test_blocks_sorted_alphabetically(self):
        result = sort_voices_text(UNSORTED_YAML)
        _, blocks, _ = split_voice_section(result)
        assert [key for key, _ in blocks] == SORTED_KEYS

    def test_data_is_preserved(self):
        """Only ordering changes -- parsed data is identical."""
        assert yaml.safe_load(sort_voices_text(UNSORTED_YAML)) == yaml.safe_load(
            UNSORTED_YAML
        )

    def test_formatting_preserved_byte_for_byte(self):
        """Each voice's block bytes are unchanged; only their order differs."""
        _, original_blocks, _ = split_voice_section(UNSORTED_YAML)
        original_by_key = dict(original_blocks)
        _, sorted_blocks, _ = split_voice_section(sort_voices_text(UNSORTED_YAML))
        for key, text in sorted_blocks:
            assert text == original_by_key[key]
        # Quoted empty string survives (a YAML dump would rewrite this).
        assert "special_vocal_characteristics: ''" in sort_voices_text(UNSORTED_YAML)

    def test_other_top_level_section_preserved(self):
        """Files with a provider_metadata section sort voices and keep metadata."""
        result = sort_voices_text(UNSORTED_YAML_WITH_METADATA)
        _, blocks, _ = split_voice_section(result)
        assert [key for key, _ in blocks] == ["aria", "zelda"]
        # Full-document data (including provider_metadata) is unchanged.
        assert yaml.safe_load(result) == yaml.safe_load(UNSORTED_YAML_WITH_METADATA)
        assert "cost_value: 0.3" in result

    def test_leading_comment_travels_with_its_voice(self):
        """A `# Name` comment above a voice key stays attached when order changes."""
        result = sort_voices_text(UNSORTED_YAML_WITH_COMMENTS)
        _, blocks, _ = split_voice_section(result)
        assert [key for key, _ in blocks] == ["aria", "zelda"]
        # aria (and its comment) now precede zelda (and its comment).
        assert result.index("# aria") < result.index("# zelda")
        # Each comment is still immediately above the key it documents.
        assert "  # aria - the first one\n  aria:\n" in result
        assert "  # zelda - the last one\n  zelda:\n" in result

    def test_comments_preserve_data_and_lines(self):
        """Reordering commented voices preserves data and every source line."""
        result = sort_voices_text(UNSORTED_YAML_WITH_COMMENTS)
        assert yaml.safe_load(result) == yaml.safe_load(UNSORTED_YAML_WITH_COMMENTS)
        assert sorted(result.splitlines()) == sorted(
            UNSORTED_YAML_WITH_COMMENTS.splitlines()
        )

    def test_trailing_newline_preserved(self):
        assert sort_voices_text(UNSORTED_YAML).endswith("\n")
        assert not sort_voices_text(UNSORTED_YAML).endswith("\n\n")

    def test_idempotent(self):
        once = sort_voices_text(UNSORTED_YAML)
        assert sort_voices_text(once) == once

    def test_already_sorted_unchanged(self):
        already = sort_voices_text(UNSORTED_YAML)
        assert sort_voices_text(already) == already

    def test_no_voices_returns_unchanged(self):
        text = "voices:\n"
        assert sort_voices_text(text) == text


class TestSortVoicesFile:
    """Tests for the file-level operation."""

    def test_writes_sorted_output_to_new_file(self, tmp_path: Path):
        input_path = tmp_path / "voices.yaml"
        input_path.write_text(UNSORTED_YAML)

        exit_code = sort_voices_file(input_path)

        assert exit_code == 0
        output_path = tmp_path / "voices.sorted.yaml"
        assert output_path.exists()
        # Input is untouched.
        assert input_path.read_text() == UNSORTED_YAML
        _, blocks, _ = split_voice_section(output_path.read_text())
        assert [key for key, _ in blocks] == SORTED_KEYS

    def test_explicit_output_path(self, tmp_path: Path):
        input_path = tmp_path / "voices.yaml"
        input_path.write_text(UNSORTED_YAML)
        output_path = tmp_path / "out.yaml"

        assert sort_voices_file(input_path, output_path) == 0
        assert output_path.read_text() == sort_voices_text(UNSORTED_YAML)

    def test_refuses_to_overwrite_input(self, tmp_path: Path):
        input_path = tmp_path / "voices.yaml"
        input_path.write_text(UNSORTED_YAML)

        assert sort_voices_file(input_path, input_path) == 1
        # Unchanged.
        assert input_path.read_text() == UNSORTED_YAML

    def test_missing_input_returns_error(self, tmp_path: Path):
        assert sort_voices_file(tmp_path / "nope.yaml") == 1

    def test_no_voices_returns_error(self, tmp_path: Path):
        input_path = tmp_path / "voices.yaml"
        input_path.write_text("voices:\n")
        assert sort_voices_file(input_path) == 1

    def test_check_mode_unsorted_returns_one_and_writes_nothing(self, tmp_path: Path):
        input_path = tmp_path / "voices.yaml"
        input_path.write_text(UNSORTED_YAML)

        assert sort_voices_file(input_path, check=True) == 1
        assert not (tmp_path / "voices.sorted.yaml").exists()

    def test_check_mode_sorted_returns_zero(self, tmp_path: Path):
        input_path = tmp_path / "voices.yaml"
        input_path.write_text(sort_voices_text(UNSORTED_YAML))

        assert sort_voices_file(input_path, check=True) == 0


class TestMain:
    """Tests for the argparse entry point."""

    def test_main_passes_args_and_exits(self, tmp_path: Path):
        input_path = tmp_path / "voices.yaml"
        input_path.write_text(UNSORTED_YAML)

        with patch("sys.argv", ["sts-sort-voice-library-data", str(input_path)]):
            with patch("sys.exit") as mock_exit:
                main()

        mock_exit.assert_called_once_with(0)
        assert (tmp_path / "voices.sorted.yaml").exists()

    def test_main_check_flag(self, tmp_path: Path):
        input_path = tmp_path / "voices.yaml"
        input_path.write_text(UNSORTED_YAML)

        with patch(
            "sys.argv", ["sts-sort-voice-library-data", str(input_path), "--check"]
        ):
            with patch("sys.exit") as mock_exit:
                main()

        mock_exit.assert_called_once_with(1)
