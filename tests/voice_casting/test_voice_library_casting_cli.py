import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from script_to_speech.voice_casting import voice_library_casting_cli


def test_parse_arguments_minimal():
    """Test parsing minimal required arguments."""
    with patch.object(sys, "argv", ["prog", "config.yaml", "openai"]):
        args = voice_library_casting_cli.parse_arguments()
        assert args.voice_config_path == Path("config.yaml")
        assert args.providers == ["openai"]
        assert args.prompt_file_path is None
        assert args.output_file_path is None


def test_parse_arguments_multiple_providers():
    """Test parsing with multiple providers."""
    with patch.object(
        sys, "argv", ["prog", "config.yaml", "openai", "elevenlabs", "cartesia"]
    ):
        args = voice_library_casting_cli.parse_arguments()
        assert args.providers == ["openai", "elevenlabs", "cartesia"]


def test_parse_arguments_with_optional_flags():
    """Test parsing with optional prompt and output file arguments."""
    with patch.object(
        sys,
        "argv",
        [
            "prog",
            "config.yaml",
            "openai",
            "--prompt-file",
            "custom_prompt.txt",
            "--output-file",
            "output.txt",
        ],
    ):
        args = voice_library_casting_cli.parse_arguments()
        assert args.prompt_file_path == Path("custom_prompt.txt")
        assert args.output_file_path == Path("output.txt")


def test_main_success(monkeypatch, tmp_path, capsys):
    """Test successful CLI execution."""
    # Arrange
    config_path = tmp_path / "test_config.yaml"
    config_path.write_text("test config")
    output_path = tmp_path / "output.txt"

    def mock_generate(*args, **kwargs):
        return output_path

    monkeypatch.setattr(
        voice_library_casting_cli,
        "generate_voice_library_casting_prompt_file",
        mock_generate,
    )

    test_args = ["prog", str(config_path), "openai", "elevenlabs"]
    monkeypatch.setattr(sys, "argv", test_args)

    # Act
    voice_library_casting_cli.main()
    captured = capsys.readouterr()

    # Assert
    assert "Successfully generated voice library casting prompt file" in captured.out
    assert str(output_path) in captured.out
    assert "openai, elevenlabs" in captured.out
    assert "PRIVACY NOTICE" in captured.out
    assert "test_config.yaml" in captured.out


def test_main_with_custom_files(monkeypatch, tmp_path, capsys):
    """Test CLI with custom prompt and output files."""
    # Arrange
    config_path = tmp_path / "config.yaml"
    prompt_path = tmp_path / "prompt.txt"
    output_path = tmp_path / "custom_output.txt"

    def mock_generate(*args, **kwargs):
        return output_path

    monkeypatch.setattr(
        voice_library_casting_cli,
        "generate_voice_library_casting_prompt_file",
        mock_generate,
    )

    test_args = [
        "prog",
        str(config_path),
        "openai",
        "--prompt-file",
        str(prompt_path),
        "--output-file",
        str(output_path),
    ]
    monkeypatch.setattr(sys, "argv", test_args)

    # Act
    voice_library_casting_cli.main()
    captured = capsys.readouterr()

    # Assert
    assert "Successfully generated" in captured.out
    assert "custom_output.txt" in captured.out


def test_main_file_not_found_error(monkeypatch, capsys):
    """Test CLI handling of FileNotFoundError."""

    # Arrange
    def mock_generate(*args, **kwargs):
        raise FileNotFoundError("Config file not found")

    monkeypatch.setattr(
        voice_library_casting_cli,
        "generate_voice_library_casting_prompt_file",
        mock_generate,
    )

    test_args = ["prog", "missing_config.yaml", "openai"]
    monkeypatch.setattr(sys, "argv", test_args)

    # Act/Assert
    with pytest.raises(SystemExit) as exc_info:
        voice_library_casting_cli.main()

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Error: Config file not found" in captured.err


def test_main_value_error(monkeypatch, capsys):
    """Test CLI handling of ValueError."""

    # Arrange
    def mock_generate(*args, **kwargs):
        raise ValueError("Invalid provider configuration")

    monkeypatch.setattr(
        voice_library_casting_cli,
        "generate_voice_library_casting_prompt_file",
        mock_generate,
    )

    test_args = ["prog", "config.yaml", "invalid_provider"]
    monkeypatch.setattr(sys, "argv", test_args)

    # Act/Assert
    with pytest.raises(SystemExit) as exc_info:
        voice_library_casting_cli.main()

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Error: Invalid provider configuration" in captured.err


def test_main_yaml_error(monkeypatch, capsys):
    """Test CLI handling of yaml.YAMLError."""

    # Arrange
    def mock_generate(*args, **kwargs):
        raise yaml.YAMLError("Invalid YAML syntax")

    monkeypatch.setattr(
        voice_library_casting_cli,
        "generate_voice_library_casting_prompt_file",
        mock_generate,
    )

    test_args = ["prog", "config.yaml", "openai"]
    monkeypatch.setattr(sys, "argv", test_args)

    # Act/Assert
    with pytest.raises(SystemExit) as exc_info:
        voice_library_casting_cli.main()

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Error processing YAML: Invalid YAML syntax" in captured.err


def test_main_unexpected_error(monkeypatch, capsys):
    """Test CLI handling of unexpected exceptions."""

    # Arrange
    def mock_generate(*args, **kwargs):
        raise RuntimeError("Unexpected error occurred")

    monkeypatch.setattr(
        voice_library_casting_cli,
        "generate_voice_library_casting_prompt_file",
        mock_generate,
    )

    test_args = ["prog", "config.yaml", "openai"]
    monkeypatch.setattr(sys, "argv", test_args)

    # Act/Assert
    with pytest.raises(SystemExit) as exc_info:
        voice_library_casting_cli.main()

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "An unexpected error occurred" in captured.err


def test_main_privacy_notice_content(monkeypatch, tmp_path, capsys):
    """Test that privacy notice includes expected content."""
    # Arrange
    config_path = tmp_path / "screenplay_config.yaml"
    output_path = tmp_path / "output.txt"

    def mock_generate(*args, **kwargs):
        return output_path

    monkeypatch.setattr(
        voice_library_casting_cli,
        "generate_voice_library_casting_prompt_file",
        mock_generate,
    )

    test_args = ["prog", str(config_path), "openai"]
    monkeypatch.setattr(sys, "argv", test_args)

    # Act
    voice_library_casting_cli.main()
    captured = capsys.readouterr()

    # Assert privacy notice content
    assert "PRIVACY NOTICE" in captured.out
    assert "Review the service's privacy policy" in captured.out
    assert (
        "Consider whether the service uses your content for AI training" in captured.out
    )
    assert "local LLM solutions" in captured.out
    assert "PRIVACY.md" in captured.out


def test_main_usage_instructions(monkeypatch, tmp_path, capsys):
    """Test that usage instructions are provided."""
    # Arrange
    config_path = tmp_path / "config.yaml"
    output_path = tmp_path / "result.txt"

    def mock_generate(*args, **kwargs):
        return output_path

    monkeypatch.setattr(
        voice_library_casting_cli,
        "generate_voice_library_casting_prompt_file",
        mock_generate,
    )

    test_args = ["prog", str(config_path), "openai"]
    monkeypatch.setattr(sys, "argv", test_args)

    # Act
    voice_library_casting_cli.main()
    captured = capsys.readouterr()

    # Assert usage instructions
    assert "To use this file with an LLM for voice casting:" in captured.out
    assert "Upload the file" in captured.out
    assert "sts-copy-to-clipboard" in captured.out
    assert "copy the LLM's YAML output" in captured.out
    assert "sts-tts-provider-yaml validate" in captured.out
