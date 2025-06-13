"""Tests for voice library CLI functionality."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from script_to_speech.voice_library.cli import main, validate_voice_libraries


class TestValidateVoiceLibraries:
    """Tests for the validate_voice_libraries function."""

    def test_validate_voice_libraries_success(self):
        """Test validate_voice_libraries when validation succeeds."""
        # Arrange
        mock_validator = MagicMock()
        mock_validator.validate_all.return_value = (True, [])

        # Act
        with patch(
            "script_to_speech.voice_library.cli.VoiceLibraryValidator",
            return_value=mock_validator,
        ):
            with patch("builtins.print") as mock_print:
                result = validate_voice_libraries()

        # Assert
        assert result == 0
        mock_validator.validate_all.assert_called_once()
        mock_print.assert_any_call("Validating voice library files...")
        mock_print.assert_any_call("✓ All voice library files are valid!")

    def test_validate_voice_libraries_with_errors(self):
        """Test validate_voice_libraries when validation finds errors."""
        # Arrange
        mock_validator = MagicMock()
        validation_errors = [
            "Error 1: Missing required field",
            "Error 2: Invalid property value",
        ]
        mock_validator.validate_all.return_value = (False, validation_errors)

        # Act
        with patch(
            "script_to_speech.voice_library.cli.VoiceLibraryValidator",
            return_value=mock_validator,
        ):
            with patch("builtins.print") as mock_print:
                result = validate_voice_libraries()

        # Assert
        assert result == 1
        mock_validator.validate_all.assert_called_once()
        mock_print.assert_any_call("Validating voice library files...")
        mock_print.assert_any_call(
            f"\n❌ Found {len(validation_errors)} voice library validation error(s):\n"
        )
        mock_print.assert_any_call("  • Error 1: Missing required field")
        mock_print.assert_any_call("  • Error 2: Invalid property value")

    def test_validate_voice_libraries_single_error(self):
        """Test validate_voice_libraries with a single error."""
        # Arrange
        mock_validator = MagicMock()
        validation_errors = ["Single error message"]
        mock_validator.validate_all.return_value = (False, validation_errors)

        # Act
        with patch(
            "script_to_speech.voice_library.cli.VoiceLibraryValidator",
            return_value=mock_validator,
        ):
            with patch("builtins.print") as mock_print:
                result = validate_voice_libraries()

        # Assert
        assert result == 1
        mock_validator.validate_all.assert_called_once()
        mock_print.assert_any_call(f"\n❌ Found 1 voice library validation error(s):\n")
        mock_print.assert_any_call("  • Single error message")

    def test_validate_voice_libraries_empty_errors_list(self):
        """Test validate_voice_libraries with empty errors list but False validation."""
        # Arrange
        mock_validator = MagicMock()
        mock_validator.validate_all.return_value = (False, [])

        # Act
        with patch(
            "script_to_speech.voice_library.cli.VoiceLibraryValidator",
            return_value=mock_validator,
        ):
            with patch("builtins.print") as mock_print:
                result = validate_voice_libraries()

        # Assert
        assert result == 1
        mock_validator.validate_all.assert_called_once()
        mock_print.assert_any_call(f"\n❌ Found 0 voice library validation error(s):\n")


class TestMain:
    """Tests for the main function."""

    def test_main_calls_sys_exit_with_validation_result(self):
        """Test main function calls sys.exit with validation result."""
        # Arrange
        expected_exit_code = 0

        # Act
        with patch(
            "script_to_speech.voice_library.cli.validate_voice_libraries",
            return_value=expected_exit_code,
        ) as mock_validate:
            with patch("sys.exit") as mock_exit:
                main()

        # Assert
        mock_validate.assert_called_once()
        mock_exit.assert_called_once_with(expected_exit_code)

    def test_main_calls_sys_exit_with_error_code(self):
        """Test main function calls sys.exit with error code when validation fails."""
        # Arrange
        expected_exit_code = 1

        # Act
        with patch(
            "script_to_speech.voice_library.cli.validate_voice_libraries",
            return_value=expected_exit_code,
        ) as mock_validate:
            with patch("sys.exit") as mock_exit:
                main()

        # Assert
        mock_validate.assert_called_once()
        mock_exit.assert_called_once_with(expected_exit_code)
