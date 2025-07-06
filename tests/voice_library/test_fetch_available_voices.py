"""Tests for the fetch_available_voices script."""

import argparse
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
import yaml

from script_to_speech.voice_library.voice_library_scripts.fetch_available_voices.fetch_available_voices import (
    get_argument_parser,
    run,
)


class TestGetArgumentParser:
    """Tests for the get_argument_parser function."""

    def test_get_argument_parser_returns_parser(self):
        """Tests that get_argument_parser returns an ArgumentParser."""
        # Act
        parser = get_argument_parser()

        # Assert
        assert isinstance(parser, argparse.ArgumentParser)

    def test_get_argument_parser_has_provider_argument(self):
        """Tests that the parser has a provider argument."""
        # Arrange
        parser = get_argument_parser()

        # Act
        args = parser.parse_args(["test_provider"])

        # Assert
        assert args.provider == "test_provider"

    def test_get_argument_parser_has_optional_file_name(self):
        """Tests that the parser has an optional file_name argument."""
        # Arrange
        parser = get_argument_parser()

        # Act
        args = parser.parse_args(["test_provider", "--file_name", "custom_file"])

        # Assert
        assert args.file_name == "custom_file"

    def test_get_argument_parser_default_file_name_none(self):
        """Tests that file_name defaults to None."""
        # Arrange
        parser = get_argument_parser()

        # Act
        args = parser.parse_args(["test_provider"])

        # Assert
        assert args.file_name is None


class TestRun:
    """Tests for the run function."""

    @patch(
        "script_to_speech.voice_library.voice_library_scripts.fetch_available_voices.fetch_available_voices.find_provider_specific_file"
    )
    @patch("importlib.util.spec_from_file_location")
    @patch("importlib.util.module_from_spec")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    @patch("yaml.dump")
    def test_run_success_with_default_filename(
        self,
        mock_yaml_dump,
        mock_file_open,
        mock_path_exists,
        mock_mkdir,
        mock_module_from_spec,
        mock_spec_from_file_location,
        mock_find_provider_specific_file,
        capsys,
    ):
        """Tests successful execution with default filename."""
        # Arrange
        args = argparse.Namespace(provider="elevenlabs", file_name=None)
        mock_provider_path = Path("/mock/provider/fetch_provider_voices.py")
        mock_find_provider_specific_file.return_value = mock_provider_path

        mock_spec = MagicMock()
        mock_spec.loader = MagicMock()
        mock_spec_from_file_location.return_value = mock_spec

        mock_provider_module = MagicMock()
        mock_provider_module.fetch_voices.return_value = ["voice1", "voice2", "voice3"]
        mock_module_from_spec.return_value = mock_provider_module

        mock_path_exists.return_value = False

        # Act
        run(args)

        # Assert
        mock_find_provider_specific_file.assert_called_once_with(
            "fetch_available_voices", "elevenlabs", "fetch_provider_voices.py"
        )
        mock_spec_from_file_location.assert_called_once_with(
            "provider_fetcher", mock_provider_path
        )
        mock_provider_module.fetch_voices.assert_called_once()
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

        expected_data = {
            "included_sts_ids": {"elevenlabs": ["voice1", "voice2", "voice3"]}
        }
        mock_yaml_dump.assert_called_once_with(
            expected_data,
            mock_file_open.return_value.__enter__.return_value,
            default_flow_style=False,
            sort_keys=False,
        )

        captured = capsys.readouterr()
        assert "Successfully wrote voice list to" in captured.out
        assert "elevenlabs_fetched_voices.yaml" in captured.out

    @patch(
        "script_to_speech.voice_library.voice_library_scripts.fetch_available_voices.fetch_available_voices.find_provider_specific_file"
    )
    @patch("importlib.util.spec_from_file_location")
    @patch("importlib.util.module_from_spec")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    @patch("yaml.dump")
    def test_run_success_with_custom_filename(
        self,
        mock_yaml_dump,
        mock_file_open,
        mock_path_exists,
        mock_mkdir,
        mock_module_from_spec,
        mock_spec_from_file_location,
        mock_find_provider_specific_file,
        capsys,
    ):
        """Tests successful execution with custom filename."""
        # Arrange
        args = argparse.Namespace(provider="openai", file_name="custom_voices")
        mock_provider_path = Path("/mock/provider/fetch_provider_voices.py")
        mock_find_provider_specific_file.return_value = mock_provider_path

        mock_spec = MagicMock()
        mock_spec.loader = MagicMock()
        mock_spec_from_file_location.return_value = mock_spec

        mock_provider_module = MagicMock()
        mock_provider_module.fetch_voices.return_value = ["voice_a", "voice_b"]
        mock_module_from_spec.return_value = mock_provider_module

        mock_path_exists.return_value = False

        # Act
        run(args)

        # Assert
        expected_data = {"included_sts_ids": {"openai": ["voice_a", "voice_b"]}}
        mock_yaml_dump.assert_called_once_with(
            expected_data,
            mock_file_open.return_value.__enter__.return_value,
            default_flow_style=False,
            sort_keys=False,
        )

        captured = capsys.readouterr()
        assert "Successfully wrote voice list to" in captured.out
        assert "custom_voices" in captured.out

    @patch(
        "script_to_speech.voice_library.voice_library_scripts.fetch_available_voices.fetch_available_voices.find_provider_specific_file"
    )
    def test_run_provider_script_not_found(
        self, mock_find_provider_specific_file, capsys
    ):
        """Tests when provider script is not found."""
        # Arrange
        args = argparse.Namespace(provider="unknown_provider", file_name=None)
        mock_find_provider_specific_file.return_value = None

        # Act
        run(args)

        # Assert
        captured = capsys.readouterr()
        assert (
            "No voice fetching script found for provider: unknown_provider"
            in captured.out
        )

    @patch(
        "script_to_speech.voice_library.voice_library_scripts.fetch_available_voices.fetch_available_voices.find_provider_specific_file"
    )
    @patch("importlib.util.spec_from_file_location")
    def test_run_import_error_none_spec(
        self, mock_spec_from_file_location, mock_find_provider_specific_file, capsys
    ):
        """Tests when importlib returns None spec."""
        # Arrange
        args = argparse.Namespace(provider="elevenlabs", file_name=None)
        mock_provider_path = Path("/mock/provider/fetch_provider_voices.py")
        mock_find_provider_specific_file.return_value = mock_provider_path
        mock_spec_from_file_location.return_value = None

        # Act
        run(args)

        # Assert
        captured = capsys.readouterr()
        assert "Error loading or running provider script" in captured.out
        assert "Could not load module from" in captured.out

    @patch(
        "script_to_speech.voice_library.voice_library_scripts.fetch_available_voices.fetch_available_voices.find_provider_specific_file"
    )
    @patch("importlib.util.spec_from_file_location")
    def test_run_import_error_none_loader(
        self, mock_spec_from_file_location, mock_find_provider_specific_file, capsys
    ):
        """Tests when spec has None loader."""
        # Arrange
        args = argparse.Namespace(provider="elevenlabs", file_name=None)
        mock_provider_path = Path("/mock/provider/fetch_provider_voices.py")
        mock_find_provider_specific_file.return_value = mock_provider_path

        mock_spec = MagicMock()
        mock_spec.loader = None
        mock_spec_from_file_location.return_value = mock_spec

        # Act
        run(args)

        # Assert
        captured = capsys.readouterr()
        assert "Error loading or running provider script" in captured.out
        assert "Could not load module from" in captured.out

    @patch(
        "script_to_speech.voice_library.voice_library_scripts.fetch_available_voices.fetch_available_voices.find_provider_specific_file"
    )
    @patch("importlib.util.spec_from_file_location")
    @patch("importlib.util.module_from_spec")
    def test_run_provider_script_missing_fetch_voices(
        self,
        mock_module_from_spec,
        mock_spec_from_file_location,
        mock_find_provider_specific_file,
        capsys,
    ):
        """Tests when provider script is missing fetch_voices method."""
        # Arrange
        args = argparse.Namespace(provider="elevenlabs", file_name=None)
        mock_provider_path = Path("/mock/provider/fetch_provider_voices.py")
        mock_find_provider_specific_file.return_value = mock_provider_path

        mock_spec = MagicMock()
        mock_spec.loader = MagicMock()
        mock_spec_from_file_location.return_value = mock_spec

        mock_provider_module = MagicMock()
        del mock_provider_module.fetch_voices  # Missing fetch_voices method
        mock_module_from_spec.return_value = mock_provider_module

        # Act
        run(args)

        # Assert
        captured = capsys.readouterr()
        assert "Error loading or running provider script" in captured.out

    @patch(
        "script_to_speech.voice_library.voice_library_scripts.fetch_available_voices.fetch_available_voices.find_provider_specific_file"
    )
    @patch("importlib.util.spec_from_file_location")
    @patch("importlib.util.module_from_spec")
    def test_run_provider_script_fetch_voices_exception(
        self,
        mock_module_from_spec,
        mock_spec_from_file_location,
        mock_find_provider_specific_file,
        capsys,
    ):
        """Tests when provider script's fetch_voices method raises an exception."""
        # Arrange
        args = argparse.Namespace(provider="elevenlabs", file_name=None)
        mock_provider_path = Path("/mock/provider/fetch_provider_voices.py")
        mock_find_provider_specific_file.return_value = mock_provider_path

        mock_spec = MagicMock()
        mock_spec.loader = MagicMock()
        mock_spec_from_file_location.return_value = mock_spec

        mock_provider_module = MagicMock()
        mock_provider_module.fetch_voices.side_effect = Exception("API error")
        mock_module_from_spec.return_value = mock_provider_module

        # Act
        run(args)

        # Assert
        captured = capsys.readouterr()
        assert "Error loading or running provider script" in captured.out
        assert "API error" in captured.out

    @patch(
        "script_to_speech.voice_library.voice_library_scripts.fetch_available_voices.fetch_available_voices.find_provider_specific_file"
    )
    @patch("importlib.util.spec_from_file_location")
    @patch("importlib.util.module_from_spec")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    @patch("yaml.dump")
    def test_run_file_already_exists(
        self,
        mock_yaml_dump,
        mock_file_open,
        mock_path_exists,
        mock_mkdir,
        mock_module_from_spec,
        mock_spec_from_file_location,
        mock_find_provider_specific_file,
        capsys,
    ):
        """Tests when output file already exists."""
        # Arrange
        args = argparse.Namespace(provider="elevenlabs", file_name=None)
        mock_provider_path = Path("/mock/provider/fetch_provider_voices.py")
        mock_find_provider_specific_file.return_value = mock_provider_path

        mock_spec = MagicMock()
        mock_spec.loader = MagicMock()
        mock_spec_from_file_location.return_value = mock_spec

        mock_provider_module = MagicMock()
        mock_provider_module.fetch_voices.return_value = ["voice1"]
        mock_module_from_spec.return_value = mock_provider_module

        mock_path_exists.return_value = True  # File already exists

        # Act
        run(args)

        # Assert
        captured = capsys.readouterr()
        assert "already exists. Overwriting." in captured.out

    @patch(
        "script_to_speech.voice_library.voice_library_scripts.fetch_available_voices.fetch_available_voices.find_provider_specific_file"
    )
    @patch("importlib.util.spec_from_file_location")
    @patch("importlib.util.module_from_spec")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    @patch("yaml.dump")
    def test_run_yaml_write_failure(
        self,
        mock_yaml_dump,
        mock_file_open,
        mock_path_exists,
        mock_mkdir,
        mock_module_from_spec,
        mock_spec_from_file_location,
        mock_find_provider_specific_file,
        capsys,
    ):
        """Tests when YAML writing fails."""
        # Arrange
        args = argparse.Namespace(provider="elevenlabs", file_name=None)
        mock_provider_path = Path("/mock/provider/fetch_provider_voices.py")
        mock_find_provider_specific_file.return_value = mock_provider_path

        mock_spec = MagicMock()
        mock_spec.loader = MagicMock()
        mock_spec_from_file_location.return_value = mock_spec

        mock_provider_module = MagicMock()
        mock_provider_module.fetch_voices.return_value = ["voice1"]
        mock_module_from_spec.return_value = mock_provider_module

        mock_path_exists.return_value = False
        mock_yaml_dump.side_effect = Exception("YAML write error")

        # Act
        # Note: This will raise an exception, which is expected behavior
        with pytest.raises(Exception, match="YAML write error"):
            run(args)

    @patch(
        "script_to_speech.voice_library.voice_library_scripts.fetch_available_voices.fetch_available_voices.find_provider_specific_file"
    )
    @patch("importlib.util.spec_from_file_location")
    @patch("importlib.util.module_from_spec")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    @patch("yaml.dump")
    def test_run_directory_creation(
        self,
        mock_yaml_dump,
        mock_file_open,
        mock_path_exists,
        mock_mkdir,
        mock_module_from_spec,
        mock_spec_from_file_location,
        mock_find_provider_specific_file,
    ):
        """Tests that output directory is created properly."""
        # Arrange
        args = argparse.Namespace(provider="elevenlabs", file_name=None)
        mock_provider_path = Path("/mock/provider/fetch_provider_voices.py")
        mock_find_provider_specific_file.return_value = mock_provider_path

        mock_spec = MagicMock()
        mock_spec.loader = MagicMock()
        mock_spec_from_file_location.return_value = mock_spec

        mock_provider_module = MagicMock()
        mock_provider_module.fetch_voices.return_value = ["voice1"]
        mock_module_from_spec.return_value = mock_provider_module

        mock_path_exists.return_value = False

        # Act
        run(args)

        # Assert
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch(
        "script_to_speech.voice_library.voice_library_scripts.fetch_available_voices.fetch_available_voices.find_provider_specific_file"
    )
    @patch("importlib.util.spec_from_file_location")
    @patch("importlib.util.module_from_spec")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    @patch("yaml.dump")
    def test_run_filename_with_yaml_extension(
        self,
        mock_yaml_dump,
        mock_file_open,
        mock_path_exists,
        mock_mkdir,
        mock_module_from_spec,
        mock_spec_from_file_location,
        mock_find_provider_specific_file,
        capsys,
    ):
        """Tests that filenames with .yaml extension are not modified."""
        # Arrange
        args = argparse.Namespace(provider="elevenlabs", file_name="voices.yaml")
        mock_provider_path = Path("/mock/provider/fetch_provider_voices.py")
        mock_find_provider_specific_file.return_value = mock_provider_path

        mock_spec = MagicMock()
        mock_spec.loader = MagicMock()
        mock_spec_from_file_location.return_value = mock_spec

        mock_provider_module = MagicMock()
        mock_provider_module.fetch_voices.return_value = ["voice1"]
        mock_module_from_spec.return_value = mock_provider_module

        mock_path_exists.return_value = False

        # Act
        run(args)

        # Assert
        captured = capsys.readouterr()
        assert "voices.yaml" in captured.out
        assert "voices.yaml.yaml" not in captured.out

    @patch(
        "script_to_speech.voice_library.voice_library_scripts.fetch_available_voices.fetch_available_voices.find_provider_specific_file"
    )
    @patch("importlib.util.spec_from_file_location")
    @patch("importlib.util.module_from_spec")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    @patch("yaml.dump")
    def test_run_filename_with_yml_extension(
        self,
        mock_yaml_dump,
        mock_file_open,
        mock_path_exists,
        mock_mkdir,
        mock_module_from_spec,
        mock_spec_from_file_location,
        mock_find_provider_specific_file,
        capsys,
    ):
        """Tests that filenames with .yml extension are not modified."""
        # Arrange
        args = argparse.Namespace(provider="elevenlabs", file_name="voices.yml")
        mock_provider_path = Path("/mock/provider/fetch_provider_voices.py")
        mock_find_provider_specific_file.return_value = mock_provider_path

        mock_spec = MagicMock()
        mock_spec.loader = MagicMock()
        mock_spec_from_file_location.return_value = mock_spec

        mock_provider_module = MagicMock()
        mock_provider_module.fetch_voices.return_value = ["voice1"]
        mock_module_from_spec.return_value = mock_provider_module

        mock_path_exists.return_value = False

        # Act
        run(args)

        # Assert
        captured = capsys.readouterr()
        assert "voices.yml" in captured.out
        assert "voices.yml.yaml" not in captured.out

    @patch(
        "script_to_speech.voice_library.voice_library_scripts.fetch_available_voices.fetch_available_voices.find_provider_specific_file"
    )
    @patch("importlib.util.spec_from_file_location")
    @patch("importlib.util.module_from_spec")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    @patch("yaml.dump")
    def test_run_filename_without_extension(
        self,
        mock_yaml_dump,
        mock_file_open,
        mock_path_exists,
        mock_mkdir,
        mock_module_from_spec,
        mock_spec_from_file_location,
        mock_find_provider_specific_file,
        capsys,
    ):
        """Tests that filenames without extension get .yaml added."""
        # Arrange
        args = argparse.Namespace(provider="elevenlabs", file_name="voices")
        mock_provider_path = Path("/mock/provider/fetch_provider_voices.py")
        mock_find_provider_specific_file.return_value = mock_provider_path

        mock_spec = MagicMock()
        mock_spec.loader = MagicMock()
        mock_spec_from_file_location.return_value = mock_spec

        mock_provider_module = MagicMock()
        mock_provider_module.fetch_voices.return_value = ["voice1"]
        mock_module_from_spec.return_value = mock_provider_module

        mock_path_exists.return_value = False

        # Act
        run(args)

        # Assert
        captured = capsys.readouterr()
        assert "voices.yaml" in captured.out

    @patch(
        "script_to_speech.voice_library.voice_library_scripts.fetch_available_voices.fetch_available_voices.find_provider_specific_file"
    )
    @patch("importlib.util.spec_from_file_location")
    @patch("importlib.util.module_from_spec")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    @patch("yaml.dump")
    def test_run_provider_returns_empty_list(
        self,
        mock_yaml_dump,
        mock_file_open,
        mock_path_exists,
        mock_mkdir,
        mock_module_from_spec,
        mock_spec_from_file_location,
        mock_find_provider_specific_file,
        capsys,
    ):
        """Tests handling when provider returns empty list."""
        # Arrange
        args = argparse.Namespace(provider="elevenlabs", file_name=None)
        mock_provider_path = Path("/mock/provider/fetch_provider_voices.py")
        mock_find_provider_specific_file.return_value = mock_provider_path

        mock_spec = MagicMock()
        mock_spec.loader = MagicMock()
        mock_spec_from_file_location.return_value = mock_spec

        mock_provider_module = MagicMock()
        mock_provider_module.fetch_voices.return_value = []  # Empty list
        mock_module_from_spec.return_value = mock_provider_module

        mock_path_exists.return_value = False

        # Act
        run(args)

        # Assert
        expected_data = {"included_sts_ids": {"elevenlabs": []}}
        mock_yaml_dump.assert_called_once_with(
            expected_data,
            mock_file_open.return_value.__enter__.return_value,
            default_flow_style=False,
            sort_keys=False,
        )
        captured = capsys.readouterr()
        assert "Successfully wrote voice list to" in captured.out

    @patch(
        "script_to_speech.voice_library.voice_library_scripts.fetch_available_voices.fetch_available_voices.find_provider_specific_file"
    )
    @patch("importlib.util.spec_from_file_location")
    @patch("importlib.util.module_from_spec")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    @patch("yaml.dump")
    def test_run_provider_returns_non_list(
        self,
        mock_yaml_dump,
        mock_file_open,
        mock_path_exists,
        mock_mkdir,
        mock_module_from_spec,
        mock_spec_from_file_location,
        mock_find_provider_specific_file,
        capsys,
    ):
        """Tests handling when provider returns non-list data."""
        # Arrange
        args = argparse.Namespace(provider="elevenlabs", file_name=None)
        mock_provider_path = Path("/mock/provider/fetch_provider_voices.py")
        mock_find_provider_specific_file.return_value = mock_provider_path

        mock_spec = MagicMock()
        mock_spec.loader = MagicMock()
        mock_spec_from_file_location.return_value = mock_spec

        mock_provider_module = MagicMock()
        mock_provider_module.fetch_voices.return_value = "not_a_list"  # Non-list data
        mock_module_from_spec.return_value = mock_provider_module

        mock_path_exists.return_value = False

        # Act
        run(args)

        # Assert
        expected_data = {"included_sts_ids": {"elevenlabs": "not_a_list"}}
        mock_yaml_dump.assert_called_once_with(
            expected_data,
            mock_file_open.return_value.__enter__.return_value,
            default_flow_style=False,
            sort_keys=False,
        )
