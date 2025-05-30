"""Tests for tts_providers/utils.py."""

import json
import tempfile
from pathlib import Path
from typing import List, Optional
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest
from ruamel.yaml.constructor import DuplicateKeyError

from script_to_speech.tts_providers.utils import (
    _handle_yaml_operation,
    _load_processed_chunks,
    _print_validation_report,
    generate_yaml_config,
    populate_multi_provider_yaml,
    validate_yaml_config,
)


class TestHandleYamlOperation:
    """Tests for _handle_yaml_operation function."""

    @patch("script_to_speech.tts_providers.utils.TTSProviderManager")
    @patch("script_to_speech.tts_providers.utils.TextProcessorManager")
    @patch("script_to_speech.tts_providers.utils.get_text_processor_configs")
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.load")
    def test_generate_new_yaml_success(
        self,
        mock_json_load,
        mock_file,
        mock_get_configs,
        mock_processor_manager,
        mock_tts_manager,
    ):
        """Test successful generation of new YAML configuration."""
        # Arrange
        input_json_path = Path("test_input.json")
        chunks = [{"type": "dialogue", "speaker": "Alice", "text": "Hello"}]
        processed_chunks = [
            {"type": "dialogue", "speaker": "Alice", "text": "Hello processed"}
        ]

        mock_json_load.return_value = chunks
        mock_get_configs.return_value = ["config1.yaml"]

        mock_processor = Mock()
        mock_processor.process_chunks.return_value = processed_chunks
        mock_processor_manager.return_value = mock_processor

        mock_tts = Mock()
        mock_tts_manager.return_value = mock_tts

        # Act
        result = _handle_yaml_operation(
            input_json_path=input_json_path, provider="test_provider"
        )

        # Assert
        expected_output = (
            input_json_path.parent / f"{input_json_path.stem}_voice_config.yaml"
        )
        assert result == expected_output

        mock_tts.generate_yaml_config.assert_called_once_with(
            processed_chunks, expected_output, "test_provider", False
        )
        mock_processor.process_chunks.assert_called_once_with(chunks)

    @patch("script_to_speech.tts_providers.utils.TTSProviderManager")
    @patch("script_to_speech.tts_providers.utils.TextProcessorManager")
    @patch("script_to_speech.tts_providers.utils.get_text_processor_configs")
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.load")
    def test_populate_existing_yaml_success(
        self,
        mock_json_load,
        mock_file,
        mock_get_configs,
        mock_processor_manager,
        mock_tts_manager,
    ):
        """Test successful population of existing YAML configuration."""
        # Arrange
        input_json_path = Path("test_input.json")
        existing_yaml_path = Path("existing_config.yaml")
        chunks = [{"type": "dialogue", "speaker": "Bob", "text": "Hi"}]
        processed_chunks = [
            {"type": "dialogue", "speaker": "Bob", "text": "Hi processed"}
        ]

        mock_json_load.return_value = chunks
        mock_get_configs.return_value = ["config1.yaml"]

        mock_processor = Mock()
        mock_processor.process_chunks.return_value = processed_chunks
        mock_processor_manager.return_value = mock_processor

        mock_tts = Mock()
        mock_tts_manager.return_value = mock_tts

        # Act
        result = _handle_yaml_operation(
            input_json_path=input_json_path,
            existing_yaml_path=existing_yaml_path,
            include_optional_fields=True,
        )

        # Assert
        expected_output = (
            existing_yaml_path.parent / f"{existing_yaml_path.stem}_populated.yaml"
        )
        assert result == expected_output

        mock_tts.update_yaml_with_provider_fields_preserving_comments.assert_called_once_with(
            existing_yaml_path, expected_output, processed_chunks, True
        )

    @patch("script_to_speech.tts_providers.utils.get_text_processor_configs")
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.load")
    def test_handle_yaml_operation_json_error(
        self, mock_json_load, mock_file, mock_get_configs
    ):
        """Test error handling when JSON loading fails."""
        # Arrange
        input_json_path = Path("invalid.json")
        mock_json_load.side_effect = json.JSONDecodeError("Invalid JSON", "doc", 0)

        # Act & Assert
        with pytest.raises(json.JSONDecodeError):
            _handle_yaml_operation(input_json_path=input_json_path)

    @patch("script_to_speech.tts_providers.utils.TTSProviderManager")
    @patch("script_to_speech.tts_providers.utils.TextProcessorManager")
    @patch("script_to_speech.tts_providers.utils.get_text_processor_configs")
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.load")
    def test_handle_yaml_operation_processor_error(
        self,
        mock_json_load,
        mock_file,
        mock_get_configs,
        mock_processor_manager,
        mock_tts_manager,
    ):
        """Test error handling when text processing fails."""
        # Arrange
        input_json_path = Path("test_input.json")
        chunks = [{"type": "dialogue", "speaker": "Alice", "text": "Hello"}]

        mock_json_load.return_value = chunks
        mock_get_configs.return_value = ["config1.yaml"]

        mock_processor = Mock()
        mock_processor.process_chunks.side_effect = Exception("Processing failed")
        mock_processor_manager.return_value = mock_processor

        # Act & Assert
        with pytest.raises(Exception, match="Processing failed"):
            _handle_yaml_operation(input_json_path=input_json_path)


class TestGenerateYamlConfig:
    """Tests for generate_yaml_config function."""

    @patch("script_to_speech.tts_providers.utils._handle_yaml_operation")
    def test_generate_yaml_config_calls_handle_operation(self, mock_handle):
        """Test that generate_yaml_config properly calls _handle_yaml_operation."""
        # Arrange
        input_json_path = Path("test.json")
        processing_configs = [Path("config1.yaml"), Path("config2.yaml")]
        provider = "test_provider"
        expected_output = Path("output.yaml")

        mock_handle.return_value = expected_output

        # Act
        result = generate_yaml_config(
            input_json_path=input_json_path,
            processing_configs=processing_configs,
            provider=provider,
            include_optional_fields=True,
        )

        # Assert
        assert result == expected_output
        mock_handle.assert_called_once_with(
            input_json_path, processing_configs, provider, None, True
        )


class TestPopulateMultiProviderYaml:
    """Tests for populate_multi_provider_yaml function."""

    @patch("script_to_speech.tts_providers.utils._handle_yaml_operation")
    def test_populate_multi_provider_yaml_calls_handle_operation(self, mock_handle):
        """Test that populate_multi_provider_yaml properly calls _handle_yaml_operation."""
        # Arrange
        input_json_path = Path("test.json")
        voice_config_yaml_path = Path("config.yaml")
        processing_configs = [Path("proc1.yaml")]
        expected_output = Path("populated.yaml")

        mock_handle.return_value = expected_output

        # Act
        result = populate_multi_provider_yaml(
            input_json_path=input_json_path,
            voice_config_yaml_path=voice_config_yaml_path,
            processing_configs=processing_configs,
            include_optional_fields=False,
        )

        # Assert
        assert result == expected_output
        mock_handle.assert_called_once_with(
            input_json_path, processing_configs, None, voice_config_yaml_path, False
        )


class TestLoadProcessedChunks:
    """Tests for _load_processed_chunks function."""

    @patch("script_to_speech.tts_providers.utils.TextProcessorManager")
    @patch("script_to_speech.tts_providers.utils.get_text_processor_configs")
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.load")
    def test_load_processed_chunks_success(
        self, mock_json_load, mock_file, mock_get_configs, mock_processor_manager
    ):
        """Test successful loading and processing of chunks."""
        # Arrange
        input_json_path = Path("test.json")
        text_processor_configs = [Path("config.yaml")]
        chunks = [{"type": "dialogue", "speaker": "Alice", "text": "Hello"}]
        processed_chunks = [
            {"type": "dialogue", "speaker": "Alice", "text": "Hello processed"}
        ]

        mock_json_load.return_value = chunks
        mock_get_configs.return_value = ["generated_config.yaml"]

        mock_processor = Mock()
        mock_processor.process_chunks.return_value = processed_chunks
        mock_processor_manager.return_value = mock_processor

        # Act
        result = _load_processed_chunks(input_json_path, text_processor_configs)

        # Assert
        assert result == processed_chunks
        mock_get_configs.assert_called_once_with(
            input_json_path, text_processor_configs
        )
        mock_processor.process_chunks.assert_called_once_with(chunks)

    @patch("builtins.open", new_callable=mock_open)
    @patch("json.load")
    def test_load_processed_chunks_file_not_found(self, mock_json_load, mock_file):
        """Test error handling when input file doesn't exist."""
        # Arrange
        input_json_path = Path("nonexistent.json")
        mock_file.side_effect = FileNotFoundError("File not found")

        # Act & Assert
        with pytest.raises(FileNotFoundError):
            _load_processed_chunks(input_json_path, None)


class TestValidateYamlConfig:
    """Tests for validate_yaml_config function."""

    @patch("script_to_speech.tts_providers.utils._load_processed_chunks")
    @patch("builtins.open", new_callable=mock_open)
    def test_validate_yaml_config_no_issues(self, mock_file, mock_load_chunks):
        """Test validation with no issues found."""
        # Arrange
        input_json_path = Path("test.json")
        voice_config_yaml_path = Path("config.yaml")

        # Mock processed chunks with speakers
        processed_chunks = [
            {"type": "dialogue", "speaker": "Alice", "text": "Hello"},
            {"type": "dialogue", "speaker": "Bob", "text": "Hi"},
            {"type": "action", "text": "Scene description"},
        ]
        mock_load_chunks.return_value = processed_chunks

        # Mock YAML content
        yaml_content = """
Alice:
  provider: test_provider
  voice_id: alice_voice
Bob:
  provider: test_provider
  voice_id: bob_voice
default:
  provider: test_provider
  voice_id: default_voice
"""
        mock_file.return_value.read.return_value = yaml_content

        with patch("script_to_speech.tts_providers.utils.YAML") as mock_yaml_class:
            mock_yaml = Mock()
            mock_yaml_class.return_value = mock_yaml
            mock_yaml.load.return_value = {
                "Alice": {"provider": "test_provider", "voice_id": "alice_voice"},
                "Bob": {"provider": "test_provider", "voice_id": "bob_voice"},
                "default": {"provider": "test_provider", "voice_id": "default_voice"},
            }

            # Act
            missing, extra, duplicates, invalid = validate_yaml_config(
                input_json_path, voice_config_yaml_path
            )

            # Assert
            assert missing == []
            assert extra == []
            assert duplicates == []
            assert invalid == {}

    @patch("script_to_speech.tts_providers.utils._load_processed_chunks")
    @patch("builtins.open", new_callable=mock_open)
    def test_validate_yaml_config_missing_speakers(self, mock_file, mock_load_chunks):
        """Test validation with missing speakers in YAML."""
        # Arrange
        input_json_path = Path("test.json")
        voice_config_yaml_path = Path("config.yaml")

        # Mock processed chunks with more speakers than in YAML
        processed_chunks = [
            {"type": "dialogue", "speaker": "Alice", "text": "Hello"},
            {"type": "dialogue", "speaker": "Bob", "text": "Hi"},
            {"type": "dialogue", "speaker": "Charlie", "text": "Hey"},
        ]
        mock_load_chunks.return_value = processed_chunks

        yaml_content = """
Alice:
  provider: test_provider
Bob:
  provider: test_provider
"""
        mock_file.return_value.read.return_value = yaml_content

        with patch("script_to_speech.tts_providers.utils.YAML") as mock_yaml_class:
            mock_yaml = Mock()
            mock_yaml_class.return_value = mock_yaml
            mock_yaml.load.return_value = {
                "Alice": {"provider": "test_provider"},
                "Bob": {"provider": "test_provider"},
            }

            # Act
            missing, extra, duplicates, invalid = validate_yaml_config(
                input_json_path, voice_config_yaml_path
            )

            # Assert
            assert "Charlie" in missing
            assert extra == []
            assert duplicates == []
            assert invalid == {}

    @patch("script_to_speech.tts_providers.utils._load_processed_chunks")
    @patch("builtins.open", new_callable=mock_open)
    def test_validate_yaml_config_extra_speakers(self, mock_file, mock_load_chunks):
        """Test validation with extra speakers in YAML."""
        # Arrange
        input_json_path = Path("test.json")
        voice_config_yaml_path = Path("config.yaml")

        # Mock processed chunks with fewer speakers than in YAML
        processed_chunks = [
            {"type": "dialogue", "speaker": "Alice", "text": "Hello"},
        ]
        mock_load_chunks.return_value = processed_chunks

        yaml_content = """
Alice:
  provider: test_provider
Bob:
  provider: test_provider
Charlie:
  provider: test_provider
"""
        mock_file.return_value.read.return_value = yaml_content

        with patch("script_to_speech.tts_providers.utils.YAML") as mock_yaml_class:
            mock_yaml = Mock()
            mock_yaml_class.return_value = mock_yaml
            mock_yaml.load.return_value = {
                "Alice": {"provider": "test_provider"},
                "Bob": {"provider": "test_provider"},
                "Charlie": {"provider": "test_provider"},
            }

            # Act
            missing, extra, duplicates, invalid = validate_yaml_config(
                input_json_path, voice_config_yaml_path
            )

            # Assert
            assert missing == []
            assert "Bob" in extra
            assert "Charlie" in extra
            assert duplicates == []
            assert invalid == {}

    @patch("script_to_speech.tts_providers.utils._load_processed_chunks")
    def test_validate_yaml_config_duplicate_keys(self, mock_load_chunks):
        """Test validation with duplicate keys in YAML."""
        # Arrange
        input_json_path = Path("test.json")
        voice_config_yaml_path = Path("config.yaml")

        processed_chunks = [
            {"type": "dialogue", "speaker": "Alice", "text": "Hello"},
        ]
        mock_load_chunks.return_value = processed_chunks

        # Mock YAML file content with duplicates
        yaml_lines = [
            "Alice:\n",
            "  provider: test_provider1\n",
            "Bob:\n",
            "  provider: test_provider2\n",
            "Alice:\n",  # Duplicate key
            "  provider: test_provider3\n",
        ]

        with patch("script_to_speech.tts_providers.utils.YAML") as mock_yaml_class:
            mock_yaml = Mock()
            mock_yaml_class.return_value = mock_yaml

            # First call raises DuplicateKeyError
            mock_yaml.load.side_effect = [
                DuplicateKeyError('found duplicate key "Alice"'),
                {
                    "Alice": {"provider": "test_provider3"},
                    "Bob": {"provider": "test_provider2"},
                },
            ]

            with patch("builtins.open", mock_open()) as mock_file:
                # Mock file reading for duplicate detection
                mock_file.return_value.readlines.return_value = yaml_lines

                # Act
                missing, extra, duplicates, invalid = validate_yaml_config(
                    input_json_path, voice_config_yaml_path
                )

                # Assert
                assert "Alice" in duplicates
                assert len(duplicates) == 1

    @patch("script_to_speech.tts_providers.utils._load_processed_chunks")
    @patch("builtins.open", new_callable=mock_open)
    def test_validate_yaml_config_strict_mode_invalid_config(
        self, mock_file, mock_load_chunks
    ):
        """Test validation in strict mode with invalid provider configuration."""
        # Arrange
        input_json_path = Path("test.json")
        voice_config_yaml_path = Path("config.yaml")

        processed_chunks = [
            {"type": "dialogue", "speaker": "Alice", "text": "Hello"},
        ]
        mock_load_chunks.return_value = processed_chunks

        yaml_content = """
Alice:
  provider: test_provider
  invalid_field: invalid_value
"""
        mock_file.return_value.read.return_value = yaml_content

        with patch("script_to_speech.tts_providers.utils.YAML") as mock_yaml_class:
            mock_yaml = Mock()
            mock_yaml_class.return_value = mock_yaml
            mock_yaml.load.return_value = {
                "Alice": {"provider": "test_provider", "invalid_field": "invalid_value"}
            }

            # Mock TTSProviderManager for strict validation
            with patch(
                "script_to_speech.tts_providers.tts_provider_manager.TTSProviderManager"
            ) as mock_manager:
                mock_provider_class = Mock()
                mock_provider_class.validate_speaker_config.side_effect = Exception(
                    "Invalid config"
                )
                mock_manager._get_provider_class.return_value = mock_provider_class

                # Act
                missing, extra, duplicates, invalid = validate_yaml_config(
                    input_json_path, voice_config_yaml_path, strict=True
                )

                # Assert
                assert missing == []
                assert extra == []
                assert duplicates == []
                assert "Alice" in invalid
                assert "Invalid config" in invalid["Alice"]

    @patch("script_to_speech.tts_providers.utils._load_processed_chunks")
    @patch("builtins.open", new_callable=mock_open)
    def test_validate_yaml_config_strict_mode_missing_provider(
        self, mock_file, mock_load_chunks
    ):
        """Test validation in strict mode with missing provider field."""
        # Arrange
        input_json_path = Path("test.json")
        voice_config_yaml_path = Path("config.yaml")

        processed_chunks = [
            {"type": "dialogue", "speaker": "Alice", "text": "Hello"},
        ]
        mock_load_chunks.return_value = processed_chunks

        yaml_content = """
Alice:
  voice_id: alice_voice
"""
        mock_file.return_value.read.return_value = yaml_content

        with patch("script_to_speech.tts_providers.utils.YAML") as mock_yaml_class:
            mock_yaml = Mock()
            mock_yaml_class.return_value = mock_yaml
            mock_yaml.load.return_value = {"Alice": {"voice_id": "alice_voice"}}

            # Act
            missing, extra, duplicates, invalid = validate_yaml_config(
                input_json_path, voice_config_yaml_path, strict=True
            )

            # Assert
            assert missing == []
            assert extra == []
            assert duplicates == []
            assert "Alice" in invalid
            assert "Missing required 'provider' field" in invalid["Alice"]

    @patch("script_to_speech.tts_providers.utils._load_processed_chunks")
    @patch("builtins.open", new_callable=mock_open)
    def test_validate_yaml_config_strict_mode_non_dict_config(
        self, mock_file, mock_load_chunks
    ):
        """Test validation in strict mode with non-dictionary configuration."""
        # Arrange
        input_json_path = Path("test.json")
        voice_config_yaml_path = Path("config.yaml")

        processed_chunks = [
            {"type": "dialogue", "speaker": "Alice", "text": "Hello"},
        ]
        mock_load_chunks.return_value = processed_chunks

        yaml_content = """
Alice: "not a dictionary"
"""
        mock_file.return_value.read.return_value = yaml_content

        with patch("script_to_speech.tts_providers.utils.YAML") as mock_yaml_class:
            mock_yaml = Mock()
            mock_yaml_class.return_value = mock_yaml
            mock_yaml.load.return_value = {"Alice": "not a dictionary"}

            # Act
            missing, extra, duplicates, invalid = validate_yaml_config(
                input_json_path, voice_config_yaml_path, strict=True
            )

            # Assert
            assert missing == []
            assert extra == []
            assert duplicates == []
            assert "Alice" in invalid
            assert "Configuration must be a mapping/dictionary" in invalid["Alice"]

    @patch("script_to_speech.tts_providers.utils._load_processed_chunks")
    @patch("builtins.open", new_callable=mock_open)
    def test_validate_yaml_config_invalid_yaml_structure(
        self, mock_file, mock_load_chunks
    ):
        """Test validation with invalid YAML structure (not a dictionary)."""
        # Arrange
        input_json_path = Path("test.json")
        voice_config_yaml_path = Path("config.yaml")

        processed_chunks = [
            {"type": "dialogue", "speaker": "Alice", "text": "Hello"},
        ]
        mock_load_chunks.return_value = processed_chunks

        yaml_content = "- not a dictionary"
        mock_file.return_value.read.return_value = yaml_content

        with patch("script_to_speech.tts_providers.utils.YAML") as mock_yaml_class:
            mock_yaml = Mock()
            mock_yaml_class.return_value = mock_yaml
            mock_yaml.load.return_value = ["not a dictionary"]

            # Act & Assert
            with pytest.raises(ValueError, match="YAML config must be a mapping"):
                validate_yaml_config(input_json_path, voice_config_yaml_path)

    @patch("script_to_speech.tts_providers.utils._load_processed_chunks")
    @patch("builtins.open", new_callable=mock_open)
    def test_validate_yaml_config_handles_none_speaker(
        self, mock_file, mock_load_chunks
    ):
        """Test validation handles None speaker values correctly."""
        # Arrange
        input_json_path = Path("test.json")
        voice_config_yaml_path = Path("config.yaml")

        # Mock processed chunks with None speaker (should become "default")
        processed_chunks = [
            {"type": "dialogue", "speaker": None, "text": "Hello"},
            {"type": "action", "text": "Scene description"},  # No speaker field
        ]
        mock_load_chunks.return_value = processed_chunks

        yaml_content = """
default:
  provider: test_provider
  voice_id: default_voice
"""
        mock_file.return_value.read.return_value = yaml_content

        with patch("script_to_speech.tts_providers.utils.YAML") as mock_yaml_class:
            mock_yaml = Mock()
            mock_yaml_class.return_value = mock_yaml
            mock_yaml.load.return_value = {
                "default": {"provider": "test_provider", "voice_id": "default_voice"}
            }

            # Act
            missing, extra, duplicates, invalid = validate_yaml_config(
                input_json_path, voice_config_yaml_path
            )

            # Assert
            assert missing == []
            assert extra == []
            assert duplicates == []
            assert invalid == {}


class TestPrintValidationReport:
    """Tests for _print_validation_report function."""

    def test_print_validation_report_no_issues(self, capsys):
        """Test printing validation report with no issues."""
        # Arrange
        missing_speakers = []
        extra_speakers = []
        duplicate_speakers = []
        invalid_configs = {}

        # Act
        _print_validation_report(
            missing_speakers, extra_speakers, duplicate_speakers, invalid_configs
        )

        # Assert
        captured = capsys.readouterr()
        assert "✓ Validation successful: no issues found." in captured.out
        assert "VALIDATION RESULTS" in captured.out

    def test_print_validation_report_with_issues(self, capsys):
        """Test printing validation report with various issues."""
        # Arrange
        missing_speakers = ["Alice", "Bob"]
        extra_speakers = ["Charlie"]
        duplicate_speakers = ["Dave"]
        invalid_configs = {"Eve": "Missing provider field"}

        # Act
        _print_validation_report(
            missing_speakers, extra_speakers, duplicate_speakers, invalid_configs
        )

        # Assert
        captured = capsys.readouterr()
        assert "with issues:" in captured.out
        assert "Missing speaker(s) in YAML: Alice, Bob" in captured.out
        assert "Extra speaker(s) in YAML: Charlie" in captured.out
        assert "Duplicate speaker(s) in YAML: Dave" in captured.out
        assert "Invalid configuration for 1 speaker(s):" in captured.out
        assert "Eve: Missing provider field" in captured.out

    def test_print_validation_report_only_missing(self, capsys):
        """Test printing validation report with only missing speakers."""
        # Arrange
        missing_speakers = ["Alice"]
        extra_speakers = []
        duplicate_speakers = []
        invalid_configs = {}

        # Act
        _print_validation_report(
            missing_speakers, extra_speakers, duplicate_speakers, invalid_configs
        )

        # Assert
        captured = capsys.readouterr()
        assert "completed with issues:" in captured.out
        assert "Missing speaker(s) in YAML: Alice" in captured.out
        # Should not contain other issue types
        assert "Extra speaker(s) in YAML:" not in captured.out
        assert "Duplicate speaker(s) in YAML:" not in captured.out
        assert "Invalid configuration" not in captured.out

    def test_print_validation_report_only_invalid_configs(self, capsys):
        """Test printing validation report with only invalid configurations."""
        # Arrange
        missing_speakers = []
        extra_speakers = []
        duplicate_speakers = []
        invalid_configs = {
            "Alice": "Missing provider field",
            "Bob": "Invalid voice configuration",
        }

        # Act
        _print_validation_report(
            missing_speakers, extra_speakers, duplicate_speakers, invalid_configs
        )

        # Assert
        captured = capsys.readouterr()
        assert "completed with issues:" in captured.out
        assert "Invalid configuration for 2 speaker(s):" in captured.out
        assert "Alice: Missing provider field" in captured.out
        assert "Bob: Invalid voice configuration" in captured.out
        # Should not contain other issue types
        assert "Missing speaker(s) in YAML:" not in captured.out
        assert "Extra speaker(s) in YAML:" not in captured.out
        assert "Duplicate speaker(s) in YAML:" not in captured.out
