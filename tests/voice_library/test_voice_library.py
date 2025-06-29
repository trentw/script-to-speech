"""Tests for voice library core functionality."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
import yaml

from script_to_speech.tts_providers.base.exceptions import VoiceNotFoundError
from script_to_speech.voice_library.voice_library import VoiceLibrary


class TestVoiceLibrary:
    """Tests for the VoiceLibrary class."""

    def test_init(self):
        """Test VoiceLibrary initialization."""
        # Arrange & Act
        library = VoiceLibrary()

        # Assert
        assert library._voice_library_cache == {}

    @patch("script_to_speech.voice_library.voice_library.yaml.safe_load")
    @patch("builtins.open", new_callable=mock_open)
    @patch("script_to_speech.voice_library.voice_library.USER_VOICE_LIBRARY_PATH")
    @patch("script_to_speech.voice_library.voice_library.REPO_VOICE_LIBRARY_PATH")
    def test_load_provider_voices_success(
        self, mock_repo_path, mock_user_path, mock_file, mock_yaml
    ):
        """Test _load_provider_voices with valid provider directories."""
        # Arrange
        library = VoiceLibrary()

        # Mock directory structure
        project_dir = MagicMock()
        user_dir = MagicMock()

        project_dir.exists.return_value = True
        project_dir.is_dir.return_value = True
        project_dir.glob.return_value = [Path("voices1.yaml")]

        user_dir.exists.return_value = True
        user_dir.is_dir.return_value = True
        user_dir.glob.return_value = [Path("voices2.yaml")]

        mock_repo_path.__truediv__.return_value = project_dir
        mock_user_path.__truediv__.return_value = user_dir

        # Mock YAML data
        project_voices = {
            "voices": {
                "voice1": {"config": {"voice": "v1"}, "description": "Voice 1"},
                "voice2": {"config": {"voice": "v2"}, "description": "Voice 2"},
            }
        }
        user_voices = {
            "voices": {
                "voice2": {
                    "config": {"voice": "v2_override"},
                    "description": "Voice 2 Override",
                },
                "voice3": {"config": {"voice": "v3"}, "description": "Voice 3"},
            }
        }

        mock_yaml.side_effect = [project_voices, user_voices]

        # Act
        result = library._load_provider_voices("test_provider")

        # Assert - user voice2 should override project voice2
        expected = {
            "voice1": {"config": {"voice": "v1"}, "description": "Voice 1"},
            "voice2": {
                "config": {"voice": "v2_override"},
                "description": "Voice 2 Override",
            },
            "voice3": {"config": {"voice": "v3"}, "description": "Voice 3"},
        }
        assert result == expected
        assert library._voice_library_cache["test_provider"] == expected

    def test_load_provider_voices_cached(self):
        """Test _load_provider_voices returns cached data on second call."""
        # Arrange
        library = VoiceLibrary()
        cached_data = {"voice1": {"config": {"voice": "v1"}}}
        library._voice_library_cache["test_provider"] = cached_data

        # Act
        result = library._load_provider_voices("test_provider")

        # Assert
        assert result == cached_data
        assert result is cached_data  # Should be the same object

    @patch("script_to_speech.voice_library.voice_library.USER_VOICE_LIBRARY_PATH")
    @patch("script_to_speech.voice_library.voice_library.REPO_VOICE_LIBRARY_PATH")
    def test_load_provider_voices_provider_not_found(
        self, mock_repo_path, mock_user_path
    ):
        """Test _load_provider_voices when provider directory doesn't exist."""
        # Arrange
        library = VoiceLibrary()

        # Mock both directories as non-existent
        project_dir = MagicMock()
        user_dir = MagicMock()
        project_dir.exists.return_value = False
        user_dir.exists.return_value = False

        mock_repo_path.__truediv__.return_value = project_dir
        mock_user_path.__truediv__.return_value = user_dir

        # Act & Assert
        with pytest.raises(
            VoiceNotFoundError,
            match="No voice library found for provider 'nonexistent'",
        ):
            library._load_provider_voices("nonexistent")

    def test_load_provider_voices_skip_schema_files(self):
        """Test _load_provider_voices skips provider_schema.yaml files."""
        # Arrange
        voice_data = {"voices": {"voice1": {"config": {"voice": "v1"}}}}
        schema_data = {"voice_properties": {"custom_prop": {"type": "text"}}}

        file_contents = {
            "voices.yaml": yaml.dump(voice_data),
            "provider_schema.yaml": yaml.dump(schema_data),
        }

        def mock_glob(pattern):
            return [Path(f) for f in file_contents.keys() if f.endswith(".yaml")]

        def mock_open_func(file, mode="r"):
            return mock_open(read_data=file_contents[Path(file).name])()

        with (
            patch("pathlib.Path.glob", side_effect=mock_glob),
            patch("builtins.open", side_effect=mock_open_func),
            patch("pathlib.Path.is_dir", return_value=True),
            patch("pathlib.Path.exists", return_value=True),
        ):
            library = VoiceLibrary()

            # Act
            result = library._load_provider_voices("test_provider")

            # Assert
            expected = {"voice1": {"config": {"voice": "v1"}}}
            assert result == expected

    def test_load_provider_voices_invalid_voices_section(self):
        """Test _load_provider_voices handles invalid voices section."""
        # Arrange
        invalid_data = {"voices": "not_a_dict"}

        with (
            patch("pathlib.Path.glob", return_value=[Path("invalid.yaml")]),
            patch("builtins.open", mock_open(read_data=yaml.dump(invalid_data))),
            patch("pathlib.Path.is_dir", return_value=True),
            patch("pathlib.Path.exists", return_value=True),
            patch("script_to_speech.voice_library.voice_library.logger") as mock_logger,
        ):
            library = VoiceLibrary()

            # Act & Assert
            with pytest.raises(
                VoiceNotFoundError,
                match="No voice library found for provider 'test_provider'",
            ):
                library._load_provider_voices("test_provider")

            assert mock_logger.warning.call_count > 0
            assert "Invalid voices section" in mock_logger.warning.call_args[0][0]

    def test_load_provider_voices_file_load_error(self):
        """Test _load_provider_voices handles file loading errors."""
        # Arrange
        with (
            patch("pathlib.Path.glob", return_value=[Path("error.yaml")]),
            patch("builtins.open", side_effect=IOError("File read error")),
            patch("pathlib.Path.is_dir", return_value=True),
            patch("pathlib.Path.exists", return_value=True),
            patch("script_to_speech.voice_library.voice_library.logger") as mock_logger,
        ):
            library = VoiceLibrary()

            # Act & Assert
            with pytest.raises(
                VoiceNotFoundError,
                match="No voice library found for provider 'test_provider'",
            ):
                library._load_provider_voices("test_provider")

            assert mock_logger.error.call_count > 0
            assert "Error loading" in mock_logger.error.call_args[0][0]

    def test_expand_config_success(self):
        """Test expand_config with valid provider and sts_id."""
        # Arrange
        library = VoiceLibrary()
        voice_data = {
            "test_voice": {
                "config": {"voice": "test", "model": "test_model"},
                "description": "Test voice",
            }
        }
        library._voice_library_cache["test_provider"] = voice_data

        # Act
        result = library.expand_config("test_provider", "test_voice")

        # Assert
        expected = {"voice": "test", "model": "test_model", "provider": "test_provider"}
        assert result == expected

    def test_expand_config_empty_provider(self):
        """Test expand_config with empty provider name."""
        # Arrange
        library = VoiceLibrary()

        # Act & Assert
        with pytest.raises(ValueError, match="Provider cannot be empty"):
            library.expand_config("", "test_voice")

    def test_expand_config_empty_sts_id(self):
        """Test expand_config with empty sts_id."""
        # Arrange
        library = VoiceLibrary()

        # Act & Assert
        with pytest.raises(VoiceNotFoundError, match="Voice ID cannot be empty"):
            library.expand_config("test_provider", "")

    @patch("script_to_speech.voice_library.voice_library.USER_VOICE_LIBRARY_PATH")
    @patch("script_to_speech.voice_library.voice_library.REPO_VOICE_LIBRARY_PATH")
    def test_expand_config_provider_not_found(self, mock_repo_path, mock_user_path):
        """Test expand_config when provider is not found."""
        # Arrange
        library = VoiceLibrary()

        # Mock both directories as non-existent
        project_dir = MagicMock()
        user_dir = MagicMock()
        project_dir.exists.return_value = False
        user_dir.exists.return_value = False

        mock_repo_path.__truediv__.return_value = project_dir
        mock_user_path.__truediv__.return_value = user_dir

        # Act & Assert
        with pytest.raises(
            VoiceNotFoundError,
            match="Cannot expand sts_id 'test_voice': provider 'nonexistent' not found",
        ):
            library.expand_config("nonexistent", "test_voice")

    def test_expand_config_voice_not_found(self):
        """Test expand_config when voice is not found in provider."""
        # Arrange
        library = VoiceLibrary()
        voice_data = {
            "voice1": {"config": {"voice": "v1"}},
            "voice2": {"config": {"voice": "v2"}},
            "voice3": {"config": {"voice": "v3"}},
            "voice4": {"config": {"voice": "v4"}},
            "voice5": {"config": {"voice": "v5"}},
            "voice6": {
                "config": {"voice": "v6"}
            },  # More than 5 voices to test truncation
        }
        library._voice_library_cache["test_provider"] = voice_data

        # Act & Assert
        with pytest.raises(VoiceNotFoundError) as exc_info:
            library.expand_config("test_provider", "nonexistent_voice")

        error_message = str(exc_info.value)
        assert (
            "Voice 'nonexistent_voice' not found in test_provider voice library"
            in error_message
        )
        assert "Available voices:" in error_message
        assert "and more..." in error_message  # Should show truncation message

    def test_expand_config_voice_not_found_few_voices(self):
        """Test expand_config when voice is not found with few available voices."""
        # Arrange
        library = VoiceLibrary()
        voice_data = {
            "voice1": {"config": {"voice": "v1"}},
            "voice2": {"config": {"voice": "v2"}},
        }
        library._voice_library_cache["test_provider"] = voice_data

        # Act & Assert
        with pytest.raises(VoiceNotFoundError) as exc_info:
            library.expand_config("test_provider", "nonexistent_voice")

        error_message = str(exc_info.value)
        assert (
            "Voice 'nonexistent_voice' not found in test_provider voice library"
            in error_message
        )
        assert "Available voices: voice1, voice2" in error_message
        assert "and more..." not in error_message  # Should not show truncation message

    def test_expand_config_missing_config_section(self):
        """Test expand_config when voice is missing config section."""
        # Arrange
        library = VoiceLibrary()
        voice_data = {"test_voice": {"description": "Test voice without config"}}
        library._voice_library_cache["test_provider"] = voice_data

        # Act & Assert
        with pytest.raises(
            ValueError,
            match="Voice 'test_voice' in test_provider is missing 'config' section",
        ):
            library.expand_config("test_provider", "test_voice")

    def test_expand_config_returns_copy(self):
        """Test expand_config returns a copy of the config, not the original."""
        # Arrange
        library = VoiceLibrary()
        original_config = {"voice": "test", "model": "test_model"}
        voice_data = {
            "test_voice": {"config": original_config, "description": "Test voice"}
        }
        library._voice_library_cache["test_provider"] = voice_data

        # Act
        result = library.expand_config("test_provider", "test_voice")

        # Assert
        assert result is not original_config  # Should be a different object
        result["new_key"] = "new_value"  # Modify the result
        assert "new_key" not in original_config  # Original should be unchanged

    def test_load_provider_voices_no_voices_section(self):
        """Test _load_provider_voices handles files without voices section."""
        # Arrange
        no_voices_data = {"metadata": {"provider": "test"}}

        with (
            patch("pathlib.Path.glob", return_value=[Path("no_voices.yaml")]),
            patch("builtins.open", mock_open(read_data=yaml.dump(no_voices_data))),
            patch("pathlib.Path.is_dir", return_value=True),
        ):
            library = VoiceLibrary()

            # Act & Assert
            with pytest.raises(
                VoiceNotFoundError,
                match="No voice library found for provider 'test_provider'",
            ):
                library._load_provider_voices("test_provider")

    def test_load_provider_voices_empty_file(self):
        """Test _load_provider_voices handles empty YAML files."""
        # Arrange
        with (
            patch("pathlib.Path.glob", return_value=[Path("empty.yaml")]),
            patch("builtins.open", mock_open(read_data="")),
            patch("pathlib.Path.is_dir", return_value=True),
        ):
            library = VoiceLibrary()

            # Act & Assert
            with pytest.raises(
                VoiceNotFoundError,
                match="No voice library found for provider 'test_provider'",
            ):
                library._load_provider_voices("test_provider")

    def test_load_provider_voices_duplicate_voice_ids(self):
        """Test _load_provider_voices raises error on duplicate voice IDs across files."""
        # Arrange
        voice_data1 = {
            "voices": {
                "voice1": {
                    "config": {"voice": "v1"},
                    "description": "Voice 1 from file 1",
                },
                "voice2": {"config": {"voice": "v2"}, "description": "Voice 2"},
            }
        }
        voice_data2 = {
            "voices": {
                "voice1": {
                    "config": {"voice": "v1_duplicate"},
                    "description": "Voice 1 from file 2",
                },
                "voice3": {"config": {"voice": "v3"}, "description": "Voice 3"},
            }
        }

        file_contents = {
            "voices1.yaml": yaml.dump(voice_data1),
            "voices2.yaml": yaml.dump(voice_data2),
        }

        def mock_glob(pattern):
            return [Path(f) for f in file_contents.keys()]

        def mock_open_func(file, mode="r"):
            return mock_open(read_data=file_contents[Path(file).name])()

        with (
            patch("pathlib.Path.glob", side_effect=mock_glob),
            patch("builtins.open", side_effect=mock_open_func),
            patch("pathlib.Path.is_dir", return_value=True),
            patch("pathlib.Path.exists", return_value=True),
        ):
            library = VoiceLibrary()

            # Act & Assert
            with pytest.raises(
                ValueError,
                match="Duplicate voice ID 'voice1' found in voices2.yaml for provider 'test_provider'",
            ):
                library._load_provider_voices("test_provider")
