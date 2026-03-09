"""Tests for audio analyzer logic."""

import base64
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.audio_analyzer import (
    INITIAL_BACKOFF,
    MAX_RETRIES,
    analyze_voice,
    analyze_voice_batch,
    encode_audio_base64,
    get_openrouter_client,
)


def _mock_completion_response(content):
    """Build a mock OpenAI chat completion response."""
    mock_choice = MagicMock()
    mock_choice.message.content = content
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


def _valid_json_response():
    """Return a valid voice analysis JSON string."""
    return json.dumps(
        {
            "voice_properties": {
                "age": 0.5,
                "pitch": 0.4,
                "gender": "male",
                "accent": "american",
            },
            "description": {"custom_description": "test"},
            "tags": {"character_types": ["narrator"]},
        }
    )


class TestGetOpenrouterClient:
    """Tests for get_openrouter_client()."""

    @patch(
        "script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.audio_analyzer.OpenAI"
    )
    @patch(
        "script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.audio_analyzer.load_environment_variables"
    )
    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "test_key_123"})
    def test_returns_client_with_key(self, _mock_env, mock_openai):
        # Act
        result = get_openrouter_client()

        # Assert
        assert result is not None
        mock_openai.assert_called_once()

    @patch(
        "script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.audio_analyzer.load_environment_variables"
    )
    @patch.dict(os.environ, {}, clear=True)
    def test_raises_without_key(self, _mock_env):
        # Act & Assert
        with pytest.raises(ValueError):
            get_openrouter_client()


class TestEncodeAudioBase64:
    """Tests for encode_audio_base64()."""

    @patch("builtins.open", new_callable=mock_open, read_data=b"fake_audio_data")
    def test_returns_decodable_base64(self, _mock_file):
        # Act
        result = encode_audio_base64("/fake/path.mp3")

        # Assert
        assert isinstance(result, str)
        # Verify it's valid base64 by decoding
        decoded = base64.b64decode(result)
        assert decoded == b"fake_audio_data"


class TestAnalyzeVoice:
    """Tests for analyze_voice()."""

    @patch(
        "script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.audio_analyzer.encode_audio_base64",
        return_value="base64data",
    )
    def test_single_clip_builds_one_audio(self, _mock_encode):
        # Arrange
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_completion_response(
            _valid_json_response()
        )

        # Act
        result = analyze_voice(
            client=mock_client,
            model="test-model",
            system_prompt="system",
            user_message="analyze",
            audio_path="/fake/audio.mp3",
        )

        # Assert
        assert "voice_properties" in result
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args[1]["messages"]
        user_content = messages[1]["content"]
        # Count input_audio entries
        audio_entries = [c for c in user_content if c.get("type") == "input_audio"]
        assert len(audio_entries) == 1

    @patch(
        "script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.audio_analyzer.encode_audio_base64",
        return_value="base64data",
    )
    def test_dual_clips_builds_two_audios(self, _mock_encode):
        # Arrange
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_completion_response(
            _valid_json_response()
        )

        # Act
        result = analyze_voice(
            client=mock_client,
            model="test-model",
            system_prompt="system",
            user_message="analyze",
            audio_paths={
                "neutral": "/fake/neutral.mp3",
                "expressive": "/fake/expressive.mp3",
            },
        )

        # Assert
        assert "voice_properties" in result
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args[1]["messages"]
        user_content = messages[1]["content"]
        audio_entries = [c for c in user_content if c.get("type") == "input_audio"]
        assert len(audio_entries) == 2

    def test_no_audio_raises(self):
        # Arrange
        mock_client = MagicMock()

        # Act & Assert
        with pytest.raises(ValueError):
            analyze_voice(
                client=mock_client,
                model="test-model",
                system_prompt="system",
                user_message="analyze",
            )

    @patch(
        "script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.audio_analyzer.encode_audio_base64",
        return_value="base64data",
    )
    def test_strips_markdown_fences(self, _mock_encode):
        # Arrange
        fenced_json = "```json\n" + _valid_json_response() + "\n```"
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_completion_response(
            fenced_json
        )

        # Act
        result = analyze_voice(
            client=mock_client,
            model="test-model",
            system_prompt="system",
            user_message="analyze",
            audio_path="/fake/audio.mp3",
        )

        # Assert
        assert "voice_properties" in result

    @patch(
        "script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.audio_analyzer.encode_audio_base64",
        return_value="base64data",
    )
    @patch("time.sleep")
    def test_retries_on_rate_limit(self, mock_sleep, _mock_encode):
        # Arrange
        mock_client = MagicMock()
        # First call raises rate limit, second succeeds
        mock_client.chat.completions.create.side_effect = [
            Exception("429 rate limit exceeded"),
            _mock_completion_response(_valid_json_response()),
        ]

        # Act
        result = analyze_voice(
            client=mock_client,
            model="test-model",
            system_prompt="system",
            user_message="analyze",
            audio_path="/fake/audio.mp3",
        )

        # Assert
        assert "voice_properties" in result
        mock_sleep.assert_called()
        assert mock_sleep.call_args[0][0] == INITIAL_BACKOFF

    @patch(
        "script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.audio_analyzer.encode_audio_base64",
        return_value="base64data",
    )
    @patch("time.sleep")
    def test_retries_on_json_error(self, mock_sleep, _mock_encode):
        # Arrange — the retry logic checks for "json" in the error string
        # Use an exception whose message contains "json" to trigger the retry path
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = [
            Exception("invalid json response from model"),
            _mock_completion_response(_valid_json_response()),
        ]

        # Act
        result = analyze_voice(
            client=mock_client,
            model="test-model",
            system_prompt="system",
            user_message="analyze",
            audio_path="/fake/audio.mp3",
        )

        # Assert
        assert "voice_properties" in result
        mock_sleep.assert_called()

    @patch(
        "script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.audio_analyzer.encode_audio_base64",
        return_value="base64data",
    )
    @patch("time.sleep")
    def test_disables_json_format_on_unsupported(self, _mock_sleep, _mock_encode):
        # Arrange
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = [
            Exception("response_format is not supported"),
            _mock_completion_response(_valid_json_response()),
        ]

        # Act
        result = analyze_voice(
            client=mock_client,
            model="test-model",
            system_prompt="system",
            user_message="analyze",
            audio_path="/fake/audio.mp3",
        )

        # Assert
        assert "voice_properties" in result
        # Second call should not have response_format
        second_call_kwargs = mock_client.chat.completions.create.call_args_list[1][1]
        assert "response_format" not in second_call_kwargs

    @patch(
        "script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.audio_analyzer.encode_audio_base64",
        return_value="base64data",
    )
    @patch("time.sleep")
    def test_max_retries_exceeded(self, _mock_sleep, _mock_encode):
        # Arrange
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception(
            "429 rate limit exceeded"
        )

        # Act & Assert
        with pytest.raises((RuntimeError, Exception)):
            analyze_voice(
                client=mock_client,
                model="test-model",
                system_prompt="system",
                user_message="analyze",
                audio_path="/fake/audio.mp3",
            )


class TestAnalyzeVoiceBatch:
    """Tests for analyze_voice_batch()."""

    @patch(
        "script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.prompt_builder.build_user_message",
        return_value="msg",
    )
    @patch(
        "script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.audio_analyzer.analyze_voice"
    )
    @patch(
        "script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.audio_analyzer.get_openrouter_client"
    )
    def test_processes_all_voices(self, _mock_client, mock_analyze, _mock_msg):
        # Arrange
        mock_analyze.return_value = {"voice_properties": {"age": 0.5}}
        voices = {"v1": {}, "v2": {}}
        audio_paths = {"v1": "/path/v1.mp3", "v2": "/path/v2.mp3"}

        # Act
        result = analyze_voice_batch(
            model="test-model",
            system_prompt="system",
            voices=voices,
            audio_paths=audio_paths,
            iterations=2,
        )

        # Assert
        assert set(result.keys()) == {"v1", "v2"}
        assert len(result["v1"]) == 2
        assert len(result["v2"]) == 2

    @patch(
        "script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.prompt_builder.build_user_message",
        return_value="msg",
    )
    @patch(
        "script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.audio_analyzer.analyze_voice"
    )
    @patch(
        "script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.audio_analyzer.get_openrouter_client"
    )
    def test_handles_per_voice_errors(self, _mock_client, mock_analyze, _mock_msg):
        # Arrange
        mock_analyze.side_effect = Exception("analysis failed")
        voices = {"v1": {}}
        audio_paths = {"v1": "/path/v1.mp3"}

        # Act
        result = analyze_voice_batch(
            model="test-model",
            system_prompt="system",
            voices=voices,
            audio_paths=audio_paths,
            iterations=1,
        )

        # Assert
        assert "v1" in result
        assert len(result["v1"]) == 1
        assert "error" in result["v1"][0]

    @patch(
        "script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.prompt_builder.build_user_message",
        return_value="msg",
    )
    @patch(
        "script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.audio_analyzer.analyze_voice"
    )
    @patch(
        "script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.audio_analyzer.get_openrouter_client"
    )
    def test_saves_raw_results(self, _mock_client, mock_analyze, _mock_msg):
        # Arrange
        mock_analyze.return_value = {"voice_properties": {"age": 0.5}}
        voices = {"v1": {}}
        audio_paths = {"v1": "/path/v1.mp3"}
        raw_dir = MagicMock(spec=Path)
        result_path_mock = MagicMock(spec=Path)
        result_path_mock.parent = MagicMock()
        raw_dir.__truediv__ = MagicMock(return_value=result_path_mock)

        with patch("builtins.open", mock_open()):
            # Act
            result = analyze_voice_batch(
                model="test-model",
                system_prompt="system",
                voices=voices,
                audio_paths=audio_paths,
                iterations=1,
                raw_results_dir=raw_dir,
            )

        # Assert
        assert "v1" in result
        result_path_mock.parent.mkdir.assert_called()
