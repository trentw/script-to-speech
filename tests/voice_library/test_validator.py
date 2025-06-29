"""Tests for voice library validator functionality."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
import yaml

from script_to_speech.voice_library.validator import VoiceLibraryValidator


class TestVoiceLibraryValidator:
    """Tests for the VoiceLibraryValidator class."""

    def test_init_default(self):
        """Test VoiceLibraryValidator initialization with default settings."""
        # Arrange & Act
        validator = VoiceLibraryValidator()

        # Assert
        assert validator.project_only == False
        assert validator.validation_errors == []

    def test_init_project_only(self):
        """Test VoiceLibraryValidator initialization with project_only=True."""
        # Arrange & Act
        validator = VoiceLibraryValidator(project_only=True)

        # Assert
        assert validator.project_only == True
        assert validator.validation_errors == []

    def test_load_yaml_file_success(self):
        """Test _load_yaml_file with valid YAML file."""
        # Arrange
        validator = VoiceLibraryValidator()
        test_data = {"test": "data", "nested": {"key": "value"}}
        yaml_content = yaml.dump(test_data)

        # Act
        with patch("builtins.open", mock_open(read_data=yaml_content)):
            with patch("pathlib.Path.exists", return_value=True):
                result = validator._load_yaml_file(Path("test.yaml"), "Test file")

        # Assert
        assert result == test_data
        assert validator.validation_errors == []

    def test_load_yaml_file_not_found(self):
        """Test _load_yaml_file when file doesn't exist."""
        # Arrange
        validator = VoiceLibraryValidator()
        file_path = Path("nonexistent.yaml")

        # Act
        with patch("pathlib.Path.exists", return_value=False):
            result = validator._load_yaml_file(file_path, "Test file")

        # Assert
        assert result is None
        assert len(validator.validation_errors) == 1
        assert "Test file not found at" in validator.validation_errors[0]

    def test_load_yaml_file_empty_file(self):
        """Test _load_yaml_file with empty YAML file."""
        # Arrange
        validator = VoiceLibraryValidator()

        # Act
        with patch("builtins.open", mock_open(read_data="")):
            with patch("pathlib.Path.exists", return_value=True):
                result = validator._load_yaml_file(Path("empty.yaml"), "Empty file")

        # Assert
        assert result is None
        assert len(validator.validation_errors) == 1
        assert "Empty file is empty" in validator.validation_errors[0]

    def test_load_yaml_file_invalid_yaml(self):
        """Test _load_yaml_file with invalid YAML content."""
        # Arrange
        validator = VoiceLibraryValidator()
        invalid_yaml = "invalid: yaml: content: ["

        # Act
        with patch("builtins.open", mock_open(read_data=invalid_yaml)):
            with patch("pathlib.Path.exists", return_value=True):
                result = validator._load_yaml_file(Path("invalid.yaml"), "Invalid file")

        # Assert
        assert result is None
        assert len(validator.validation_errors) == 1
        assert "YAML error in Invalid file:" in validator.validation_errors[0]

    def test_load_yaml_file_non_dict_content(self):
        """Test _load_yaml_file with non-dictionary YAML content."""
        # Arrange
        validator = VoiceLibraryValidator()
        list_yaml = "- item1\n- item2"

        # Act
        with patch("builtins.open", mock_open(read_data=list_yaml)):
            with patch("pathlib.Path.exists", return_value=True):
                result = validator._load_yaml_file(Path("list.yaml"), "List file")

        # Assert
        assert result is None
        assert len(validator.validation_errors) == 1
        assert "List file must be a dictionary" in validator.validation_errors[0]

    def test_schema_merging_integration(self):
        """Test that schema merging works through the schema utility."""
        # Arrange
        from script_to_speech.voice_library.schema_utils import merge_schemas

        global_schema = {
            "voice_properties": {
                "age": {"type": "range", "min": 0.0, "max": 1.0},
                "gender": {"type": "enum", "values": ["masculine", "feminine"]},
            }
        }
        provider_schema = {
            "voice_properties": {"custom_prop": {"type": "text"}},
            "provider_specific": {"key": "value"},
        }

        # Act
        result = merge_schemas([global_schema, provider_schema])

        # Assert
        expected = {
            "voice_properties": {
                "age": {"type": "range", "min": 0.0, "max": 1.0},
                "gender": {"type": "enum", "values": ["masculine", "feminine"]},
                "custom_prop": {"type": "text"},
            },
            "provider_specific": {"key": "value"},
        }
        assert result == expected

    def test_validate_property_value_range_valid(self):
        """Test _validate_property_value with valid range property."""
        # Arrange
        validator = VoiceLibraryValidator()
        prop_schema = {"type": "range", "min": 0.0, "max": 1.0}

        # Act
        validator._validate_property_value("test_voice", "age", 0.5, prop_schema)

        # Assert
        assert validator.validation_errors == []

    def test_validate_property_value_range_invalid_type(self):
        """Test _validate_property_value with invalid type for range property."""
        # Arrange
        validator = VoiceLibraryValidator()
        prop_schema = {"type": "range", "min": 0.0, "max": 1.0}

        # Act
        validator._validate_property_value("test_voice", "age", "invalid", prop_schema)

        # Assert
        assert len(validator.validation_errors) == 1
        assert "Property 'age' must be a number" in validator.validation_errors[0]

    def test_validate_property_value_range_out_of_bounds(self):
        """Test _validate_property_value with out-of-bounds range value."""
        # Arrange
        validator = VoiceLibraryValidator()
        prop_schema = {"type": "range", "min": 0.0, "max": 1.0}

        # Act
        validator._validate_property_value("test_voice", "age", 1.5, prop_schema)

        # Assert
        assert len(validator.validation_errors) == 1
        assert "value 1.5 outside range [0.0, 1.0]" in validator.validation_errors[0]

    def test_validate_property_value_enum_valid(self):
        """Test _validate_property_value with valid enum property."""
        # Arrange
        validator = VoiceLibraryValidator()
        prop_schema = {
            "type": "enum",
            "values": ["masculine", "feminine", "androgynous"],
        }

        # Act
        validator._validate_property_value(
            "test_voice", "gender", "masculine", prop_schema
        )

        # Assert
        assert validator.validation_errors == []

    def test_validate_property_value_enum_invalid(self):
        """Test _validate_property_value with invalid enum value."""
        # Arrange
        validator = VoiceLibraryValidator()
        prop_schema = {"type": "enum", "values": ["masculine", "feminine"]}

        # Act
        validator._validate_property_value(
            "test_voice", "gender", "invalid", prop_schema
        )

        # Assert
        assert len(validator.validation_errors) == 1
        assert (
            "not in allowed values: ['masculine', 'feminine']"
            in validator.validation_errors[0]
        )

    def test_validate_property_value_boolean_valid(self):
        """Test _validate_property_value with valid boolean property."""
        # Arrange
        validator = VoiceLibraryValidator()
        prop_schema = {"type": "boolean"}

        # Act
        validator._validate_property_value("test_voice", "enabled", True, prop_schema)

        # Assert
        assert validator.validation_errors == []

    def test_validate_property_value_boolean_invalid(self):
        """Test _validate_property_value with invalid boolean value."""
        # Arrange
        validator = VoiceLibraryValidator()
        prop_schema = {"type": "boolean"}

        # Act
        validator._validate_property_value("test_voice", "enabled", "true", prop_schema)

        # Assert
        assert len(validator.validation_errors) == 1
        assert "Property 'enabled' must be a boolean" in validator.validation_errors[0]

    def test_validate_property_value_text_valid(self):
        """Test _validate_property_value with valid text property."""
        # Arrange
        validator = VoiceLibraryValidator()
        prop_schema = {"type": "text"}

        # Act
        validator._validate_property_value(
            "test_voice", "description", "Valid text", prop_schema
        )

        # Assert
        assert validator.validation_errors == []

    def test_validate_property_value_text_invalid(self):
        """Test _validate_property_value with invalid text value."""
        # Arrange
        validator = VoiceLibraryValidator()
        prop_schema = {"type": "text"}

        # Act
        validator._validate_property_value(
            "test_voice", "description", 123, prop_schema
        )

        # Assert
        assert len(validator.validation_errors) == 1
        assert (
            "Property 'description' must be a string" in validator.validation_errors[0]
        )

    def test_check_mirror_properties_conflict(self):
        """Test _check_mirror_properties detects mirror property conflicts."""
        # Arrange
        validator = VoiceLibraryValidator()
        properties = {"prop1": 0.5, "prop2": 0.7}
        schema_properties = {
            "prop1": {"type": "range"},
            "prop2": {"type": "range", "mirror_of": "prop1"},
        }

        # Act
        validator._check_mirror_properties("test_voice", properties, schema_properties)

        # Assert
        assert len(validator.validation_errors) == 1
        assert (
            "Cannot specify both mirror properties 'prop1' and 'prop2'"
            in validator.validation_errors[0]
        )

    def test_check_mirror_properties_no_conflict(self):
        """Test _check_mirror_properties with no mirror property conflicts."""
        # Arrange
        validator = VoiceLibraryValidator()
        properties = {"prop1": 0.5}
        schema_properties = {
            "prop1": {"type": "range"},
            "prop2": {"type": "range", "mirror_of": "prop1"},
        }

        # Act
        validator._check_mirror_properties("test_voice", properties, schema_properties)

        # Assert
        assert validator.validation_errors == []

    def test_validate_voice_config_success(self):
        """Test _validate_voice_config with valid configuration."""
        # Arrange
        validator = VoiceLibraryValidator()
        config = {"voice": "test_voice", "model": "test_model"}

        mock_provider_class = MagicMock()
        mock_provider_class.validate_speaker_config = MagicMock()

        # Act
        with patch(
            "script_to_speech.voice_library.validator.TTSProviderManager._get_provider_class",
            return_value=mock_provider_class,
        ):
            validator._validate_voice_config("test_voice", config, "test_provider")

        # Assert
        assert validator.validation_errors == []
        mock_provider_class.validate_speaker_config.assert_called_once_with(
            {"voice": "test_voice", "model": "test_model", "provider": "test_provider"}
        )

    def test_validate_voice_config_invalid_config(self):
        """Test _validate_voice_config with invalid configuration."""
        # Arrange
        validator = VoiceLibraryValidator()
        config = "not_a_dict"

        # Act
        validator._validate_voice_config("test_voice", config, "test_provider")

        # Assert
        assert len(validator.validation_errors) == 1
        assert "'config' must be a dictionary" in validator.validation_errors[0]

    def test_validate_voice_config_provider_validation_error(self):
        """Test _validate_voice_config when provider validation fails."""
        # Arrange
        validator = VoiceLibraryValidator()
        config = {"voice": "invalid_voice"}

        mock_provider_class = MagicMock()
        mock_provider_class.validate_speaker_config.side_effect = Exception(
            "Invalid voice configuration"
        )

        # Act
        with patch(
            "script_to_speech.voice_library.validator.TTSProviderManager._get_provider_class",
            return_value=mock_provider_class,
        ):
            validator._validate_voice_config("test_voice", config, "test_provider")

        # Assert
        assert len(validator.validation_errors) == 1
        assert (
            "Invalid TTS config - Invalid voice configuration"
            in validator.validation_errors[0]
        )

    def test_validate_all_missing_global_schema(self):
        """Test validate_all when global schema is missing."""
        # Arrange
        with (
            patch(
                "script_to_speech.voice_library.validator.load_merged_schemas_for_providers",
                side_effect=ValueError("No schema files found"),
            ),
            patch(
                "pathlib.Path.glob",
                return_value=[Path("/fake/openai/voices.yaml")],
            ),
            patch(
                "builtins.open",
                mock_open(read_data='voices:\n  test: {}\n"'),
            ),
            patch("pathlib.Path.is_dir", return_value=True),
        ):
            validator = VoiceLibraryValidator()

            # Act
            is_valid, errors = validator.validate_all()

            # Assert
            assert not is_valid
            assert len(errors) >= 1
            assert any("Schema error" in error for error in errors)

    def test_validate_all_success(self):
        """Test validate_all with successful validation."""
        # Arrange
        schema_content = {
            "voice_properties": {"age": {"type": "range", "min": 0.0, "max": 1.0}}
        }
        voice_content = {
            "voices": {
                "test_voice": {
                    "config": {"voice": "test"},
                    "voice_properties": {"age": 0.5},
                    "description": {"text": "Test voice"},
                }
            }
        }

        with (
            patch(
                "script_to_speech.voice_library.validator.load_merged_schemas_for_providers",
                return_value=schema_content,
            ),
            patch(
                "pathlib.Path.glob",
                return_value=[Path("/fake/test_provider/voices.yaml")],
            ),
            patch(
                "builtins.open",
                mock_open(read_data=yaml.dump(voice_content)),
            ),
            patch("pathlib.Path.is_dir", return_value=True),
            patch("pathlib.Path.exists", return_value=True),
        ):
            validator = VoiceLibraryValidator()

            mock_provider_class = MagicMock()
            mock_provider_class.validate_speaker_config = MagicMock()

            # Act
            with patch(
                "script_to_speech.voice_library.validator.TTSProviderManager._get_provider_class",
                return_value=mock_provider_class,
            ):
                is_valid, errors = validator.validate_all()

            # Assert
            assert is_valid
            assert errors == []
