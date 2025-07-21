import tempfile
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest
import yaml

from script_to_speech.tts_providers.base.exceptions import VoiceNotFoundError
from script_to_speech.voice_casting.voice_library_casting_utils import (
    _filter_provider_voices,
    generate_voice_library_casting_prompt_file,
)


def test_generate_voice_library_casting_prompt_file_success():
    """Test successful prompt file generation with all required files."""
    # Arrange
    voice_config_content = "characters:\n  - name: John\n"
    prompt_content = "This is the default prompt."
    schema_content = "schema: voice_library\n"

    # Mock VoiceLibrary to return test data
    with patch(
        "script_to_speech.voice_casting.voice_library_casting_utils.VoiceLibrary"
    ) as MockVoiceLibrary:
        mock_instance = MockVoiceLibrary.return_value
        mock_instance._load_provider_voices.side_effect = [
            {"voice1": {"model_id": "tts-1"}},  # openai
            {"voice2": {"model_id": "eleven"}},  # elevenlabs
        ]

        # Create separate mock files for different read operations
        voice_config_mock = mock_open(read_data=voice_config_content)
        schema_mock = mock_open(read_data=schema_content)
        output_mock = mock_open()

        def mock_open_side_effect(file_path, mode="r", *args, **kwargs):
            file_str = str(file_path)
            if "config.yaml" in file_str and mode == "r":
                return voice_config_mock.return_value
            elif "schema.yaml" in file_str and mode == "r":
                return schema_mock.return_value
            elif mode == "w":
                return output_mock.return_value
            return mock_open().return_value

        with (
            patch(
                "script_to_speech.voice_casting.voice_library_casting_utils.load_config",
                return_value={},
            ),
            patch(
                "script_to_speech.voice_casting.voice_library_casting_utils.get_conflicting_ids",
                return_value={},
            ),
            patch(
                "script_to_speech.voice_casting.voice_library_casting_utils.read_prompt_file",
                return_value=prompt_content,
            ),
            patch("builtins.open", side_effect=mock_open_side_effect),
            patch.object(Path, "is_file", return_value=True),
            patch.object(Path, "mkdir"),
        ):
            # Act
            result = generate_voice_library_casting_prompt_file(
                voice_config_path=Path("/fake/config.yaml"),
                providers=["openai", "elevenlabs"],
            )

    # Assert
    assert result == Path("/fake/config_voice_library_casting_prompt.txt")

    # Verify VoiceLibrary was called correctly
    assert mock_instance._load_provider_voices.call_count == 2


def test_generate_voice_library_casting_prompt_file_custom_output_path():
    """Test with custom output file path."""
    # Arrange
    voice_config_content = "characters:\n  - name: John\n"
    prompt_content = "Default prompt"
    schema_content = "schema: test"
    custom_output = Path("/fake/custom_output.txt")

    # Mock VoiceLibrary to return test data
    mock_voice_library = patch(
        "script_to_speech.voice_casting.voice_library_casting_utils.VoiceLibrary"
    )

    with mock_voice_library as MockVoiceLibrary:
        mock_instance = MockVoiceLibrary.return_value
        mock_instance._load_provider_voices.return_value = {}

        with (
            patch(
                "script_to_speech.voice_casting.voice_library_casting_utils.load_config",
                return_value={},
            ),
            patch(
                "script_to_speech.voice_casting.voice_library_casting_utils.get_conflicting_ids",
                return_value={},
            ),
            patch(
                "script_to_speech.voice_casting.voice_library_casting_utils.read_prompt_file",
                return_value=prompt_content,
            ),
            patch("builtins.open", mock_open(read_data=voice_config_content)),
            patch(
                "pathlib.Path.is_file",
                return_value=True,
            ),
            patch(
                "pathlib.Path.parent",
            ),
            patch(
                "pathlib.Path.mkdir",
            ),
        ):
            # Act
            result = generate_voice_library_casting_prompt_file(
                voice_config_path=Path("/fake/config.yaml"),
                providers=["openai"],
                output_file_path=custom_output,
            )

    # Assert
    assert result == custom_output


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


def test_generate_voice_library_casting_prompt_file_missing_schema():
    """Test with missing voice library schema file."""
    # Arrange
    voice_config_content = "test"
    prompt_content = "prompt"

    with (
        patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.load_config",
            return_value={},
        ),
        patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.get_conflicting_ids",
            return_value={},
        ),
        patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.read_prompt_file",
            return_value=prompt_content,
        ),
        patch("builtins.open", mock_open(read_data=voice_config_content)),
        patch.object(Path, "is_file", return_value=True),
        patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.load_merged_schemas_for_providers",
            side_effect=ValueError("No global schema files found"),
        ),
    ):
        # Act/Assert
        with pytest.raises(
            ValueError,
            match="Error loading voice library schema: No global schema files found",
        ):
            generate_voice_library_casting_prompt_file(
                voice_config_path=Path("/fake/config.yaml"), providers=["openai"]
            )


def test_generate_voice_library_casting_prompt_file_missing_provider_voices():
    """Test with missing provider voice library file."""
    # Arrange
    voice_config_content = "test"
    prompt_content = "prompt"
    schema_content = {"voice_properties": {"age": {"type": "range"}}}

    # Mock VoiceLibrary to raise VoiceNotFoundError
    mock_voice_library = patch(
        "script_to_speech.voice_casting.voice_library_casting_utils.VoiceLibrary"
    )

    with mock_voice_library as MockVoiceLibrary:
        mock_instance = MockVoiceLibrary.return_value
        mock_instance._load_provider_voices.side_effect = VoiceNotFoundError(
            "No voice library found for provider 'openai'"
        )

        with (
            patch(
                "script_to_speech.voice_casting.voice_library_casting_utils.load_config",
                return_value={},
            ),
            patch(
                "script_to_speech.voice_casting.voice_library_casting_utils.get_conflicting_ids",
                return_value={},
            ),
            patch(
                "script_to_speech.voice_casting.voice_library_casting_utils.read_prompt_file",
                return_value=prompt_content,
            ),
            patch("builtins.open", mock_open(read_data=voice_config_content)),
            patch(
                "pathlib.Path.is_file",
                return_value=True,
            ),
            patch(
                "script_to_speech.voice_casting.voice_library_casting_utils.load_merged_schemas_for_providers",
                return_value=schema_content,
            ),
        ):
            # Act/Assert
            with pytest.raises(
                ValueError,
                match="Error processing voice library data for provider 'openai'",
            ):
                generate_voice_library_casting_prompt_file(
                    voice_config_path=Path("/fake/config.yaml"), providers=["openai"]
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


def test_generate_voice_library_casting_prompt_file_multiple_providers():
    """Test with multiple providers."""
    # Arrange
    voice_config_content = "test"
    prompt_content = "prompt"
    schema_content = {"voice_properties": {"age": {"type": "range"}}}

    # Mock VoiceLibrary to return test data for multiple providers
    mock_voice_library = patch(
        "script_to_speech.voice_casting.voice_library_casting_utils.VoiceLibrary"
    )

    with mock_voice_library as MockVoiceLibrary:
        mock_instance = MockVoiceLibrary.return_value
        # Return different data for each provider call
        mock_instance._load_provider_voices.side_effect = [
            {"openai_voice": {"model_id": "tts-1"}},  # openai
            {"elevenlabs_voice": {"model_id": "eleven"}},  # elevenlabs
        ]

        # Create separate mock files for different read operations
        voice_config_mock = mock_open(read_data=voice_config_content)
        output_mock = mock_open()

        def mock_open_side_effect(file_path, mode="r", *args, **kwargs):
            file_str = str(file_path)
            if "config.yaml" in file_str and mode == "r":
                return voice_config_mock.return_value
            elif mode == "w":
                return output_mock.return_value
            return mock_open().return_value

        with (
            patch(
                "script_to_speech.voice_casting.voice_library_casting_utils.load_config",
                return_value={},
            ),
            patch(
                "script_to_speech.voice_casting.voice_library_casting_utils.get_conflicting_ids",
                return_value={},
            ),
            patch(
                "script_to_speech.voice_casting.voice_library_casting_utils.read_prompt_file",
                return_value=prompt_content,
            ),
            patch("builtins.open", side_effect=mock_open_side_effect),
            patch.object(Path, "is_file", return_value=True),
            patch.object(Path, "mkdir"),
            patch(
                "script_to_speech.voice_casting.voice_library_casting_utils.load_merged_schemas_for_providers",
                return_value=schema_content,
            ),
        ):

            # Act
            result = generate_voice_library_casting_prompt_file(
                voice_config_path=Path("/fake/config.yaml"),
                providers=["openai", "elevenlabs"],
            )

    # Assert
    assert result == Path("/fake/config_voice_library_casting_prompt.txt")

    # Verify VoiceLibrary was called for each provider
    assert mock_instance._load_provider_voices.call_count == 2
    mock_instance._load_provider_voices.assert_any_call("openai")
    mock_instance._load_provider_voices.assert_any_call("elevenlabs")


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
    prompt_content = "prompt"
    schema_content = {"voice_properties": {"age": {"type": "range"}}}
    
    # Test voices data - this will be returned by the mocked VoiceLibrary
    voices_data = {
        "alloy": {"model_id": "tts-1"},
        "nova": {"model_id": "tts-1-hd"},
        "shimmer": {"model_id": "tts-1"},
    }

    # Mock VoiceLibrary to return test data
    output_mock = mock_open()
    
    def mock_open_side_effect(file_path, mode="r", *args, **kwargs):
        file_str = str(file_path)
        if "config.yaml" in file_str and mode == "r":
            return mock_open(read_data="test").return_value
        elif mode == "w":
            return output_mock.return_value
        return mock_open().return_value

    with (
        patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.VoiceLibrary"
        ) as MockVoiceLibrary,
        patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.load_config",
            return_value={"included_sts_ids": {"openai": ["alloy", "nova"]}},
        ),
        patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.get_conflicting_ids",
            return_value={},
        ),
        patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.read_prompt_file",
            return_value=prompt_content,
        ),
        patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.load_merged_schemas_for_providers",
            return_value=schema_content,
        ),
        patch("builtins.open", side_effect=mock_open_side_effect),
        patch.object(Path, "is_file", return_value=True),
        patch.object(Path, "mkdir"),
    ):
        mock_instance = MockVoiceLibrary.return_value
        mock_instance._load_provider_voices.return_value = voices_data

        # Act
        result = generate_voice_library_casting_prompt_file(
            voice_config_path=voice_config_path, providers=["openai"]
        )

        # Assert - check the content that was written to the file
        output_mock().write.assert_called_once()
        written_content = output_mock().write.call_args[0][0]
        
        assert "alloy" in written_content
        assert "nova" in written_content
        assert "shimmer" not in written_content  # Should be filtered out


def test_generate_voice_library_casting_prompt_file_no_config_no_filtering():
    """Test that all voices are included when no config filtering is present."""
    # Arrange
    voice_config_content = "test"
    prompt_content = "prompt"
    schema_content = {"voice_properties": {"age": {"type": "range"}}}
    voices_data = {
        "voices": {
            "alloy": {"model_id": "tts-1"},
            "nova": {"model_id": "tts-1-hd"},
            "shimmer": {"model_id": "tts-1"},
        }
    }
    output_mock = mock_open()

    def mock_open_side_effect(file_path, mode="r", *args, **kwargs):
        file_str = str(file_path)
        if "config.yaml" in file_str:
            return mock_open(read_data=voice_config_content).return_value
        elif mode == "w":
            return output_mock.return_value
        return mock_open().return_value

    with (
        patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.VoiceLibrary"
        ) as MockVoiceLibrary,
        patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.load_config",
            return_value={},
        ),
        patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.get_conflicting_ids",
            return_value={},
        ),
        patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.read_prompt_file",
            return_value=prompt_content,
        ),
        patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.load_merged_schemas_for_providers",
            return_value=schema_content,
        ),
        patch("builtins.open", side_effect=mock_open_side_effect),
        patch.object(Path, "is_file", return_value=True),
        patch.object(Path, "mkdir"),
    ):
        mock_instance = MockVoiceLibrary.return_value
        mock_instance._load_provider_voices.return_value = voices_data

        # Act
        generate_voice_library_casting_prompt_file(
            voice_config_path=Path("/fake/config.yaml"), providers=["openai"]
        )

        # Assert
        output_mock().write.assert_called_once()
        written_content = output_mock().write.call_args[0][0]

        assert "alloy" in written_content
        assert "nova" in written_content
        assert "shimmer" in written_content


def test_generate_voice_library_casting_prompt_file_with_additional_instructions():
    """Test that additional voice casting instructions are included in prompt."""
    # Arrange
    voice_config_content = "test"
    prompt_content = "prompt"
    schema_content = {"voice_properties": {"age": {"type": "range"}}}
    voices_data = {
        "voices": {
            "alloy": {"model_id": "tts-1"},
            "nova": {"model_id": "tts-1-hd"},
        }
    }

    # Config with additional instructions
    config_with_instructions = {
        "additional_voice_casting_instructions": {
            "openai": [
                "Use dramatic voices for action scenes",
                "Prefer younger sounding voices",
            ],
            "elevenlabs": ["Use British accents when available"],
        }
    }

    output_mock = mock_open()

    def mock_open_side_effect(file_path, mode="r", *args, **kwargs):
        file_str = str(file_path)
        if "config.yaml" in file_str:
            return mock_open(read_data=voice_config_content).return_value
        elif mode == "w":
            return output_mock.return_value
        return mock_open().return_value

    with (
        patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.VoiceLibrary"
        ) as MockVoiceLibrary,
        patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.load_config",
            return_value=config_with_instructions,
        ),
        patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.get_conflicting_ids",
            return_value={},
        ),
        patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.read_prompt_file",
            return_value=prompt_content,
        ),
        patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.load_merged_schemas_for_providers",
            return_value=schema_content,
        ),
        patch("builtins.open", side_effect=mock_open_side_effect),
        patch.object(Path, "is_file", return_value=True),
        patch.object(Path, "mkdir"),
    ):
        mock_instance = MockVoiceLibrary.return_value
        mock_instance._load_provider_voices.side_effect = [
            voices_data,  # openai
            voices_data,  # elevenlabs
        ]

        # Act
        generate_voice_library_casting_prompt_file(
            voice_config_path=Path("/fake/config.yaml"),
            providers=["openai", "elevenlabs"],
        )

        # Assert
        output_mock().write.assert_called_once()
        written_content = output_mock().write.call_args[0][0]

        # Check that additional instructions are included for openai
        assert "When casting for this provider (openai)" in written_content
        assert "Use dramatic voices for action scenes" in written_content
        assert "Prefer younger sounding voices" in written_content

        # Check that additional instructions are included for elevenlabs
        assert "When casting for this provider (elevenlabs)" in written_content
        assert "Use British accents when available" in written_content


def test_generate_voice_library_casting_prompt_file_no_additional_instructions():
    """Test that prompt generation works without additional instructions."""
    # Arrange
    voice_config_content = "test"
    prompt_content = "prompt"
    schema_content = {"voice_properties": {"age": {"type": "range"}}}
    voices_data = {
        "voices": {
            "alloy": {"model_id": "tts-1"},
        }
    }

    # Config without additional instructions
    config_without_instructions = {}

    output_mock = mock_open()

    def mock_open_side_effect(file_path, mode="r", *args, **kwargs):
        file_str = str(file_path)
        if "config.yaml" in file_str:
            return mock_open(read_data=voice_config_content).return_value
        elif mode == "w":
            return output_mock.return_value
        return mock_open().return_value

    with (
        patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.VoiceLibrary"
        ) as MockVoiceLibrary,
        patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.load_config",
            return_value=config_without_instructions,
        ),
        patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.get_conflicting_ids",
            return_value={},
        ),
        patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.read_prompt_file",
            return_value=prompt_content,
        ),
        patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.load_merged_schemas_for_providers",
            return_value=schema_content,
        ),
        patch("builtins.open", side_effect=mock_open_side_effect),
        patch.object(Path, "is_file", return_value=True),
        patch.object(Path, "mkdir"),
    ):
        mock_instance = MockVoiceLibrary.return_value
        mock_instance._load_provider_voices.return_value = voices_data

        # Act
        generate_voice_library_casting_prompt_file(
            voice_config_path=Path("/fake/config.yaml"), providers=["openai"]
        )

        # Assert
        output_mock().write.assert_called_once()
        written_content = output_mock().write.call_args[0][0]

        # Check that no additional instructions are included
        assert "When casting for this provider" not in written_content
        assert "Use dramatic voices" not in written_content


def test_generate_voice_library_casting_prompt_file_partial_additional_instructions():
    """Test that only providers with instructions get them included."""
    # Arrange
    voice_config_content = "test"
    prompt_content = "prompt"
    schema_content = {"voice_properties": {"age": {"type": "range"}}}
    voices_data = {
        "voices": {
            "alloy": {"model_id": "tts-1"},
        }
    }

    # Config with instructions for only one provider
    config_with_partial_instructions = {
        "additional_voice_casting_instructions": {
            "openai": ["Use dramatic voices for action scenes"]
        }
    }

    output_mock = mock_open()

    def mock_open_side_effect(file_path, mode="r", *args, **kwargs):
        file_str = str(file_path)
        if "config.yaml" in file_str:
            return mock_open(read_data=voice_config_content).return_value
        elif mode == "w":
            return output_mock.return_value
        return mock_open().return_value

    with (
        patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.VoiceLibrary"
        ) as MockVoiceLibrary,
        patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.load_config",
            return_value=config_with_partial_instructions,
        ),
        patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.get_conflicting_ids",
            return_value={},
        ),
        patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.read_prompt_file",
            return_value=prompt_content,
        ),
        patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.load_merged_schemas_for_providers",
            return_value=schema_content,
        ),
        patch("builtins.open", side_effect=mock_open_side_effect),
        patch.object(Path, "is_file", return_value=True),
        patch.object(Path, "mkdir"),
    ):
        mock_instance = MockVoiceLibrary.return_value
        mock_instance._load_provider_voices.side_effect = [
            voices_data,  # openai
            voices_data,  # elevenlabs
        ]

        # Act
        generate_voice_library_casting_prompt_file(
            voice_config_path=Path("/fake/config.yaml"),
            providers=["openai", "elevenlabs"],
        )

        # Assert
        output_mock().write.assert_called_once()
        written_content = output_mock().write.call_args[0][0]

        # Check that instructions are included for openai but not elevenlabs
        assert "When casting for this provider (openai)" in written_content
        assert "Use dramatic voices for action scenes" in written_content
        assert "When casting for this provider (elevenlabs)" not in written_content


def test_generate_voice_library_casting_prompt_file_with_overall_voice_casting_prompt():
    """Test that overall_voice_casting_prompt is included in the initial prompt section."""
    # Arrange
    voice_config_content = "test"
    prompt_content = "This is the initial prompt."
    schema_content = {"voice_properties": {"age": {"type": "range"}}}
    voices_data = {
        "voices": {
            "alloy": {"model_id": "tts-1"},
        }
    }

    # Config with only overall instructions
    config_with_overall = {
        "additional_voice_casting_instructions": {
            "overall_voice_casting_prompt": [
                "Focus on character emotional state",
                "Maintain consistency across scenes",
            ]
        }
    }

    output_mock = mock_open()

    def mock_open_side_effect(file_path, mode="r", *args, **kwargs):
        file_str = str(file_path)
        if "config.yaml" in file_str:
            return mock_open(read_data=voice_config_content).return_value
        elif mode == "w":
            return output_mock.return_value
        return mock_open().return_value

    with (
        patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.VoiceLibrary"
        ) as MockVoiceLibrary,
        patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.load_config",
            return_value=config_with_overall,
        ),
        patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.get_conflicting_ids",
            return_value={},
        ),
        patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.read_prompt_file",
            return_value=prompt_content,
        ),
        patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.load_merged_schemas_for_providers",
            return_value=schema_content,
        ),
        patch("builtins.open", side_effect=mock_open_side_effect),
        patch.object(Path, "is_file", return_value=True),
        patch.object(Path, "mkdir"),
    ):
        mock_instance = MockVoiceLibrary.return_value
        mock_instance._load_provider_voices.return_value = voices_data

        # Act
        generate_voice_library_casting_prompt_file(
            voice_config_path=Path("/fake/config.yaml"), providers=["openai"]
        )

        # Assert
        output_mock().write.assert_called_once()
        written_content = output_mock().write.call_args[0][0]

        # Check that overall instructions appear in the initial section
        assert (
            "Additionally, please abide by the following instructions when casting voices:"
            in written_content
        )
        assert "Focus on character emotional state" in written_content
        assert "Maintain consistency across scenes" in written_content

        # Check that it appears before the voice library schema section
        overall_pos = written_content.find(
            "Additionally, please abide by the following instructions when casting voices:"
        )
        schema_pos = written_content.find("--- VOICE LIBRARY SCHEMA ---")
        assert overall_pos < schema_pos

        # Check that no provider-specific instructions appear
        assert "When casting for this provider" not in written_content


def test_generate_voice_library_casting_prompt_file_with_overall_and_provider_instructions():
    """Test combination of overall and provider-specific instructions."""
    # Arrange
    voice_config_content = "test"
    prompt_content = "This is the initial prompt."
    schema_content = {"voice_properties": {"age": {"type": "range"}}}
    voices_data = {
        "voices": {
            "alloy": {"model_id": "tts-1"},
        }
    }

    # Config with both overall and provider-specific instructions
    config_with_both = {
        "additional_voice_casting_instructions": {
            "overall_voice_casting_prompt": ["Focus on character emotional state"],
            "openai": ["Use dramatic voices for action scenes"],
            "elevenlabs": ["Use British accents when available"],
        }
    }

    output_mock = mock_open()

    def mock_open_side_effect(file_path, mode="r", *args, **kwargs):
        file_str = str(file_path)
        if "config.yaml" in file_str:
            return mock_open(read_data=voice_config_content).return_value
        elif mode == "w":
            return output_mock.return_value
        return mock_open().return_value

    with (
        patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.VoiceLibrary"
        ) as MockVoiceLibrary,
        patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.load_config",
            return_value=config_with_both,
        ),
        patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.get_conflicting_ids",
            return_value={},
        ),
        patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.read_prompt_file",
            return_value=prompt_content,
        ),
        patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.load_merged_schemas_for_providers",
            return_value=schema_content,
        ),
        patch("builtins.open", side_effect=mock_open_side_effect),
        patch.object(Path, "is_file", return_value=True),
        patch.object(Path, "mkdir"),
    ):
        mock_instance = MockVoiceLibrary.return_value
        mock_instance._load_provider_voices.side_effect = [
            voices_data,  # openai
            voices_data,  # elevenlabs
        ]

        # Act
        generate_voice_library_casting_prompt_file(
            voice_config_path=Path("/fake/config.yaml"),
            providers=["openai", "elevenlabs"],
        )

        # Assert
        output_mock().write.assert_called_once()
        written_content = output_mock().write.call_args[0][0]

        # Check that overall instructions appear in the initial section
        assert (
            "Additionally, please abide by the following instructions when casting voices:"
            in written_content
        )
        assert "Focus on character emotional state" in written_content

        # Check that provider-specific instructions appear for openai but not overall_voice_casting_prompt
        assert "When casting for this provider (openai)" in written_content
        assert "Use dramatic voices for action scenes" in written_content

        # Check that elevenlabs instructions appear
        assert "When casting for this provider (elevenlabs)" in written_content
        assert "Use British accents when available" in written_content

        # Check positioning: overall comes before schema, provider instructions come after their headers
        overall_pos = written_content.find(
            "Additionally, please abide by the following instructions when casting voices:"
        )
        schema_pos = written_content.find("--- VOICE LIBRARY SCHEMA ---")
        openai_provider_pos = written_content.find(
            "When casting for this provider (openai)"
        )
        openai_header_pos = written_content.find("--- VOICE LIBRARY DATA (OPENAI) ---")

        assert overall_pos < schema_pos
        assert openai_header_pos < openai_provider_pos


def test_generate_voice_library_casting_prompt_file_overall_voice_casting_prompt_not_in_provider_sections():
    """Test that overall_voice_casting_prompt is not treated as a provider."""
    # Arrange
    voice_config_content = "test"
    prompt_content = "This is the initial prompt."
    schema_content = {"voice_properties": {"age": {"type": "range"}}}
    voices_data = {
        "voices": {
            "alloy": {"model_id": "tts-1"},
        }
    }

    # Config with overall_voice_casting_prompt that should not be treated as a provider
    config_with_overall = {
        "additional_voice_casting_instructions": {
            "overall_voice_casting_prompt": ["Focus on character emotional state"]
        }
    }

    output_mock = mock_open()

    def mock_open_side_effect(file_path, mode="r", *args, **kwargs):
        file_str = str(file_path)
        if "config.yaml" in file_str:
            return mock_open(read_data=voice_config_content).return_value
        elif mode == "w":
            return output_mock.return_value
        return mock_open().return_value

    with (
        patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.VoiceLibrary"
        ) as MockVoiceLibrary,
        patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.load_config",
            return_value=config_with_overall,
        ),
        patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.get_conflicting_ids",
            return_value={},
        ),
        patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.read_prompt_file",
            return_value=prompt_content,
        ),
        patch(
            "script_to_speech.voice_casting.voice_library_casting_utils.load_merged_schemas_for_providers",
            return_value=schema_content,
        ),
        patch("builtins.open", side_effect=mock_open_side_effect),
        patch.object(Path, "is_file", return_value=True),
        patch.object(Path, "mkdir"),
    ):
        mock_instance = MockVoiceLibrary.return_value
        mock_instance._load_provider_voices.return_value = voices_data

        # Act
        # Pass "overall_voice_casting_prompt" as a provider to ensure it doesn't get processed as one
        generate_voice_library_casting_prompt_file(
            voice_config_path=Path("/fake/config.yaml"),
            providers=["openai", "overall_voice_casting_prompt"],
        )

        # Assert
        output_mock().write.assert_called_once()
        written_content = output_mock().write.call_args[0][0]

        # Check that overall instructions appear in the initial section
        assert (
            "Additionally, please abide by the following instructions when casting voices:"
            in written_content
        )
        assert "Focus on character emotional state" in written_content

        # Check that there's no provider section for "overall_voice_casting_prompt"
        assert (
            "--- VOICE LIBRARY DATA (OVERALL_VOICE_CASTING_PROMPT) ---"
            in written_content
        )
        # But there should be no provider-specific instructions for it
        assert (
            "When casting for this provider (overall_voice_casting_prompt)"
            not in written_content
        )
