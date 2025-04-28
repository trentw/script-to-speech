import io
import os
from datetime import datetime
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest

from script_to_speech.utils.generate_standalone_speech import (
    SPLIT_SENTENCE,
    clean_filename,
    generate_standalone_speech,
    get_command_string,
    get_provider_class,
)


class TestCleanFilename:
    """Tests for the clean_filename function."""

    def test_clean_filename_with_special_chars(self):
        """Test clean_filename with text containing special characters."""
        # Test with various special characters
        text = "Hello, World! This is a test: #123 & (test)"
        result = clean_filename(text)

        # Should remove all special characters and replace spaces with underscore
        assert result == "Hello_World_This_is_a_test_123__test"

    def test_clean_filename_with_spaces(self):
        """Test clean_filename with text containing spaces."""
        text = "Hello World"
        result = clean_filename(text)

        # Should replace spaces with underscore
        assert result == "Hello_World"

    def test_clean_filename_with_unicode(self):
        """Test clean_filename with text containing Unicode characters."""
        text = "Café ñ éèêë"
        result = clean_filename(text)

        # Just check that some Unicode characters are retained
        assert "é" in result or "ñ" in result or "Café" in result


class TestGetProviderClass:
    """Tests for the get_provider_class function."""

    @patch("script_to_speech.utils.generate_standalone_speech.importlib.import_module")
    @patch("script_to_speech.utils.generate_standalone_speech.isinstance")
    @patch("script_to_speech.utils.generate_standalone_speech.issubclass")
    def test_get_provider_class_valid_provider(
        self, mock_issubclass, mock_isinstance, mock_import
    ):
        """Test get_provider_class with a valid provider."""
        # Set up our mocks to return the expected values
        mock_isinstance.return_value = True
        mock_issubclass.return_value = True

        # Create a mock function for get_provider_identifier
        provider_identifier = MagicMock(return_value="test_provider")

        # Create a mock class
        mock_provider = MagicMock()
        # Mock provider_identifier as an attribute that's callable
        mock_provider.get_provider_identifier = provider_identifier

        # Set up the module
        mock_module = MagicMock()
        # Override __dir__ to include our provider
        mock_module.__dir__ = MagicMock(return_value=["TestProvider"])
        # Add the provider to the module
        mock_module.TestProvider = mock_provider
        mock_import.return_value = mock_module

        # Call the function
        result = get_provider_class("test_provider")

        # Verify the result is our mock provider
        assert result is mock_provider

    @patch("script_to_speech.utils.generate_standalone_speech.importlib.import_module")
    def test_get_provider_class_provider_not_found(self, mock_import):
        """Test get_provider_class when provider is not found."""
        # Setup import to raise ImportError
        mock_import.side_effect = ImportError("Provider not found")

        # Call should raise ValueError
        with pytest.raises(ValueError, match="Provider 'nonexistent' not found:"):
            get_provider_class("nonexistent")

    @patch("script_to_speech.utils.generate_standalone_speech.importlib.import_module")
    def test_get_provider_class_no_valid_provider_class(self, mock_import):
        """Test get_provider_class when no valid provider class is found."""
        # Set up mock module with no provider class
        mock_module = MagicMock()
        # No attributes that match the provider
        mock_import.return_value = mock_module

        # Call should raise ValueError
        with pytest.raises(
            ValueError, match="No valid provider class found for test_provider"
        ):
            get_provider_class("test_provider")

    @patch("script_to_speech.utils.generate_standalone_speech.importlib.import_module")
    def test_get_provider_class_provider_identifier_mismatch(self, mock_import):
        """Test get_provider_class when provider identifier doesn't match."""
        # Create mock provider class with a different identifier
        mock_provider = MagicMock()
        mock_provider.get_provider_identifier.return_value = "different_provider"

        # Set up mock module with the provider
        mock_module = MagicMock()
        mock_module.TestProvider = mock_provider
        mock_import.return_value = mock_module

        # Call should raise ValueError
        with pytest.raises(
            ValueError, match="No valid provider class found for test_provider"
        ):
            get_provider_class("test_provider")


class TestGenerateStandaloneSpeech:
    """Tests for the generate_standalone_speech function."""

    class MockProvider:
        @staticmethod
        def instantiate_client():
            return None

        @staticmethod
        def get_provider_identifier():
            return "test_provider"

        @staticmethod
        def get_speaker_identifier(speaker_config):
            return "test_voice"

        @staticmethod
        def generate_audio(client, speaker_config, text):
            return b"test audio data"

    @patch("script_to_speech.utils.generate_standalone_speech.os.makedirs")
    @patch("script_to_speech.utils.generate_standalone_speech.datetime")
    def test_generate_standalone_speech_basic(self, mock_datetime, mock_makedirs):
        """Test basic functionality of generate_standalone_speech."""
        speaker_config = {"voice_id": "test_voice"}
        mock_provider_class = self.MockProvider

        # Mock datetime to return a fixed timestamp
        mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0)

        # Mock open for writing
        with patch("builtins.open", mock_open()) as mock_file:
            # Call function
            generate_standalone_speech(
                mock_provider_class,
                speaker_config,
                "Hello world",
                output_dir="test_output",
            )

            # Verify provider.generate_audio was called correctly
            # The instance is created inside the function, so patch the class to track the instance
            instance = mock_file.call_args_list[0][0][0].split(os.sep)[-1]
            # Instead, check that a file was written with the expected data
            mock_file().write.assert_called_once_with(b"test audio data")

            # Verify output directory was created
            mock_makedirs.assert_called_once_with("test_output", exist_ok=True)

            # Verify file was opened with expected name pattern
            expected_filename = (
                "test_provider--test_voice--Hello_world--20230101_120000.mp3"
            )
            # Check that open was called with the expected filename and mode
            mock_file.assert_any_call(
                os.path.join("test_output", expected_filename), "wb"
            )
            # Ensure it was called exactly once with those arguments
            open_calls = [
                call
                for call in mock_file.call_args_list
                if call == ((os.path.join("test_output", expected_filename), "wb"),)
            ]
            assert (
                len(open_calls) == 1
            ), f"Expected open to be called once with {expected_filename}, but got {len(open_calls)}"

    @patch("script_to_speech.utils.generate_standalone_speech.os.makedirs")
    @patch("script_to_speech.utils.generate_standalone_speech.datetime")
    @patch("script_to_speech.utils.generate_standalone_speech.split_audio_on_silence")
    def test_generate_standalone_speech_with_split(
        self, mock_split, mock_datetime, mock_makedirs
    ):
        """Test generate_standalone_speech with split_audio=True."""
        speaker_config = {"voice_id": "test_voice"}
        mock_provider_class = self.MockProvider

        # Mock split_audio_on_silence
        mock_audio_segment = MagicMock()
        mock_split.return_value = mock_audio_segment

        # Mock audio_segment.export to return bytes
        mock_audio_segment.export.side_effect = lambda f, format: f.write(
            b"split audio data"
        )

        # Mock datetime to return a fixed timestamp
        mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0)

        # Mock open for writing
        with patch("builtins.open", mock_open()) as mock_file:
            # Mock io.BytesIO
            with patch("script_to_speech.utils.generate_standalone_speech.io.BytesIO") as mock_bytesio:
                # Setup BytesIO mock
                mock_buffer = MagicMock()
                mock_bytesio.return_value = mock_buffer
                mock_buffer.getvalue.return_value = b"split audio data"

                # Call function with split_audio=True
                generate_standalone_speech(
                    mock_provider_class,
                    speaker_config,
                    "Hello world",
                    output_dir="test_output",
                    split_audio=True,
                    silence_threshold=-40,
                    min_silence_len=500,
                    keep_silence=100,
                )

                # No direct access to the instance, but we can check file output and split call
                mock_split.assert_called_once_with(
                    b"test audio data",
                    min_silence_len=500,
                    silence_thresh=-40,
                    keep_silence=100,
                )

                # Verify output directory was created
                mock_makedirs.assert_called_once_with("test_output", exist_ok=True)

                # Verify file was opened with expected name pattern (including "split_" prefix)
                expected_filename = (
                    "test_provider--test_voice--split_Hello_world--20230101_120000.mp3"
                )
                mock_file.assert_called_once_with(
                    os.path.join("test_output", expected_filename), "wb"
                )

                # Verify split audio data was written
                mock_file().write.assert_called_once_with(b"split audio data")

    @patch("script_to_speech.utils.generate_standalone_speech.os.makedirs")
    @patch("script_to_speech.utils.generate_standalone_speech.split_audio_on_silence")
    def test_generate_standalone_speech_split_error(self, mock_split, mock_makedirs):
        """Test generate_standalone_speech when splitting fails."""
        speaker_config = {"voice_id": "test_voice"}
        mock_provider_class = self.MockProvider

        # Mock split_audio_on_silence to return None (no silence detected)
        mock_split.return_value = None

        # Call function - should exit early without exception
        generate_standalone_speech(
            mock_provider_class,
            speaker_config,
            "Hello world",
            output_dir="test_output",
            split_audio=True,
        )

        # Verify split_audio_on_silence was called
        mock_split.assert_called_once()

        # No file should be created when split fails

    @patch("script_to_speech.utils.generate_standalone_speech.os.makedirs")
    @patch("script_to_speech.utils.generate_standalone_speech.split_audio_on_silence")
    def test_generate_standalone_speech_split_exception(
        self, mock_split, mock_makedirs
    ):
        """Test generate_standalone_speech when splitting raises exception."""
        speaker_config = {"voice_id": "test_voice"}
        mock_provider_class = self.MockProvider

        # Mock split_audio_on_silence to raise exception
        mock_split.side_effect = Exception("Split error")

        # Call function - should exit early without exception
        generate_standalone_speech(
            mock_provider_class,
            speaker_config,
            "Hello world",
            output_dir="test_output",
            split_audio=True,
        )

        # Verify split_audio_on_silence was called
        mock_split.assert_called_once()

        # No file should be created when split raises exception

    @patch("script_to_speech.utils.generate_standalone_speech.os.makedirs")
    def test_generate_standalone_speech_with_long_text(self, mock_makedirs):
        """Test generate_standalone_speech with long text."""
        speaker_config = {"voice_id": "test_voice"}
        mock_provider_class = self.MockProvider

        # Mock datetime to return a fixed timestamp
        with patch("script_to_speech.utils.generate_standalone_speech.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0)

            # Mock open for writing
            with patch("builtins.open", mock_open()) as mock_file:
                # Call function with long text
                long_text = (
                    "This is a very long text that should be truncated in the filename"
                )
                generate_standalone_speech(
                    mock_provider_class,
                    speaker_config,
                    long_text,
                    output_dir="test_output",
                )

                # Verify filename only includes first 30 chars of text
                expected_text_part = clean_filename(long_text[:30])
                expected_filename = f"test_provider--test_voice--{expected_text_part}--20230101_120000.mp3"
                mock_file.assert_called_once_with(
                    os.path.join("test_output", expected_filename), "wb"
                )

    @patch("script_to_speech.utils.generate_standalone_speech.os.makedirs")
    def test_generate_standalone_speech_with_variant(self, mock_makedirs):
        """Test generate_standalone_speech with variant number > 1."""
        speaker_config = {"voice_id": "test_voice"}
        mock_provider_class = self.MockProvider

        # Mock datetime to return a fixed timestamp
        with patch("script_to_speech.utils.generate_standalone_speech.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0)

            # Mock open for writing
            with patch("builtins.open", mock_open()) as mock_file:
                # Call function with variant_num > 1
                generate_standalone_speech(
                    mock_provider_class,
                    speaker_config,
                    "Hello world",
                    variant_num=2,
                    output_dir="test_output",
                )

                # Verify filename includes variant suffix
                expected_filename = "test_provider--test_voice--Hello_world_variant2--20230101_120000.mp3"
                mock_file.assert_called_once_with(
                    os.path.join("test_output", expected_filename), "wb"
                )

    def test_generate_standalone_speech_provider_error(self):
        """Test generate_standalone_speech when provider raises error."""

        class ErrorProvider:
            def __init__(self, speaker_config):
                self.get_provider_identifier = Mock(return_value="test_provider")
                self.get_speaker_identifier = Mock(return_value="test_voice")
                self.generate_audio = Mock(side_effect=Exception("Provider error"))

        speaker_config = {"voice_id": "test_voice"}

        # Call function - should not raise exception
        generate_standalone_speech(
            ErrorProvider, speaker_config, "Hello world", output_dir="test_output"
        )

        # Function should just log the error and return


class TestGetCommandString:
    """Tests for the get_command_string function."""

    def test_get_command_string_basic(self):
        """Test basic functionality of get_command_string."""
        # Mock provider manager
        mock_manager = MagicMock()
        mock_manager.get_provider_for_speaker.return_value = "test_provider"
        mock_manager.get_speaker_configuration.return_value = {
            "voice_id": "test_voice",
            "model": "test_model",
        }

        # Call function
        result = get_command_string(
            provider_manager=mock_manager, speaker="test_speaker", texts=["Hello world"]
        )

        # Verify provider was looked up correctly
        mock_manager.get_provider_for_speaker.assert_called_once_with("test_speaker")

        # Verify configuration was retrieved
        mock_manager.get_speaker_configuration.assert_called_once_with("test_speaker")

        # Verify result contains expected command components
        assert "python -m script_to_speech.utils.generate_standalone_speech test_provider" in result
        assert "--voice_id test_voice" in result
        assert "--model test_model" in result
        assert '"Hello world"' in result

    def test_get_command_string_with_default_speaker(self):
        """Test get_command_string with '(default)' speaker."""
        # Mock provider manager
        mock_manager = MagicMock()
        mock_manager.get_provider_for_speaker.return_value = "test_provider"
        mock_manager.get_speaker_configuration.return_value = {
            "voice_id": "default_voice",
        }

        # Call function with (default) speaker
        result = get_command_string(
            provider_manager=mock_manager, speaker="(default)", texts=["Hello world"]
        )

        # Verify provider was looked up correctly (with "default")
        mock_manager.get_provider_for_speaker.assert_called_once_with("default")

        # Verify result uses the expected values
        assert "python -m script_to_speech.utils.generate_standalone_speech test_provider" in result
        assert "--voice_id default_voice" in result
        assert '"Hello world"' in result

    def test_get_command_string_with_none_speaker(self):
        """Test get_command_string with None speaker."""
        # Mock provider manager
        mock_manager = MagicMock()
        mock_manager.get_provider_for_speaker.return_value = "test_provider"
        mock_manager.get_speaker_configuration.return_value = {
            "voice_id": "default_voice",
        }

        # Call function with None speaker
        result = get_command_string(
            provider_manager=mock_manager, speaker=None, texts=["Hello world"]
        )

        # Verify provider was looked up correctly (with "default")
        mock_manager.get_provider_for_speaker.assert_called_once_with("default")

        # Verify result uses the expected values
        assert "python -m script_to_speech.utils.generate_standalone_speech test_provider" in result
        assert "--voice_id default_voice" in result
        assert '"Hello world"' in result

    def test_get_command_string_with_none_params(self):
        """Test get_command_string with None parameter values."""
        # Mock provider manager
        mock_manager = MagicMock()
        mock_manager.get_provider_for_speaker.return_value = "test_provider"
        mock_manager.get_speaker_configuration.return_value = {
            "voice_id": "test_voice",
            "model": None,  # None value should be excluded
            "stability": 0.5,  # Non-None value should be included
        }

        # Call function
        result = get_command_string(
            provider_manager=mock_manager, speaker="test_speaker", texts=["Hello world"]
        )

        # Verify result includes only non-None params
        assert "--voice_id test_voice" in result
        assert "--stability 0.5" in result
        assert "--model" not in result

    def test_get_command_string_with_multiple_texts(self):
        """Test get_command_string with multiple text strings."""
        # Mock provider manager
        mock_manager = MagicMock()
        mock_manager.get_provider_for_speaker.return_value = "test_provider"
        mock_manager.get_speaker_configuration.return_value = {
            "voice_id": "test_voice",
        }

        # Call function with multiple texts
        result = get_command_string(
            provider_manager=mock_manager,
            speaker="test_speaker",
            texts=["Hello world", "Another text", "Third text"],
        )

        # Verify result contains all text strings
        assert '"Hello world"' in result
        assert '"Another text"' in result
        assert '"Third text"' in result

    def test_get_command_string_error_handling(self):
        """Test get_command_string error handling."""
        # Mock provider manager that raises exception
        mock_manager = MagicMock()
        mock_manager.get_provider_for_speaker.side_effect = Exception("Provider error")

        # Call function - should not raise exception
        result = get_command_string(
            provider_manager=mock_manager, speaker="test_speaker", texts=["Hello world"]
        )

        # Result should be empty string on error
        assert result == ""
