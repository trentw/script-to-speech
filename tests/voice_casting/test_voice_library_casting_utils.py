import tempfile
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest
import yaml

from script_to_speech.voice_casting.voice_library_casting_utils import (
    _filter_provider_voices,
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
    openai_voices.write_text("voices:\n  voice1:\n    model_id: tts-1\n")

    elevenlabs_dir = voice_lib_dir / "elevenlabs"
    elevenlabs_dir.mkdir()
    elevenlabs_voices = elevenlabs_dir / "voices.yaml"
    elevenlabs_voices.write_text("voices:\n  voice2:\n    model_id: eleven\n")

    # Mock __file__ and config loading
    with patch(
        "script_to_speech.voice_casting.voice_library_casting_utils.__file__",
        str(utils_dir / "voice_library_casting_utils.py"),
    ):
        with patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.load_config",
            return_value={},
        ):
            with patch(
                "script_to_speech.voice_casting.voice_library_casting_utils.get_conflicting_ids",
                return_value={},
            ):
                # Act
                result = generate_voice_library_casting_prompt_file(
                    voice_config_path=voice_config_path,
                    providers=["openai", "elevenlabs"],
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
    (openai_dir / "voices.yaml").write_text("voices: {}")

    # Mock __file__ and config loading
    with patch(
        "script_to_speech.voice_casting.voice_library_casting_utils.__file__",
        str(utils_dir / "voice_library_casting_utils.py"),
    ):
        with patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.load_config",
            return_value={},
        ):
            with patch(
                "script_to_speech.voice_casting.voice_library_casting_utils.get_conflicting_ids",
                return_value={},
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
    (openai_dir / "voices.yaml").write_text("voices: {}")

    # Mock __file__ and config loading, but cause error in voice config reading
    with patch(
        "script_to_speech.voice_casting.voice_library_casting_utils.__file__",
        str(utils_dir / "voice_library_casting_utils.py"),
    ):
        with patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.load_config",
            return_value={},
        ):
            with patch(
                "script_to_speech.voice_casting.voice_library_casting_utils.get_conflicting_ids",
                return_value={},
            ):
                with patch(
                    "builtins.open",
                    side_effect=[
                        mock_open(read_data="prompt").return_value,  # prompt file
                        Exception("Read error"),  # voice config file
                    ],
                ):
                    # Act/Assert
                    with pytest.raises(
                        yaml.YAMLError, match="Error reading voice config file"
                    ):
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
    (openai_dir / "voices.yaml").write_text("voices: {}")

    # Mock __file__ and config loading
    with patch(
        "script_to_speech.voice_casting.voice_library_casting_utils.__file__",
        str(utils_dir / "voice_library_casting_utils.py"),
    ):
        with patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.load_config",
            return_value={},
        ):
            with patch(
                "script_to_speech.voice_casting.voice_library_casting_utils.get_conflicting_ids",
                return_value={},
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
        (provider_dir / "voices.yaml").write_text(f"voices: {{}}")

    # Mock __file__ and config loading
    with patch(
        "script_to_speech.voice_casting.voice_library_casting_utils.__file__",
        str(utils_dir / "voice_library_casting_utils.py"),
    ):
        with patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.load_config",
            return_value={},
        ):
            with patch(
                "script_to_speech.voice_casting.voice_library_casting_utils.get_conflicting_ids",
                return_value={},
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


# --- Tests for _filter_provider_voices ---


def test_filter_provider_voices_with_include_only():
    """Test filtering with only an include list."""
    # Arrange
    provider_data = {
        "provider_metadata": {"some_key": "some_value"},
        "voices": {
            "alloy": {"model_id": "tts-1", "supports_style": True},
            "nova": {"model_id": "tts-1-hd", "supports_style": False},
            "shimmer": {"model_id": "tts-1", "supports_style": False},
        },
    }
    config = {"included_sts_ids": {"openai": ["alloy", "nova"]}}

    # Act
    result = _filter_provider_voices("openai", provider_data, config)

    # Assert
    assert "voices" in result
    assert list(result["voices"].keys()) == ["alloy", "nova"]
    assert "provider_metadata" in result
    assert result["provider_metadata"] == {"some_key": "some_value"}


def test_filter_provider_voices_with_exclude_only():
    """Test filtering with only an exclude list."""
    # Arrange
    provider_data = {
        "voices": {
            "alloy": {"model_id": "tts-1"},
            "nova": {"model_id": "tts-1-hd"},
            "shimmer": {"model_id": "tts-1"},
        }
    }
    config = {"excluded_sts_ids": {"openai": ["shimmer"]}}

    # Act
    result = _filter_provider_voices("openai", provider_data, config)

    # Assert
    assert "voices" in result
    assert list(result["voices"].keys()) == ["alloy", "nova"]


def test_filter_provider_voices_with_include_and_exclude():
    """Test filtering with both include and exclude lists."""
    # Arrange
    provider_data = {
        "voices": {
            "alloy": {"model_id": "tts-1"},
            "nova": {"model_id": "tts-1-hd"},
            "shimmer": {"model_id": "tts-1"},
            "fable": {"model_id": "tts-1-hd"},
        }
    }
    config = {
        "included_sts_ids": {"openai": ["alloy", "nova", "fable"]},
        "excluded_sts_ids": {"openai": ["nova"]},
    }

    # Act
    result = _filter_provider_voices("openai", provider_data, config)

    # Assert
    assert "voices" in result
    assert list(result["voices"].keys()) == ["alloy", "fable"]


def test_filter_provider_voices_no_rules():
    """Test that no filtering occurs when no rules are provided."""
    # Arrange
    provider_data = {
        "voices": {
            "alloy": {"model_id": "tts-1"},
            "nova": {"model_id": "tts-1-hd"},
        }
    }
    config = {}

    # Act
    result = _filter_provider_voices("openai", provider_data, config)

    # Assert
    assert result == provider_data


def test_filter_provider_voices_empty_include_list():
    """Test filtering with empty include list results in no voices."""
    # Arrange
    provider_data = {
        "voices": {
            "alloy": {"model_id": "tts-1"},
            "nova": {"model_id": "tts-1-hd"},
        }
    }
    config = {"included_sts_ids": {"openai": []}}

    # Act
    result = _filter_provider_voices("openai", provider_data, config)

    # Assert
    assert "voices" in result
    assert result["voices"] == {}


def test_filter_provider_voices_no_voices_key():
    """Test filtering when provider data has no voices key."""
    # Arrange
    provider_data = {"provider_metadata": {"some_key": "value"}}
    config = {"included_sts_ids": {"openai": ["alloy"]}}

    # Act
    result = _filter_provider_voices("openai", provider_data, config)

    # Assert
    assert result == {}


def test_filter_provider_voices_direct_voice_dict():
    """Test filtering when provider data is directly a voice dictionary (no voices key)."""
    # Arrange
    provider_data = {
        "alloy": {"model_id": "tts-1"},
        "nova": {"model_id": "tts-1-hd"},
        "shimmer": {"model_id": "tts-1"},
    }
    config = {"included_sts_ids": {"openai": ["alloy", "nova"]}}

    # Act
    result = _filter_provider_voices("openai", provider_data, config)

    # Assert
    # Since provider_data has no "voices" key, it returns empty dict
    assert result == {}


# --- Tests for conflict detection behavior ---


def test_generate_voice_library_casting_prompt_file_with_config_conflicts(
    tmp_path: Path,
):
    """Test that prompt generation raises ValueError when config has conflicts."""
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

    openai_dir = voice_lib_dir / "openai"
    openai_dir.mkdir()
    (openai_dir / "voices.yaml").write_text("voices: {}")

    # Mock the config loading to return conflicts
    with patch(
        "script_to_speech.voice_casting.voice_library_casting_utils.__file__",
        str(utils_dir / "voice_library_casting_utils.py"),
    ):
        with patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.load_config",
            return_value={"some_key": "some_value"},
        ):
            with patch(
                "script_to_speech.voice_casting.voice_library_casting_utils.get_conflicting_ids",
                return_value={"openai": {"alloy"}},
            ):
                # Act & Assert
                with pytest.raises(ValueError, match="Validation FAILED"):
                    generate_voice_library_casting_prompt_file(
                        voice_config_path=voice_config_path, providers=["openai"]
                    )


def test_generate_voice_library_casting_prompt_file_with_voice_filtering(
    tmp_path: Path,
):
    """Test that voice library data is filtered based on config."""
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

    openai_dir = voice_lib_dir / "openai"
    openai_dir.mkdir()
    # Create voices.yaml with multiple voices
    voices_data = {
        "voices": {
            "alloy": {"model_id": "tts-1"},
            "nova": {"model_id": "tts-1-hd"},
            "shimmer": {"model_id": "tts-1"},
        }
    }
    (openai_dir / "voices.yaml").write_text(yaml.dump(voices_data))

    # Mock the config loading to return filtering rules
    with patch(
        "script_to_speech.voice_casting.voice_library_casting_utils.__file__",
        str(utils_dir / "voice_library_casting_utils.py"),
    ):
        with patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.load_config",
            return_value={"included_sts_ids": {"openai": ["alloy", "nova"]}},
        ):
            with patch(
                "script_to_speech.voice_casting.voice_library_casting_utils.get_conflicting_ids",
                return_value={},
            ):
                # Act
                result = generate_voice_library_casting_prompt_file(
                    voice_config_path=voice_config_path, providers=["openai"]
                )

                # Assert
                content = result.read_text()
                assert "alloy" in content
                assert "nova" in content
                assert "shimmer" not in content  # Should be filtered out


def test_generate_voice_library_casting_prompt_file_no_config_no_filtering(
    tmp_path: Path,
):
    """Test that all voices are included when no config filtering is present."""
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

    openai_dir = voice_lib_dir / "openai"
    openai_dir.mkdir()
    voices_data = {
        "voices": {
            "alloy": {"model_id": "tts-1"},
            "nova": {"model_id": "tts-1-hd"},
            "shimmer": {"model_id": "tts-1"},
        }
    }
    (openai_dir / "voices.yaml").write_text(yaml.dump(voices_data))

    # Mock the config loading to return empty config
    with patch(
        "script_to_speech.voice_casting.voice_library_casting_utils.__file__",
        str(utils_dir / "voice_library_casting_utils.py"),
    ):
        with patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.load_config",
            return_value={},
        ):
            with patch(
                "script_to_speech.voice_casting.voice_library_casting_utils.get_conflicting_ids",
                return_value={},
            ):
                # Act
                result = generate_voice_library_casting_prompt_file(
                    voice_config_path=voice_config_path, providers=["openai"]
                )

                # Assert
                content = result.read_text()
                assert "alloy" in content
                assert "nova" in content
                assert "shimmer" in content  # All voices should be included
