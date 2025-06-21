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

    def test_init_with_default_library_root(self):
        """Test VoiceLibrary initialization with default library root."""
        # Arrange & Act
        library = VoiceLibrary()

        # Assert
        expected_path = (
            Path(__file__).parent.parent.parent
            / "src"
            / "script_to_speech"
            / "voice_library_data"
        )
        assert library.library_root.resolve() == expected_path.resolve()
        assert library._voice_library_cache == {}

    def test_init_with_custom_library_root(self):
        """Test VoiceLibrary initialization with custom library root."""
        # Arrange
        custom_root = Path("/custom/path")

        # Act
        library = VoiceLibrary(library_root=custom_root)

        # Assert
        assert library.library_root == custom_root
        assert library._voice_library_cache == {}

    def test_load_provider_voices_success(self):
        """Test _load_provider_voices with valid provider directory."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            provider_dir = temp_path / "test_provider"
            provider_dir.mkdir()

            # Create voice files
            voice_data1 = {
                "voices": {
                    "voice1": {"config": {"voice": "v1"}, "description": "Voice 1"},
                    "voice2": {"config": {"voice": "v2"}, "description": "Voice 2"},
                }
            }
            voice_data2 = {
                "voices": {
                    "voice3": {"config": {"voice": "v3"}, "description": "Voice 3"}
                }
            }

            voice_file1 = provider_dir / "voices1.yaml"
            voice_file2 = provider_dir / "voices2.yaml"

            with open(voice_file1, "w") as f:
                yaml.dump(voice_data1, f)
            with open(voice_file2, "w") as f:
                yaml.dump(voice_data2, f)

            library = VoiceLibrary(library_root=temp_path)

            # Act
            result = library._load_provider_voices("test_provider")

            # Assert
            expected = {
                "voice1": {"config": {"voice": "v1"}, "description": "Voice 1"},
                "voice2": {"config": {"voice": "v2"}, "description": "Voice 2"},
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

    def test_load_provider_voices_provider_not_found(self):
        """Test _load_provider_voices when provider directory doesn't exist."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            library = VoiceLibrary(library_root=Path(temp_dir))

            # Act & Assert
            with pytest.raises(
                VoiceNotFoundError,
                match="No voice library found for provider 'nonexistent'",
            ):
                library._load_provider_voices("nonexistent")

    def test_load_provider_voices_skip_schema_files(self):
        """Test _load_provider_voices skips provider_schema.yaml files."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            provider_dir = temp_path / "test_provider"
            provider_dir.mkdir()

            # Create voice file and schema file
            voice_data = {"voices": {"voice1": {"config": {"voice": "v1"}}}}
            schema_data = {"voice_properties": {"custom_prop": {"type": "text"}}}

            voice_file = provider_dir / "voices.yaml"
            schema_file = provider_dir / "provider_schema.yaml"

            with open(voice_file, "w") as f:
                yaml.dump(voice_data, f)
            with open(schema_file, "w") as f:
                yaml.dump(schema_data, f)

            library = VoiceLibrary(library_root=temp_path)

            # Act
            result = library._load_provider_voices("test_provider")

            # Assert
            expected = {"voice1": {"config": {"voice": "v1"}}}
            assert result == expected

    def test_load_provider_voices_invalid_voices_section(self):
        """Test _load_provider_voices handles invalid voices section."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            provider_dir = temp_path / "test_provider"
            provider_dir.mkdir()

            # Create file with invalid voices section
            invalid_data = {"voices": "not_a_dict"}

            voice_file = provider_dir / "invalid.yaml"
            with open(voice_file, "w") as f:
                yaml.dump(invalid_data, f)

            library = VoiceLibrary(library_root=temp_path)

            # Act
            with patch(
                "script_to_speech.voice_library.voice_library.logger"
            ) as mock_logger:
                result = library._load_provider_voices("test_provider")

            # Assert
            assert result == {}
            mock_logger.warning.assert_called_once()
            assert "Invalid voices section" in mock_logger.warning.call_args[0][0]

    def test_load_provider_voices_file_load_error(self):
        """Test _load_provider_voices handles file loading errors."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            provider_dir = temp_path / "test_provider"
            provider_dir.mkdir()

            # Create a file that will cause an error when loading
            error_file = provider_dir / "error.yaml"
            error_file.touch()

            library = VoiceLibrary(library_root=temp_path)

            # Act
            with patch("builtins.open", side_effect=IOError("File read error")):
                with patch(
                    "script_to_speech.voice_library.voice_library.logger"
                ) as mock_logger:
                    result = library._load_provider_voices("test_provider")

            # Assert
            assert result == {}
            mock_logger.error.assert_called_once()
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

    def test_expand_config_provider_not_found(self):
        """Test expand_config when provider is not found."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            library = VoiceLibrary(library_root=Path(temp_dir))

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
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            provider_dir = temp_path / "test_provider"
            provider_dir.mkdir()

            # Create file without voices section
            no_voices_data = {"metadata": {"provider": "test"}}

            voice_file = provider_dir / "no_voices.yaml"
            with open(voice_file, "w") as f:
                yaml.dump(no_voices_data, f)

            library = VoiceLibrary(library_root=temp_path)

            # Act
            result = library._load_provider_voices("test_provider")

            # Assert
            assert result == {}

    def test_load_provider_voices_empty_file(self):
        """Test _load_provider_voices handles empty YAML files."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            provider_dir = temp_path / "test_provider"
            provider_dir.mkdir()

            # Create empty file
            empty_file = provider_dir / "empty.yaml"
            empty_file.touch()

            library = VoiceLibrary(library_root=temp_path)

            # Act
            result = library._load_provider_voices("test_provider")

            # Assert
            assert result == {}

    def test_load_provider_voices_duplicate_voice_ids(self):
        """Test _load_provider_voices raises error on duplicate voice IDs across files."""
        # Arrange
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            provider_dir = temp_path / "test_provider"
            provider_dir.mkdir()

            # Create two files with overlapping voice IDs
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

            voice_file1 = provider_dir / "voices1.yaml"
            voice_file2 = provider_dir / "voices2.yaml"

            with open(voice_file1, "w") as f:
                yaml.dump(voice_data1, f)
            with open(voice_file2, "w") as f:
                yaml.dump(voice_data2, f)

            library = VoiceLibrary(library_root=temp_path)

            # Act & Assert
            with pytest.raises(
                ValueError,
                match="Duplicate voice ID 'voice1' found in voices2.yaml for provider 'test_provider'",
            ):
                library._load_provider_voices("test_provider")
