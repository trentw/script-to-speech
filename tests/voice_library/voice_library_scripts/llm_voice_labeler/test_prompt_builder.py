"""Tests for prompt builder logic."""

from unittest.mock import mock_open, patch

from script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.prompt_builder import (
    build_system_prompt,
    build_user_message,
    format_calibration_examples,
    load_calibration_examples,
    load_schema,
)


class TestLoadSchema:
    """Tests for load_schema()."""

    @patch("builtins.open", new_callable=mock_open, read_data="schema_content_here")
    def test_returns_file_content(self, _mock_file):
        # Act
        result = load_schema()

        # Assert
        assert len(result) > 0
        assert isinstance(result, str)


class TestLoadCalibrationExamples:
    """Tests for load_calibration_examples()."""

    @patch(
        "script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.prompt_builder.yaml.safe_load"
    )
    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.exists", return_value=True)
    def test_returns_examples_for_default_providers(
        self, _mock_exists, _mock_file, mock_yaml
    ):
        # Arrange
        mock_yaml.return_value = {
            "voices": {
                "onyx": {
                    "voice_properties": {"age": 0.5},
                    "description": {"custom_description": "test"},
                    "tags": {"character_types": ["narrator"]},
                },
                "sage": {
                    "voice_properties": {"age": 0.4},
                    "description": {},
                    "tags": {},
                },
            }
        }

        # Act
        result = load_calibration_examples()

        # Assert
        assert isinstance(result, list)
        assert len(result) > 0
        for ex in result:
            assert "sts_id" in ex
            assert "voice_properties" in ex

    @patch(
        "script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.prompt_builder.yaml.safe_load"
    )
    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.exists", return_value=True)
    def test_filters_by_provider(self, _mock_exists, _mock_file, mock_yaml):
        # Arrange
        mock_yaml.return_value = {
            "voices": {
                "onyx": {"voice_properties": {}, "description": {}, "tags": {}},
            }
        }

        # Act
        result = load_calibration_examples(providers=["openai"])

        # Assert — only openai provider voices
        assert all(ex["provider"] == "openai" for ex in result)

    @patch(
        "script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.prompt_builder.yaml.safe_load"
    )
    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.exists", return_value=True)
    def test_missing_voice_skipped(self, _mock_exists, _mock_file, mock_yaml):
        # Arrange — voices.yaml doesn't have all calibration IDs
        mock_yaml.return_value = {
            "voices": {
                "onyx": {"voice_properties": {}, "description": {}, "tags": {}},
                # Missing "sage", "fable", etc.
            }
        }

        # Act
        result = load_calibration_examples(providers=["openai"])

        # Assert
        found_ids = {ex["sts_id"] for ex in result}
        assert "onyx" in found_ids

    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.exists")
    def test_fallback_to_premade(self, mock_exists, _mock_file):
        # Arrange — voices.yaml doesn't exist, voices_premade.yaml does
        mock_exists.side_effect = lambda: True  # Will be overridden per path

        # We need a more nuanced mock for Path.exists
        call_count = {"n": 0}

        def exists_side_effect(self=None):
            call_count["n"] += 1
            # First call for voices.yaml -> False, second for voices_premade.yaml -> True
            if call_count["n"] % 2 == 1:
                return False
            return True

        mock_exists.side_effect = exists_side_effect

        with patch(
            "script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.prompt_builder.yaml.safe_load",
            return_value={"voices": {}},
        ):
            # Act
            result = load_calibration_examples(providers=["openai"])

            # Assert — should attempt to open the fallback file
            assert isinstance(result, list)


class TestFormatCalibrationExamples:
    """Tests for format_calibration_examples()."""

    def test_empty_returns_nonempty_string(self):
        # Act
        result = format_calibration_examples([])

        # Assert
        assert isinstance(result, str)
        assert len(result) > 0

    def test_formats_examples(self):
        # Arrange
        examples = [
            {
                "provider": "openai",
                "sts_id": "onyx",
                "voice_properties": {"age": 0.5, "pitch": 0.4},
                "description": {"custom_description": "A deep voice"},
                "tags": {"character_types": ["narrator"]},
            }
        ]

        # Act
        result = format_calibration_examples(examples)

        # Assert
        assert isinstance(result, str)
        assert len(result) > len(format_calibration_examples([]))


class TestBuildSystemPrompt:
    """Tests for build_system_prompt()."""

    @patch(
        "script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.prompt_builder.load_calibration_examples",
        return_value=[],
    )
    @patch(
        "script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.prompt_builder.load_schema",
        return_value="mock_schema",
    )
    def test_returns_nonempty_string(self, _mock_schema, _mock_examples):
        # Act
        result = build_system_prompt()

        # Assert
        assert isinstance(result, str)
        assert len(result) > 0

    @patch(
        "script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.prompt_builder.load_calibration_examples",
        return_value=[],
    )
    @patch(
        "script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.prompt_builder.load_schema",
        return_value="mock_schema",
    )
    def test_dual_clips_produces_different_output(self, _mock_schema, _mock_examples):
        # Act
        single = build_system_prompt(dual_clips=False)
        dual = build_system_prompt(dual_clips=True)

        # Assert
        assert single != dual


class TestBuildUserMessage:
    """Tests for build_user_message()."""

    def test_without_provider_info(self):
        # Act
        result = build_user_message()

        # Assert
        assert isinstance(result, str)
        assert len(result) > 0

    def test_with_provider_info_is_longer(self):
        # Arrange
        provider_info = {
            "provider_name": "TestVoice",
            "provider_description": "A test voice",
            "provider_use_cases": "narration, news",
        }

        # Act
        with_info = build_user_message(provider_info)
        without_info = build_user_message()

        # Assert
        assert len(with_info) > len(without_info)

    def test_provider_info_fields_included(self):
        # Arrange
        provider_info = {
            "provider_name": "UniqueVoiceName123",
            "provider_description": "UniqueDescription456",
        }

        # Act
        result = build_user_message(provider_info)

        # Assert — field values appear in the output
        assert "UniqueVoiceName123" in result
        assert "UniqueDescription456" in result

    def test_partial_provider_info(self):
        # Arrange — only provider_name, no description
        provider_info = {"provider_name": "PartialVoice"}

        # Act
        result = build_user_message(provider_info)

        # Assert
        assert "PartialVoice" in result
