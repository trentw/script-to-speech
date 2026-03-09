"""Tests for sample generator logic."""

from unittest.mock import MagicMock, mock_open, patch

import pytest

from script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.sample_generator import (
    generate_dual_samples,
    generate_input_template,
    generate_samples,
    load_input_config,
    slugify_voice_id,
)


class TestSlugifyVoiceId:
    """Tests for slugify_voice_id()."""

    def test_camel_case(self):
        assert slugify_voice_id("WiseScholar") == "wise_scholar"

    def test_english_prefix(self):
        assert slugify_voice_id("English_WiseScholar") == "wise_scholar"

    def test_typo_prefix_eglish(self):
        assert slugify_voice_id("Eglish_FriendlyMan") == "friendly_man"

    def test_typo_prefix_enlish(self):
        assert slugify_voice_id("Enlish_CoolGuy") == "cool_guy"

    def test_british_child_prefix(self):
        assert slugify_voice_id("BritishChild_SmallKid") == "small_kid"

    def test_already_lowercase(self):
        assert slugify_voice_id("simple") == "simple"

    def test_hyphens_and_spaces(self):
        result = slugify_voice_id("voice-name here")
        assert "_" in result
        assert "-" not in result
        assert " " not in result

    def test_consecutive_uppercase(self):
        result = slugify_voice_id("ABCDef")
        assert result == "abc_def"

    def test_result_is_always_lowercase(self):
        assert slugify_voice_id("ALLCAPS").islower()


class TestLoadInputConfig:
    """Tests for load_input_config()."""

    @patch(
        "script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.sample_generator.yaml.safe_load"
    )
    @patch("builtins.open", new_callable=mock_open)
    def test_valid_config(self, _mock_file, mock_yaml):
        # Arrange
        mock_yaml.return_value = {
            "voices": {
                "v1": {"config": {"voice_id": "voice1"}},
            }
        }

        # Act
        result = load_input_config("/fake/config.yaml")

        # Assert
        assert "voices" in result
        assert "v1" in result["voices"]

    @patch(
        "script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.sample_generator.yaml.safe_load"
    )
    @patch("builtins.open", new_callable=mock_open)
    def test_missing_voices_key(self, _mock_file, mock_yaml):
        # Arrange
        mock_yaml.return_value = {"something_else": {}}

        # Act & Assert
        with pytest.raises(ValueError):
            load_input_config("/fake/config.yaml")

    @patch(
        "script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.sample_generator.yaml.safe_load"
    )
    @patch("builtins.open", new_callable=mock_open)
    def test_voices_not_dict(self, _mock_file, mock_yaml):
        # Arrange
        mock_yaml.return_value = {"voices": ["not", "a", "dict"]}

        # Act & Assert
        with pytest.raises(ValueError):
            load_input_config("/fake/config.yaml")

    @patch(
        "script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.sample_generator.yaml.safe_load"
    )
    @patch("builtins.open", new_callable=mock_open)
    def test_entry_missing_config(self, _mock_file, mock_yaml):
        # Arrange
        mock_yaml.return_value = {
            "voices": {
                "v1": {"no_config_here": True},
            }
        }

        # Act & Assert
        with pytest.raises(ValueError):
            load_input_config("/fake/config.yaml")


class TestGenerateInputTemplate:
    """Tests for generate_input_template()."""

    @patch("script_to_speech.utils.generate_standalone_speech.get_provider_class")
    def test_builds_template_from_valid_voice_ids(self, mock_get_provider):
        # Arrange
        mock_class = MagicMock()
        mock_class.VALID_VOICE_IDS = ["VoiceA", "VoiceB"]
        mock_class.get_required_fields.return_value = ["voice_id"]
        mock_get_provider.return_value = mock_class

        # Act
        result = generate_input_template("test_provider")

        # Assert
        assert "voices" in result
        voices = result["voices"]
        assert len(voices) == 2
        # Keys should be slugified
        for key in voices:
            assert key == key.lower()
            assert "config" in voices[key]

    @patch("script_to_speech.utils.generate_standalone_speech.get_provider_class")
    def test_no_valid_voice_ids(self, mock_get_provider):
        # Arrange — provider class without VALID_VOICE_IDS attribute
        mock_class = MagicMock()
        del mock_class.VALID_VOICE_IDS  # Remove the attribute so hasattr returns False
        mock_class.get_required_fields.return_value = ["voice_id"]
        mock_get_provider.return_value = mock_class

        # Act
        result = generate_input_template("test_provider")

        # Assert
        assert "voices" in result
        assert len(result["voices"]) == 1


class TestGenerateSamples:
    """Tests for generate_samples()."""

    @patch("os.path.exists", return_value=True)
    @patch(
        "script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.sample_generator.generate_standalone_speech"
    )
    @patch(
        "script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.sample_generator.TTSProviderManager"
    )
    @patch("os.makedirs")
    def test_generates_for_all_voices(
        self, _mock_makedirs, _mock_tts, _mock_gen, _mock_exists
    ):
        # Arrange
        input_config = {
            "voices": {
                "v1": {"config": {"voice_id": "id1"}},
                "v2": {"config": {"voice_id": "id2"}},
            }
        }

        # Act
        result = generate_samples("test_provider", input_config, "/output")

        # Assert
        assert len(result) == 2
        assert "v1" in result
        assert "v2" in result

    @patch("os.path.exists", return_value=True)
    @patch(
        "script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.sample_generator.generate_standalone_speech"
    )
    @patch(
        "script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.sample_generator.TTSProviderManager"
    )
    @patch("os.makedirs")
    def test_filters_by_sts_ids(
        self, _mock_makedirs, _mock_tts, _mock_gen, _mock_exists
    ):
        # Arrange
        input_config = {
            "voices": {
                "v1": {"config": {"voice_id": "id1"}},
                "v2": {"config": {"voice_id": "id2"}},
            }
        }

        # Act
        result = generate_samples(
            "test_provider", input_config, "/output", sts_ids=["v1"]
        )

        # Assert
        assert "v1" in result
        assert "v2" not in result

    @patch(
        "script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.sample_generator.generate_standalone_speech"
    )
    @patch(
        "script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.sample_generator.TTSProviderManager"
    )
    @patch("os.makedirs")
    def test_handles_generation_failure(self, _mock_makedirs, _mock_tts, mock_gen):
        # Arrange
        mock_gen.side_effect = Exception("TTS failed")
        input_config = {
            "voices": {
                "v1": {"config": {"voice_id": "id1"}},
            }
        }

        # Act
        result = generate_samples("test_provider", input_config, "/output")

        # Assert
        assert len(result) == 0


class TestGenerateDualSamples:
    """Tests for generate_dual_samples()."""

    @patch("os.path.exists", return_value=True)
    @patch(
        "script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.sample_generator.generate_standalone_speech"
    )
    @patch(
        "script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.sample_generator.TTSProviderManager"
    )
    @patch("os.makedirs")
    def test_creates_both_clips(
        self, _mock_makedirs, _mock_tts, _mock_gen, _mock_exists
    ):
        # Arrange
        input_config = {
            "voices": {
                "v1": {"config": {"voice_id": "id1"}},
            }
        }

        # Act
        result = generate_dual_samples("test_provider", input_config, "/output")

        # Assert
        assert "v1" in result
        assert "neutral" in result["v1"]
        assert "expressive" in result["v1"]
