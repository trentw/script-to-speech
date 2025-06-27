import tempfile
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest
import yaml

from script_to_speech.voice_casting.voice_library_casting_utils import (
    generate_voice_library_casting_prompt_file,
)


def test_generate_voice_library_casting_prompt_file_success(tmp_path: Path):
    """Test successful prompt file generation with all required files."""
    # Arrange
    voice_config_path = tmp_path / "config.yaml"
    voice_config_path.write_text("characters:\n  - name: John\n")

    # Create voice library structure relative to the module location
    utils_dir = tmp_path / "utils_dir"
    utils_dir.mkdir()

    # Create default prompt file in utils_dir
    prompt_file = utils_dir / "default_voice_library_casting_prompt.txt"
    prompt_file.write_text("This is the default prompt.")

    # Create voice library structure
    voice_lib_dir = utils_dir.parent / "voice_library" / "voice_library_data"
    voice_lib_dir.mkdir(parents=True)

    schema_file = voice_lib_dir / "voice_library_schema.yaml"
    schema_file.write_text("schema: voice_library\n")

    openai_dir = voice_lib_dir / "openai"
    openai_dir.mkdir()
    openai_voices = openai_dir / "voices.yaml"
    openai_voices.write_text("voices:\n  - id: voice1\n")

    elevenlabs_dir = voice_lib_dir / "elevenlabs"
    elevenlabs_dir.mkdir()
    elevenlabs_voices = elevenlabs_dir / "voices.yaml"
    elevenlabs_voices.write_text("voices:\n  - id: voice2\n")

    # Mock __file__ to point to our utils_dir
    with patch(
        "script_to_speech.voice_casting.voice_library_casting_utils.__file__",
        str(utils_dir / "voice_library_casting_utils.py"),
    ):
        # Act
        result = generate_voice_library_casting_prompt_file(
            voice_config_path=voice_config_path, providers=["openai", "elevenlabs"]
        )

    # Assert
    assert result.exists()
    content = result.read_text()
    assert "This is the default prompt." in content
    assert "--- VOICE LIBRARY SCHEMA ---" in content
    assert "--- VOICE CONFIGURATION ---" in content
    assert "--- VOICE LIBRARY DATA (OPENAI) ---" in content
    assert "--- VOICE LIBRARY DATA (ELEVENLABS) ---" in content


def test_generate_voice_library_casting_prompt_file_custom_output_path(tmp_path: Path):
    """Test with custom output file path."""
    # Arrange
    voice_config_path = tmp_path / "config.yaml"
    voice_config_path.write_text("characters:\n  - name: John\n")

    custom_output = tmp_path / "custom_output.txt"

    # Create file structure
    utils_dir = tmp_path / "utils_dir"
    utils_dir.mkdir()

    # Create default prompt file
    (utils_dir / "default_voice_library_casting_prompt.txt").write_text(
        "Default prompt"
    )

    # Create voice library structure
    voice_lib_dir = utils_dir.parent / "voice_library" / "voice_library_data"
    voice_lib_dir.mkdir(parents=True)
    (voice_lib_dir / "voice_library_schema.yaml").write_text("schema: test")
    openai_dir = voice_lib_dir / "openai"
    openai_dir.mkdir()
    (openai_dir / "voices.yaml").write_text("voices: []")

    # Mock __file__ to point to our utils_dir
    with patch(
        "script_to_speech.voice_casting.voice_library_casting_utils.__file__",
        str(utils_dir / "voice_library_casting_utils.py"),
    ):
        # Act
        result = generate_voice_library_casting_prompt_file(
            voice_config_path=voice_config_path,
            providers=["openai"],
            output_file_path=custom_output,
        )

    # Assert
    assert result == custom_output
    assert custom_output.exists()


def test_generate_voice_library_casting_prompt_file_missing_voice_config():
    """Test with missing voice config file."""
    with pytest.raises(FileNotFoundError, match="Voice config file not found"):
        generate_voice_library_casting_prompt_file(
            voice_config_path=Path("/nonexistent/config.yaml"), providers=["openai"]
        )


def test_generate_voice_library_casting_prompt_file_missing_custom_prompt():
    """Test with missing custom prompt file."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        voice_config_path = tmp_path / "config.yaml"
        voice_config_path.write_text("test")

        with pytest.raises(FileNotFoundError, match="Custom prompt file not found"):
            generate_voice_library_casting_prompt_file(
                voice_config_path=voice_config_path,
                providers=["openai"],
                prompt_file_path=Path("/nonexistent/prompt.txt"),
            )


def test_generate_voice_library_casting_prompt_file_missing_schema(tmp_path: Path):
    """Test with missing voice library schema file."""
    # Arrange
    voice_config_path = tmp_path / "config.yaml"
    voice_config_path.write_text("test")

    # Create file structure but missing schema
    utils_dir = tmp_path / "utils_dir"
    utils_dir.mkdir()
    (utils_dir / "default_voice_library_casting_prompt.txt").write_text("prompt")

    # Mock __file__ to point to our utils_dir
    with patch(
        "script_to_speech.voice_casting.voice_library_casting_utils.__file__",
        str(utils_dir / "voice_library_casting_utils.py"),
    ):
        # Act/Assert
        with pytest.raises(
            FileNotFoundError, match="Voice library schema file not found"
        ):
            generate_voice_library_casting_prompt_file(
                voice_config_path=voice_config_path, providers=["openai"]
            )


def test_generate_voice_library_casting_prompt_file_missing_provider_voices(
    tmp_path: Path,
):
    """Test with missing provider voice library file."""
    # Arrange
    voice_config_path = tmp_path / "config.yaml"
    voice_config_path.write_text("test")

    # Create file structure but missing provider voices
    utils_dir = tmp_path / "utils_dir"
    utils_dir.mkdir()
    (utils_dir / "default_voice_library_casting_prompt.txt").write_text("prompt")

    voice_lib_dir = utils_dir.parent / "voice_library" / "voice_library_data"
    voice_lib_dir.mkdir(parents=True)
    (voice_lib_dir / "voice_library_schema.yaml").write_text("schema")

    # Mock __file__ to point to our utils_dir
    with patch(
        "script_to_speech.voice_casting.voice_library_casting_utils.__file__",
        str(utils_dir / "voice_library_casting_utils.py"),
    ):
        # Act/Assert
        with pytest.raises(
            FileNotFoundError,
            match="Voice library file not found for provider 'openai'",
        ):
            generate_voice_library_casting_prompt_file(
                voice_config_path=voice_config_path, providers=["openai"]
            )


def test_generate_voice_library_casting_prompt_file_yaml_error(tmp_path: Path):
    """Test with invalid YAML in voice config file."""
    # Arrange
    voice_config_path = tmp_path / "config.yaml"
    voice_config_path.write_text("invalid: yaml: content:")

    # Create file structure
    utils_dir = tmp_path / "utils_dir"
    utils_dir.mkdir()
    (utils_dir / "default_voice_library_casting_prompt.txt").write_text("prompt")

    voice_lib_dir = utils_dir.parent / "voice_library" / "voice_library_data"
    voice_lib_dir.mkdir(parents=True)
    (voice_lib_dir / "voice_library_schema.yaml").write_text("schema")

    openai_dir = voice_lib_dir / "openai"
    openai_dir.mkdir()
    (openai_dir / "voices.yaml").write_text("voices: []")

    # Mock __file__ and file read to raise exception during voice config reading
    with patch(
        "script_to_speech.voice_casting.voice_library_casting_utils.__file__",
        str(utils_dir / "voice_library_casting_utils.py"),
    ):
        with patch(
            "builtins.open",
            side_effect=[
                mock_open(read_data="prompt").return_value,  # prompt file
                Exception("Read error"),  # voice config file
            ],
        ):
            # Act/Assert
            with pytest.raises(yaml.YAMLError, match="Error reading voice config file"):
                generate_voice_library_casting_prompt_file(
                    voice_config_path=voice_config_path, providers=["openai"]
                )


def test_generate_voice_library_casting_prompt_file_default_output_name(tmp_path: Path):
    """Test that default output filename is generated correctly."""
    # Arrange
    voice_config_path = tmp_path / "my_screenplay_config.yaml"
    voice_config_path.write_text("test")

    # Create file structure
    utils_dir = tmp_path / "utils_dir"
    utils_dir.mkdir()
    (utils_dir / "default_voice_library_casting_prompt.txt").write_text("prompt")

    voice_lib_dir = utils_dir.parent / "voice_library" / "voice_library_data"
    voice_lib_dir.mkdir(parents=True)
    (voice_lib_dir / "voice_library_schema.yaml").write_text("schema")

    openai_dir = voice_lib_dir / "openai"
    openai_dir.mkdir()
    (openai_dir / "voices.yaml").write_text("voices: []")

    # Mock __file__ to point to our utils_dir
    with patch(
        "script_to_speech.voice_casting.voice_library_casting_utils.__file__",
        str(utils_dir / "voice_library_casting_utils.py"),
    ):
        # Act
        result = generate_voice_library_casting_prompt_file(
            voice_config_path=voice_config_path, providers=["openai"]
        )

    # Assert
    expected_name = "my_screenplay_config_voice_library_casting_prompt.txt"
    assert result.name == expected_name
    assert result.parent == tmp_path


def test_generate_voice_library_casting_prompt_file_multiple_providers(tmp_path: Path):
    """Test with multiple providers."""
    # Arrange
    voice_config_path = tmp_path / "config.yaml"
    voice_config_path.write_text("test")

    # Create file structure
    utils_dir = tmp_path / "utils_dir"
    utils_dir.mkdir()
    (utils_dir / "default_voice_library_casting_prompt.txt").write_text("prompt")

    voice_lib_dir = utils_dir.parent / "voice_library" / "voice_library_data"
    voice_lib_dir.mkdir(parents=True)
    (voice_lib_dir / "voice_library_schema.yaml").write_text("schema")

    for provider in ["openai", "elevenlabs", "cartesia"]:
        provider_dir = voice_lib_dir / provider
        provider_dir.mkdir()
        (provider_dir / "voices.yaml").write_text(f"{provider}_voices: []")

    # Mock __file__ to point to our utils_dir
    with patch(
        "script_to_speech.voice_casting.voice_library_casting_utils.__file__",
        str(utils_dir / "voice_library_casting_utils.py"),
    ):
        # Act
        result = generate_voice_library_casting_prompt_file(
            voice_config_path=voice_config_path,
            providers=["openai", "elevenlabs", "cartesia"],
        )

    # Assert
    content = result.read_text()
    assert "--- VOICE LIBRARY DATA (OPENAI) ---" in content
    assert "--- VOICE LIBRARY DATA (ELEVENLABS) ---" in content
    assert "--- VOICE LIBRARY DATA (CARTESIA) ---" in content
