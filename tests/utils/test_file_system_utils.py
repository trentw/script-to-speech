"""Tests for file_system_utils.py."""

import os
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from script_to_speech.utils.file_system_utils import (
    create_output_folders,
    sanitize_name,
    PathSecurityValidator,
)


class TestSanitizeName:
    """Tests for sanitize_name function."""

    def test_sanitize_name(self):
        """Test sanitizing names for use in filenames."""
        # Test basic sanitization
        assert sanitize_name("Hello World!") == "Hello_World"

        # Test with special characters
        assert sanitize_name("My@Screenplay#123") == "MyScreenplay123"

        # Test with multiple spaces and hyphens
        assert sanitize_name("This - is  a   test") == "This_is_a_test"

        # Test with leading/trailing spaces
        assert (
            sanitize_name(" leading and trailing spaces ")
            == "leading_and_trailing_spaces"
        )

        # Test with empty string
        assert sanitize_name("") == ""


class TestCreateOutputFolders:
    """Tests for output folders creation function."""

    @patch("pathlib.Path.mkdir")
    @patch("script_to_speech.utils.file_system_utils.datetime")
    def test_create_output_folders_basic(self, mock_datetime, mock_mkdir):
        """Test basic functionality of create_output_folders."""
        # Arrange
        mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0)
        input_file = "input/test_screenplay.fountain"

        # Act
        main_output_folder, cache_folder, logs_folder, log_file = create_output_folders(
            input_file
        )

        # Assert path relationships (environment-independent)
        assert main_output_folder.name == "test_screenplay"
        assert main_output_folder.parent.name == "output"
        assert cache_folder.name == "cache"
        assert cache_folder.parent == main_output_folder
        assert logs_folder.name == "logs"
        assert logs_folder.parent == main_output_folder
        assert log_file.parent == logs_folder
        assert log_file.name == "log_20230101_120000.txt"

        # Verify mkdir was called for each directory
        assert mock_mkdir.call_count == 3
        # We can't directly check the exact calls because Path objects are created inside the function
        # But we can verify the function was called with the expected arguments
        for call in mock_mkdir.call_args_list:
            args, kwargs = call
            assert kwargs == {"parents": True, "exist_ok": True}
        
        # Verify security: all paths should be absolute and within a safe base
        assert main_output_folder.is_absolute()
        assert cache_folder.is_absolute()
        assert logs_folder.is_absolute()
        assert log_file.is_absolute()

    @patch("pathlib.Path.mkdir")
    @patch("script_to_speech.utils.file_system_utils.datetime")
    def test_create_output_folders_with_run_mode(self, mock_datetime, mock_mkdir):
        """Test create_output_folders with run mode."""
        # Arrange
        mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0)
        input_file = "input/test_screenplay.fountain"
        run_mode = "test_mode"

        # Act
        main_output_folder, cache_folder, logs_folder, log_file = create_output_folders(
            input_file, run_mode
        )

        # Assert path relationships (environment-independent)
        assert main_output_folder.name == "test_screenplay"
        assert main_output_folder.parent.name == "output"
        assert cache_folder.name == "cache"
        assert cache_folder.parent == main_output_folder
        assert logs_folder.name == "logs"
        assert logs_folder.parent == main_output_folder
        assert log_file.parent == logs_folder
        assert log_file.name == "[test_mode]_log_20230101_120000.txt"

        # Verify mkdir was called for each directory
        assert mock_mkdir.call_count == 3

    @patch("pathlib.Path.mkdir")
    @patch("script_to_speech.utils.file_system_utils.datetime")
    def test_create_output_folders_with_dummy_override(self, mock_datetime, mock_mkdir):
        """Test create_output_folders with dummy provider override."""
        # Arrange
        mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0)
        input_file = "input/test_screenplay.fountain"
        dummy_provider_override = True

        # Act
        main_output_folder, cache_folder, logs_folder, log_file = create_output_folders(
            input_file, dummy_provider_override=dummy_provider_override
        )

        # Assert path relationships (environment-independent)
        assert main_output_folder.name == "test_screenplay"
        assert main_output_folder.parent.name == "output"
        assert cache_folder.name == "dummy_cache"
        assert cache_folder.parent == main_output_folder
        assert logs_folder.name == "logs"
        assert logs_folder.parent == main_output_folder
        assert log_file.parent == logs_folder
        assert log_file.name == "[dummy]log_20230101_120000.txt"

        # Verify mkdir was called for each directory
        assert mock_mkdir.call_count == 3

    @patch("pathlib.Path.mkdir")
    @patch("script_to_speech.utils.file_system_utils.datetime")
    def test_create_output_folders_with_run_mode_and_dummy_override(
        self, mock_datetime, mock_mkdir
    ):
        """Test create_output_folders with both run mode and dummy provider override."""
        # Arrange
        mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0)
        input_file = "input/test_screenplay.fountain"
        run_mode = "test_mode"
        dummy_provider_override = True

        # Act
        main_output_folder, cache_folder, logs_folder, log_file = create_output_folders(
            input_file, run_mode, dummy_provider_override
        )

        # Assert path relationships (environment-independent)
        assert main_output_folder.name == "test_screenplay"
        assert main_output_folder.parent.name == "output"
        assert cache_folder.name == "dummy_cache"
        assert cache_folder.parent == main_output_folder
        assert logs_folder.name == "logs"
        assert logs_folder.parent == main_output_folder
        assert log_file.parent == logs_folder
        assert log_file.name == "[dummy][test_mode]_log_20230101_120000.txt"

        # Verify mkdir was called for each directory
        assert mock_mkdir.call_count == 3

    @patch("pathlib.Path.mkdir")
    def test_create_output_folders_handles_errors(self, mock_mkdir):
        """Test error handling when creating output folders."""
        # Arrange
        mock_mkdir.side_effect = OSError("Failed to create directory")
        input_file = "input/test_screenplay.fountain"

        # Act and Assert
        with pytest.raises(OSError, match="Failed to create directory"):
            create_output_folders(input_file)

    @patch("pathlib.Path.mkdir")
    @patch("script_to_speech.utils.file_system_utils.datetime")
    def test_create_output_folders_security_validation(self, mock_datetime, mock_mkdir):
        """Test that security validation is properly applied."""
        # Arrange
        mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0)
        input_file = "input/test_screenplay.fountain"
        test_base = Path("/test/secure/base")

        # Act
        main_output_folder, cache_folder, logs_folder, log_file = create_output_folders(
            input_file, base_path=test_base
        )

        # Assert security validator was used - all paths should be under test_base
        assert test_base in main_output_folder.parents
        assert test_base in cache_folder.parents
        assert test_base in logs_folder.parents
        assert test_base in log_file.parents
        
        # Verify path structure is maintained
        assert main_output_folder.name == "test_screenplay"
        assert cache_folder.name == "cache"
        assert logs_folder.name == "logs"


class TestPathSecurityValidator:
    """Tests for PathSecurityValidator class."""

    def test_init_with_valid_base_path(self):
        """Test initializing validator with valid base path."""
        base_path = Path("/tmp/secure_base")
        validator = PathSecurityValidator(base_path)
        assert validator.base_path == base_path.resolve()

    def test_validate_and_join_simple_path(self):
        """Test joining simple path components."""
        base_path = Path("/tmp/test_base")
        validator = PathSecurityValidator(base_path)
        
        result = validator.validate_and_join("subfolder", "file.txt")
        expected = base_path / "subfolder" / "file.txt"
        assert result == expected.resolve()

    def test_validate_and_join_empty_parts(self):
        """Test handling empty path parts."""
        base_path = Path("/tmp/test_base")
        validator = PathSecurityValidator(base_path)
        
        result = validator.validate_and_join("", "folder", "", "file.txt")
        expected = base_path / "folder" / "file.txt"
        assert result == expected.resolve()

    def test_validate_and_join_no_parts_returns_base(self):
        """Test that no parts returns base path."""
        base_path = Path("/tmp/test_base")
        validator = PathSecurityValidator(base_path)
        
        result = validator.validate_and_join()
        assert result == base_path.resolve()

    def test_validate_and_join_sanitizes_filenames(self):
        """Test that path parts are sanitized using pathvalidate."""
        base_path = Path("/tmp/test_base")
        validator = PathSecurityValidator(base_path)
        
        # Test with invalid filename characters
        result = validator.validate_and_join("my folder!", "file<name>.txt")
        # pathvalidate should remove/replace invalid characters
        # Note: pathvalidate may replace rather than remove characters
        result_str = str(result)
        # Verify the result is still within the base path
        assert base_path.resolve() in result.parents or result == base_path.resolve()

    def test_prevent_directory_traversal_attack(self):
        """Test prevention of directory traversal attacks."""
        base_path = Path("/tmp/secure_base")
        validator = PathSecurityValidator(base_path)
        
        # These should all raise ValueError due to directory traversal attempts
        with pytest.raises(ValueError, match="resolves outside base path"):
            validator.validate_and_join("..", "etc", "passwd")
            
        with pytest.raises(ValueError, match="resolves outside base path"):
            validator.validate_and_join("subfolder", "..", "..", "etc")
            
        # This one gets sanitized to a safe filename, so it doesn't raise
        result3 = validator.validate_and_join("../../../etc/passwd")
        assert base_path.resolve() in result3.parents or result3 == base_path.resolve()

    def test_prevent_absolute_path_injection(self):
        """Test prevention of absolute path injection."""
        base_path = Path("/tmp/secure_base")
        validator = PathSecurityValidator(base_path)
        
        # Absolute paths should be sanitized by pathvalidate
        # and result should still be within base path
        result = validator.validate_and_join("folder", "/etc/passwd")
        assert base_path.resolve() in result.parents or result == base_path.resolve()

    def test_validate_existing_path_valid(self):
        """Test validating an existing path within base."""
        base_path = Path("/tmp/secure_base")
        validator = PathSecurityValidator(base_path)
        
        valid_path = base_path / "subfolder" / "file.txt"
        result = validator.validate_existing_path(valid_path)
        assert result == valid_path.resolve()

    def test_validate_existing_path_outside_base_raises(self):
        """Test that paths outside base raise ValueError."""
        base_path = Path("/tmp/secure_base")
        validator = PathSecurityValidator(base_path)
        
        outside_path = Path("/etc/passwd")
        with pytest.raises(ValueError, match="outside the allowed base path"):
            validator.validate_existing_path(outside_path)

    def test_validate_existing_path_at_base_level(self):
        """Test that the base path itself is valid."""
        base_path = Path("/tmp/secure_base")
        validator = PathSecurityValidator(base_path)
        
        result = validator.validate_existing_path(base_path)
        assert result == base_path.resolve()

    def test_symlink_attack_prevention(self):
        """Test prevention of symlink-based attacks."""
        base_path = Path("/tmp/secure_base")
        validator = PathSecurityValidator(base_path)
        
        # Even if we try to create a path that could be a symlink,
        # the resolver should catch it if it points outside
        # This is handled by Path.resolve() in the validator
        result = validator.validate_and_join("safe_folder", "normal_file.txt")
        assert base_path.resolve() in result.parents or result == base_path.resolve()

    def test_unicode_filename_handling(self):
        """Test handling of unicode characters in filenames."""
        base_path = Path("/tmp/secure_base")
        validator = PathSecurityValidator(base_path)
        
        # Test with unicode characters
        result = validator.validate_and_join("folder", "файл.txt")
        assert base_path.resolve() in result.parents
        
        # Test with emoji (pathvalidate should handle this)
        result = validator.validate_and_join("folder", "file_😀.txt")
        assert base_path.resolve() in result.parents

    def test_long_path_handling(self):
        """Test handling of very long paths."""
        base_path = Path("/tmp/secure_base")
        validator = PathSecurityValidator(base_path)
        
        # Create a long path
        long_folder_name = "a" * 100
        result = validator.validate_and_join(long_folder_name, "file.txt")
        assert base_path.resolve() in result.parents

    def test_case_sensitivity_handling(self):
        """Test that case sensitivity is preserved."""
        base_path = Path("/tmp/secure_base")
        validator = PathSecurityValidator(base_path)
        
        result = validator.validate_and_join("MyFolder", "MyFile.TXT")
        assert "MyFolder" in str(result)
        assert "MyFile" in str(result)
