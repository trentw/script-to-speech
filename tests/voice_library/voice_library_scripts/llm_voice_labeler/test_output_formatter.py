"""Tests for output formatting logic."""

from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

from script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.output_formatter import (
    format_voices_yaml,
    print_summary,
    write_voices_yaml,
)


def _make_consensus(
    age=0.5,
    gender="male",
    accent="american",
    custom_description="A clear voice.",
    perceived_age="30-40",
    character_types=None,
    custom_tags=None,
    special_vocal_characteristics=None,
):
    """Build a minimal consensus result dict."""
    vp = {
        "age": age,
        "authority": 0.5,
        "energy": 0.5,
        "pace": 0.5,
        "performative": 0.5,
        "pitch": 0.5,
        "quality": 0.9,
        "range": 0.5,
        "gender": gender,
        "accent": accent,
    }
    if special_vocal_characteristics:
        vp["special_vocal_characteristics"] = special_vocal_characteristics
    return {
        "voice_properties": vp,
        "description": {
            "custom_description": custom_description,
            "perceived_age": perceived_age,
        },
        "tags": {
            "character_types": character_types or ["narrator"],
            "custom_tags": custom_tags or ["calm"],
        },
    }


def _make_input_config(*voice_ids, provider_info=None, preview_url=None):
    """Build a minimal input config."""
    voices = {}
    for vid in voice_ids:
        entry = {"config": {"voice_id": vid}}
        if provider_info:
            entry["provider_info"] = provider_info
        if preview_url:
            entry["preview_url"] = preview_url
        voices[vid] = entry
    return {"voices": voices}


class TestFormatVoicesYaml:
    """Tests for format_voices_yaml()."""

    def test_basic_structure(self):
        # Arrange
        input_config = _make_input_config("voice1")
        consensus_results = {"voice1": (_make_consensus(), [])}

        # Act
        output = format_voices_yaml("test_provider", input_config, consensus_results)

        # Assert
        assert "voices" in output
        assert "voice1" in output["voices"]
        voice = output["voices"]["voice1"]
        assert "config" in voice
        assert "voice_properties" in voice
        assert "description" in voice

    def test_skips_error_voices(self):
        # Arrange
        input_config = _make_input_config("good", "bad")
        consensus_results = {
            "good": (_make_consensus(), []),
            "bad": ({"error": "something failed"}, ["all_runs_failed"]),
        }

        # Act
        output = format_voices_yaml("test_provider", input_config, consensus_results)

        # Assert
        assert "good" in output["voices"]
        assert "bad" not in output["voices"]

    def test_includes_provider_metadata(self):
        # Arrange
        input_config = _make_input_config("v1")
        consensus_results = {"v1": (_make_consensus(), [])}
        metadata = {"model": "test-model", "version": "1.0"}

        # Act
        output = format_voices_yaml(
            "test_provider", input_config, consensus_results, provider_metadata=metadata
        )

        # Assert
        assert "provider_metadata" in output
        assert output["provider_metadata"] == metadata

    def test_no_provider_metadata(self):
        # Arrange
        input_config = _make_input_config("v1")
        consensus_results = {"v1": (_make_consensus(), [])}

        # Act
        output = format_voices_yaml("test_provider", input_config, consensus_results)

        # Assert
        assert "provider_metadata" not in output

    def test_voice_properties_enum_before_range(self):
        # Arrange
        input_config = _make_input_config("v1")
        consensus_results = {"v1": (_make_consensus(), [])}

        # Act
        output = format_voices_yaml("test_provider", input_config, consensus_results)

        # Assert
        vp_keys = list(output["voices"]["v1"]["voice_properties"].keys())
        # Enum props (accent, gender) should come before range props (age, authority, ...)
        enum_indices = [vp_keys.index(p) for p in ["accent", "gender"] if p in vp_keys]
        range_indices = [vp_keys.index(p) for p in ["age", "authority"] if p in vp_keys]
        assert max(enum_indices) < min(range_indices)

    def test_use_cases_string_split(self):
        # Arrange
        provider_info = {"provider_use_cases": "News, Audiobook, Podcast"}
        input_config = _make_input_config("v1", provider_info=provider_info)
        consensus_results = {"v1": (_make_consensus(), [])}

        # Act
        output = format_voices_yaml("test_provider", input_config, consensus_results)

        # Assert
        tags = output["voices"]["v1"]["tags"]["provider_use_cases"]
        assert isinstance(tags, list)
        assert len(tags) == 3
        # Should be lowercased with underscores
        assert all(t == t.lower() for t in tags)

    def test_use_cases_list_passthrough(self):
        # Arrange
        provider_info = {"provider_use_cases": ["news", "audiobook"]}
        input_config = _make_input_config("v1", provider_info=provider_info)
        consensus_results = {"v1": (_make_consensus(), [])}

        # Act
        output = format_voices_yaml("test_provider", input_config, consensus_results)

        # Assert
        tags = output["voices"]["v1"]["tags"]["provider_use_cases"]
        assert tags == ["news", "audiobook"]

    def test_consensus_character_types_in_tags(self):
        # Arrange
        input_config = _make_input_config("v1")
        consensus_results = {
            "v1": (_make_consensus(character_types=["narrator", "professor"]), [])
        }

        # Act
        output = format_voices_yaml("test_provider", input_config, consensus_results)

        # Assert
        assert output["voices"]["v1"]["tags"]["character_types"] == [
            "narrator",
            "professor",
        ]

    def test_preview_url_included(self):
        # Arrange
        input_config = _make_input_config(
            "v1", preview_url="https://example.com/v1.mp3"
        )
        consensus_results = {"v1": (_make_consensus(), [])}

        # Act
        output = format_voices_yaml("test_provider", input_config, consensus_results)

        # Assert
        assert output["voices"]["v1"]["preview_url"] == "https://example.com/v1.mp3"

    def test_empty_special_vocal_characteristics_omitted(self):
        # Arrange
        input_config = _make_input_config("v1")
        consensus_results = {
            "v1": (_make_consensus(special_vocal_characteristics=""), [])
        }

        # Act
        output = format_voices_yaml("test_provider", input_config, consensus_results)

        # Assert
        assert (
            "special_vocal_characteristics"
            not in output["voices"]["v1"]["voice_properties"]
        )

    def test_nonempty_special_vocal_characteristics_included(self):
        # Arrange
        input_config = _make_input_config("v1")
        consensus_results = {
            "v1": (_make_consensus(special_vocal_characteristics="slight rasp"), [])
        }

        # Act
        output = format_voices_yaml("test_provider", input_config, consensus_results)

        # Assert
        assert (
            output["voices"]["v1"]["voice_properties"]["special_vocal_characteristics"]
            == "slight rasp"
        )

    def test_empty_consensus_results(self):
        # Arrange
        input_config = _make_input_config()
        consensus_results = {}

        # Act
        output = format_voices_yaml("test_provider", input_config, consensus_results)

        # Assert
        assert output["voices"] == {}

    def test_description_with_provider_info(self):
        # Arrange
        provider_info = {
            "provider_name": "TestVoice",
            "provider_description": "A great voice",
        }
        input_config = _make_input_config("v1", provider_info=provider_info)
        consensus_results = {"v1": (_make_consensus(), [])}

        # Act
        output = format_voices_yaml("test_provider", input_config, consensus_results)

        # Assert
        desc = output["voices"]["v1"]["description"]
        assert "provider_name" in desc
        assert "custom_description" in desc

    def test_description_without_provider_info(self):
        # Arrange
        input_config = _make_input_config("v1")
        consensus_results = {"v1": (_make_consensus(), [])}

        # Act
        output = format_voices_yaml("test_provider", input_config, consensus_results)

        # Assert
        desc = output["voices"]["v1"]["description"]
        assert "provider_name" not in desc
        assert "custom_description" in desc


class TestWriteVoicesYaml:
    """Tests for write_voices_yaml()."""

    @patch(
        "script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.output_formatter.yaml.dump"
    )
    @patch("builtins.open", new_callable=mock_open)
    def test_creates_directory_and_writes(self, mock_file, mock_yaml_dump):
        # Arrange
        output_data = {"voices": {"v1": {}}}
        output_path = MagicMock(spec=Path)
        parent_mock = MagicMock()
        output_path.parent = parent_mock

        # Act
        write_voices_yaml(output_data, output_path)

        # Assert
        parent_mock.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_file.assert_called_once_with(output_path, "w")
        mock_yaml_dump.assert_called_once()
        # Verify yaml.dump kwargs
        call_kwargs = mock_yaml_dump.call_args[1]
        assert call_kwargs["default_flow_style"] is False
        assert call_kwargs["sort_keys"] is False


class TestPrintSummary:
    """Tests for print_summary()."""

    def test_runs_without_error_all_successful(self, capsys):
        # Arrange
        consensus_results = {
            "v1": (_make_consensus(), []),
            "v2": (_make_consensus(), []),
        }

        # Act
        print_summary(consensus_results)

        # Assert — no exception raised
        output = capsys.readouterr().out
        assert len(output) > 0

    def test_runs_without_error_with_failures_and_flags(self, capsys):
        # Arrange
        consensus_results = {
            "v1": (_make_consensus(), ["some_flag"]),
            "v2": ({"error": "failed"}, ["all_runs_failed"]),
        }

        # Act
        print_summary(consensus_results)

        # Assert — no exception raised
        output = capsys.readouterr().out
        assert len(output) > 0
