"""Tests for TTS provider manager voice library integration."""

from unittest.mock import MagicMock, patch

import pytest

from script_to_speech.tts_providers.base.exceptions import VoiceNotFoundError
from script_to_speech.tts_providers.tts_provider_manager import TTSProviderManager


class TestTTSProviderManagerVoiceLibrary:
    """Tests for voice library integration in TTSProviderManager."""

    def test_init_creates_voice_library(self):
        """Test TTSProviderManager initialization creates VoiceLibrary instance."""
        # Arrange
        config_data = {"default": {"provider": "dummy_stateless"}}

        # Act
        with patch(
            "script_to_speech.tts_providers.tts_provider_manager.VoiceLibrary"
        ) as mock_voice_library:
            manager = TTSProviderManager(config_data=config_data)

            # Assert
            mock_voice_library.assert_called_once()
            assert hasattr(manager, "_voice_library")

    def test_load_config_with_sts_id_expansion(self):
        """Test _load_config expands sts_id in speaker configuration."""
        # Arrange
        config_data = {
            "test_speaker": {
                "provider": "dummy_stateless",
                "sts_id": "test_voice_id",
                "custom_override": "override_value",
            }
        }

        expanded_config = {
            "provider": "dummy_stateless",
            "voice": "expanded_voice",
            "model": "expanded_model",
        }

        mock_voice_library = MagicMock()
        mock_voice_library.expand_config.return_value = expanded_config

        # Act
        with patch(
            "script_to_speech.tts_providers.tts_provider_manager.VoiceLibrary",
            return_value=mock_voice_library,
        ):
            manager = TTSProviderManager(config_data=config_data)
            manager._ensure_initialized()

            # Assert
            mock_voice_library.expand_config.assert_called_once_with(
                "dummy_stateless", "test_voice_id"
            )

            # Check that the final config has expanded values with user overrides
            final_config = manager._speaker_configs_map["test_speaker"]
            assert final_config["provider"] == "dummy_stateless"
            assert final_config["voice"] == "expanded_voice"
            assert final_config["model"] == "expanded_model"
            assert final_config["custom_override"] == "override_value"
            assert "sts_id" not in final_config  # sts_id should be removed

    def test_load_config_without_sts_id(self):
        """Test _load_config works normally without sts_id."""
        # Arrange
        config_data = {
            "test_speaker": {
                "provider": "dummy_stateless",
                "voice": "direct_voice",
                "model": "direct_model",
            }
        }

        mock_voice_library = MagicMock()

        # Act
        with patch(
            "script_to_speech.tts_providers.tts_provider_manager.VoiceLibrary",
            return_value=mock_voice_library,
        ):
            manager = TTSProviderManager(config_data=config_data)
            manager._ensure_initialized()

            # Assert
            mock_voice_library.expand_config.assert_not_called()

            # Check that the config remains unchanged
            final_config = manager._speaker_configs_map["test_speaker"]
            assert final_config["provider"] == "dummy_stateless"
            assert final_config["voice"] == "direct_voice"
            assert final_config["model"] == "direct_model"

    def test_load_config_sts_id_expansion_error(self):
        """Test _load_config handles sts_id expansion errors gracefully."""
        # Arrange
        config_data = {
            "test_speaker": {
                "provider": "dummy_stateless",
                "sts_id": "nonexistent_voice",
            }
        }

        mock_voice_library = MagicMock()
        mock_voice_library.expand_config.side_effect = VoiceNotFoundError(
            "Voice not found"
        )

        # Act & Assert
        with patch(
            "script_to_speech.tts_providers.tts_provider_manager.VoiceLibrary",
            return_value=mock_voice_library,
        ):
            manager = TTSProviderManager(config_data=config_data)

            # The error should be raised during initialization
            with pytest.raises(VoiceNotFoundError, match="Voice not found"):
                manager._ensure_initialized()

    def test_load_config_sts_id_with_user_overrides(self):
        """Test _load_config merges expanded config with user overrides correctly."""
        # Arrange
        config_data = {
            "test_speaker": {
                "provider": "dummy_stateless",
                "sts_id": "test_voice_id",
                "voice": "user_override_voice",  # This should override expanded value
                "custom_param": "user_value",  # This should be added
            }
        }

        expanded_config = {
            "provider": "dummy_stateless",
            "voice": "expanded_voice",
            "model": "expanded_model",
            "speed": 1.0,
        }

        mock_voice_library = MagicMock()
        mock_voice_library.expand_config.return_value = expanded_config

        # Act
        with patch(
            "script_to_speech.tts_providers.tts_provider_manager.VoiceLibrary",
            return_value=mock_voice_library,
        ):
            manager = TTSProviderManager(config_data=config_data)
            manager._ensure_initialized()

            # Assert
            final_config = manager._speaker_configs_map["test_speaker"]
            assert final_config["provider"] == "dummy_stateless"
            assert (
                final_config["voice"] == "user_override_voice"
            )  # User override should win
            assert (
                final_config["model"] == "expanded_model"
            )  # Expanded value should be kept
            assert final_config["speed"] == 1.0  # Expanded value should be kept
            assert (
                final_config["custom_param"] == "user_value"
            )  # User addition should be kept
            assert "sts_id" not in final_config  # sts_id should be removed

    def test_load_config_multiple_speakers_with_sts_id(self):
        """Test _load_config handles multiple speakers with sts_id correctly."""
        # Arrange
        config_data = {
            "speaker1": {"provider": "dummy_stateless", "sts_id": "voice1"},
            "speaker2": {
                "provider": "dummy_stateless",
                "voice": "direct_voice",  # No sts_id
            },
            "speaker3": {"provider": "dummy_stateless", "sts_id": "voice2"},
        }

        def mock_expand_config(provider, sts_id):
            if sts_id == "voice1":
                return {"provider": provider, "voice": "expanded_voice1"}
            elif sts_id == "voice2":
                return {"provider": provider, "voice": "expanded_voice2"}
            else:
                raise VoiceNotFoundError(f"Unknown voice: {sts_id}")

        mock_voice_library = MagicMock()
        mock_voice_library.expand_config.side_effect = mock_expand_config

        # Act
        with patch(
            "script_to_speech.tts_providers.tts_provider_manager.VoiceLibrary",
            return_value=mock_voice_library,
        ):
            manager = TTSProviderManager(config_data=config_data)
            manager._ensure_initialized()

            # Assert
            assert mock_voice_library.expand_config.call_count == 2

            # Check speaker1 (with sts_id)
            config1 = manager._speaker_configs_map["speaker1"]
            assert config1["voice"] == "expanded_voice1"
            assert "sts_id" not in config1

            # Check speaker2 (without sts_id)
            config2 = manager._speaker_configs_map["speaker2"]
            assert config2["voice"] == "direct_voice"

            # Check speaker3 (with sts_id)
            config3 = manager._speaker_configs_map["speaker3"]
            assert config3["voice"] == "expanded_voice2"
            assert "sts_id" not in config3

    def test_load_config_sts_id_modifies_speaker_config_in_place(self):
        """Test _load_config modifies speaker_config in place when using sts_id."""
        # Arrange
        config_data = {
            "test_speaker": {
                "provider": "dummy_stateless",
                "sts_id": "test_voice_id",
                "custom_param": "value",
            }
        }

        expanded_config = {"provider": "dummy_stateless", "voice": "expanded_voice"}

        mock_voice_library = MagicMock()
        mock_voice_library.expand_config.return_value = expanded_config

        # Act
        with patch(
            "script_to_speech.tts_providers.tts_provider_manager.VoiceLibrary",
            return_value=mock_voice_library,
        ):
            manager = TTSProviderManager(config_data=config_data)
            manager._ensure_initialized()

            # Assert
            # The implementation modifies the config in place, so sts_id is removed
            assert "sts_id" not in config_data["test_speaker"]
            assert config_data["test_speaker"]["voice"] == "expanded_voice"
            assert config_data["test_speaker"]["custom_param"] == "value"

            # Manager's internal config should match
            final_config = manager._speaker_configs_map["test_speaker"]
            assert "sts_id" not in final_config
            assert final_config["voice"] == "expanded_voice"
            assert final_config["custom_param"] == "value"
