import os
from collections import OrderedDict
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from script_to_speech.tts_providers.elevenlabs.voice_registry_manager import (
    ElevenLabsVoiceRegistryManager,
)


class TestElevenLabsVoiceRegistryManager:
    """Tests for the ElevenLabsVoiceRegistryManager class."""

    def test_init(self):
        """Test initialization of the registry manager."""
        manager = ElevenLabsVoiceRegistryManager("fake_api_key")
        assert manager.api_key == "fake_api_key"
        assert manager.client is not None
        assert isinstance(manager.voice_registry, dict)
        assert isinstance(manager.voice_usage_order, OrderedDict)
        assert manager.is_initialized is False

    @patch("script_to_speech.tts_providers.elevenlabs.voice_registry_manager.ElevenLabs")
    def test_initialize_voice_registry_empty(self, mock_elevenlabs):
        """Test _initialize_voice_registry with empty response."""
        # Setup mock
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.voices = []
        mock_client.voices.get_all.return_value = mock_response

        mock_elevenlabs.return_value = mock_client

        # Create manager with mock
        manager = ElevenLabsVoiceRegistryManager("fake_api_key")

        # Initialize registry
        manager._initialize_voice_registry()

        # Check registry was initialized correctly
        assert manager.voice_registry == {}
        assert len(manager.voice_usage_order) == 0
        assert manager.is_initialized is True

    @patch("script_to_speech.tts_providers.elevenlabs.voice_registry_manager.ElevenLabs")
    def test_initialize_voice_registry_premade_voices(self, mock_elevenlabs):
        """Test _initialize_voice_registry with premade voices."""
        # Setup mock
        mock_client = MagicMock()
        mock_response = MagicMock()

        # Create mock voices
        mock_voice1 = Mock()
        mock_voice1.voice_id = "voice1"
        mock_voice1.category = "premade"
        # Ensure sharing is None for premade voices
        mock_voice1.sharing = None

        mock_voice2 = Mock()
        mock_voice2.voice_id = "voice2"
        mock_voice2.category = "premade"
        mock_voice2.sharing = None

        mock_response.voices = [mock_voice1, mock_voice2]
        mock_client.voices.get_all.return_value = mock_response

        mock_elevenlabs.return_value = mock_client

        # Create manager with mock
        manager = ElevenLabsVoiceRegistryManager("fake_api_key")
        manager.client = mock_client

        # Initialize registry
        manager._initialize_voice_registry()

        # Check registry was initialized correctly with two premade voices
        assert len(manager.voice_registry) == 2
        # For premade voices, the voice_id is both the registry key and the registry value
        assert manager.voice_registry["voice1"] == ("voice1", "premade")
        assert manager.voice_registry["voice2"] == ("voice2", "premade")

        # Premade voices should not be in LRU order
        assert len(manager.voice_usage_order) == 0
        assert manager.is_initialized is True

    @patch("script_to_speech.tts_providers.elevenlabs.voice_registry_manager.ElevenLabs")
    def test_initialize_voice_registry_shared_voices(self, mock_elevenlabs):
        """Test _initialize_voice_registry with shared voices."""
        # Setup mock
        mock_client = MagicMock()
        mock_response = MagicMock()

        # Create mock voices with sharing attribute
        mock_voice1 = Mock()
        mock_voice1.voice_id = "registry_id1"
        mock_voice1.category = "cloned"
        mock_voice1.sharing = Mock()
        mock_voice1.sharing.original_voice_id = "public_id1"

        mock_voice2 = Mock()
        mock_voice2.voice_id = "registry_id2"
        mock_voice2.category = "cloned"
        mock_voice2.sharing = Mock()
        mock_voice2.sharing.original_voice_id = "public_id2"

        mock_response.voices = [mock_voice1, mock_voice2]
        mock_client.voices.get_all.return_value = mock_response

        mock_elevenlabs.return_value = mock_client

        # Create manager with mock
        manager = ElevenLabsVoiceRegistryManager("fake_api_key")

        # Initialize registry
        manager._initialize_voice_registry()

        # Check registry was initialized correctly with public IDs mapping to registry IDs
        assert len(manager.voice_registry) == 2
        assert manager.voice_registry["public_id1"] == ("registry_id1", "cloned")
        assert manager.voice_registry["public_id2"] == ("registry_id2", "cloned")

        # Non-premade voices should be in LRU order
        assert len(manager.voice_usage_order) == 2
        # Order may vary based on implementation, just check that both are present
        assert set(manager.voice_usage_order.keys()) == {"public_id1", "public_id2"}
        assert manager.is_initialized is True

    @patch("script_to_speech.tts_providers.elevenlabs.voice_registry_manager.ElevenLabs")
    def test_initialize_voice_registry_mixed_voices(self, mock_elevenlabs):
        """Test _initialize_voice_registry with mixed voice types."""
        # Setup mock
        mock_client = MagicMock()
        mock_response = MagicMock()

        # Create mock voices with mix of premade and shared
        mock_voice1 = Mock()
        mock_voice1.voice_id = "premade_id"
        mock_voice1.category = "premade"
        # Explicitly set sharing to None for premade voices
        mock_voice1.sharing = None

        mock_voice2 = Mock()
        mock_voice2.voice_id = "registry_id"
        mock_voice2.category = "cloned"
        mock_voice2.sharing = Mock()
        mock_voice2.sharing.original_voice_id = "public_id"

        mock_response.voices = [mock_voice1, mock_voice2]
        mock_client.voices.get_all.return_value = mock_response

        mock_elevenlabs.return_value = mock_client

        # Create manager with mock
        manager = ElevenLabsVoiceRegistryManager("fake_api_key")

        # Initialize registry
        manager._initialize_voice_registry()

        # Check registry was initialized correctly
        assert len(manager.voice_registry) == 2
        assert manager.voice_registry["premade_id"] == ("premade_id", "premade")
        assert manager.voice_registry["public_id"] == ("registry_id", "cloned")

        # Only non-premade voices should be in LRU order
        assert len(manager.voice_usage_order) == 1
        assert list(manager.voice_usage_order.keys()) == ["public_id"]
        assert manager.is_initialized is True

    @patch("script_to_speech.tts_providers.elevenlabs.voice_registry_manager.ElevenLabs")
    def test_find_voice_owner_found(self, mock_elevenlabs):
        """Test _find_voice_owner when owner is found."""
        # Setup mock
        mock_client = MagicMock()
        mock_response = MagicMock()

        # Create mock voice
        mock_voice = Mock()
        mock_voice.voice_id = "public_id"
        mock_voice.public_owner_id = "owner_id"

        mock_response.voices = [mock_voice]
        mock_client.voices.get_shared.return_value = mock_response

        mock_elevenlabs.return_value = mock_client

        # Create manager with mock
        manager = ElevenLabsVoiceRegistryManager("fake_api_key")
        manager.client = mock_client

        # Find voice owner
        owner_id = manager._find_voice_owner("public_id")

        # Check owner was found
        assert owner_id == "owner_id"
        mock_client.voices.get_shared.assert_called_once_with(search="public_id")

    @patch("script_to_speech.tts_providers.elevenlabs.voice_registry_manager.ElevenLabs")
    def test_find_voice_owner_not_found(self, mock_elevenlabs):
        """Test _find_voice_owner when owner is not found."""
        # Setup mock
        mock_client = MagicMock()
        mock_response = MagicMock()

        # Create mock voice with different ID
        mock_voice = Mock()
        mock_voice.voice_id = "different_id"
        mock_voice.public_owner_id = "owner_id"

        mock_response.voices = [mock_voice]
        mock_client.voices.get_shared.return_value = mock_response

        mock_elevenlabs.return_value = mock_client

        # Create manager with mock
        manager = ElevenLabsVoiceRegistryManager("fake_api_key")
        manager.client = mock_client

        # Find voice owner
        owner_id = manager._find_voice_owner("public_id")

        # Check owner was not found
        assert owner_id is None
        mock_client.voices.get_shared.assert_called_once_with(search="public_id")

    @patch("script_to_speech.tts_providers.elevenlabs.voice_registry_manager.requests.post")
    def test_add_voice_to_registry_success(self, mock_post):
        """Test _add_voice_to_registry successful addition."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.ok = True
        mock_post.return_value = mock_response

        # Create manager with mocked _initialize_voice_registry
        manager = ElevenLabsVoiceRegistryManager("fake_api_key")
        manager._initialize_voice_registry = MagicMock()

        # Add voice to registry
        manager._add_voice_to_registry("public_id", "owner_id")

        # Check request was made correctly
        expected_url = f"https://api.elevenlabs.io/v1/voices/add/owner_id/public_id"
        expected_headers = {
            "Content-Type": "application/json",
            "xi-api-key": "fake_api_key",
        }
        expected_payload = {"new_name": "public_id"}

        mock_post.assert_called_once_with(
            expected_url, json=expected_payload, headers=expected_headers
        )

        # Check registry was reinitialized
        manager._initialize_voice_registry.assert_called_once()

    @patch("script_to_speech.tts_providers.elevenlabs.voice_registry_manager.requests.post")
    def test_add_voice_to_registry_failure(self, mock_post):
        """Test _add_voice_to_registry API failure."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.text = "API error"
        mock_post.return_value = mock_response

        # Create manager
        manager = ElevenLabsVoiceRegistryManager("fake_api_key")

        # Adding voice should raise RuntimeError
        with pytest.raises(RuntimeError, match="Failed to add voice to registry"):
            manager._add_voice_to_registry("public_id", "owner_id")

    @patch("script_to_speech.tts_providers.elevenlabs.voice_registry_manager.requests.delete")
    def test_remove_voice_from_registry_success(self, mock_delete):
        """Test _remove_voice_from_registry successful removal."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.ok = True
        mock_delete.return_value = mock_response

        # Create manager with mocked _initialize_voice_registry
        manager = ElevenLabsVoiceRegistryManager("fake_api_key")
        manager._initialize_voice_registry = MagicMock()

        # Remove voice from registry
        manager._remove_voice_from_registry("registry_id")

        # Check request was made correctly
        expected_url = f"https://api.elevenlabs.io/v1/voices/registry_id"
        expected_headers = {"xi-api-key": "fake_api_key"}

        mock_delete.assert_called_once_with(expected_url, headers=expected_headers)

        # Check registry was reinitialized
        manager._initialize_voice_registry.assert_called_once()

    @patch("script_to_speech.tts_providers.elevenlabs.voice_registry_manager.requests.delete")
    def test_remove_voice_from_registry_failure(self, mock_delete):
        """Test _remove_voice_from_registry API failure."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.text = "API error"
        mock_delete.return_value = mock_response

        # Create manager
        manager = ElevenLabsVoiceRegistryManager("fake_api_key")

        # Removing voice should raise RuntimeError
        with pytest.raises(RuntimeError, match="Failed to remove voice from registry"):
            manager._remove_voice_from_registry("registry_id")

    def test_make_room_in_registry_lru(self):
        """Test _make_room_in_registry using LRU policy."""
        # Create manager
        manager = ElevenLabsVoiceRegistryManager("fake_api_key")
        manager._remove_voice_from_registry = MagicMock()

        # Set up voice registry with LRU order
        manager.voice_registry = {
            "public_id1": ("registry_id1", "cloned"),
            "public_id2": ("registry_id2", "cloned"),
            "public_id3": ("registry_id3", "cloned"),
        }

        # Create OrderedDict with LRU order (earliest first)
        manager.voice_usage_order = OrderedDict()
        manager.voice_usage_order["public_id1"] = None
        manager.voice_usage_order["public_id2"] = None
        manager.voice_usage_order["public_id3"] = None

        # Make room in registry
        manager._make_room_in_registry()

        # Should remove the least recently used voice (public_id1)
        manager._remove_voice_from_registry.assert_called_once_with("registry_id1")

    def test_make_room_in_registry_no_lru(self):
        """Test _make_room_in_registry with no LRU history."""
        # Create manager
        manager = ElevenLabsVoiceRegistryManager("fake_api_key")
        manager._remove_voice_from_registry = MagicMock()

        # Set up voice registry without LRU order
        manager.voice_registry = {
            "public_id1": ("registry_id1", "cloned"),
            "premade_id": ("premade_id", "premade"),
        }

        # Empty LRU order
        manager.voice_usage_order = OrderedDict()

        # Make room in registry
        manager._make_room_in_registry()

        # Should remove a non-premade voice
        manager._remove_voice_from_registry.assert_called_once_with("registry_id1")

    def test_make_room_in_registry_no_removable_voices(self):
        """Test _make_room_in_registry with no removable voices."""
        # Create manager
        manager = ElevenLabsVoiceRegistryManager("fake_api_key")
        manager._remove_voice_from_registry = MagicMock()

        # Set up voice registry with only premade voices
        manager.voice_registry = {
            "premade_id1": ("premade_id1", "premade"),
            "premade_id2": ("premade_id2", "premade"),
        }

        # Empty LRU order
        manager.voice_usage_order = OrderedDict()

        # Make room in registry should raise an error
        with pytest.raises(RuntimeError, match="No removable voices found in registry"):
            manager._make_room_in_registry()

        # Should not attempt to remove any voices
        manager._remove_voice_from_registry.assert_not_called()

    def test_get_library_voice_id_already_in_registry(self):
        """Test get_library_voice_id when voice is already in registry."""
        # Create manager
        manager = ElevenLabsVoiceRegistryManager("fake_api_key")

        # Setup voice registry with the voice already present
        manager.voice_registry = {
            "public_id": ("registry_id", "cloned"),
            "premade_id": ("premade_id", "premade"),
        }

        # Setup LRU tracking
        manager.voice_usage_order = OrderedDict()
        manager.voice_usage_order["public_id"] = None

        manager.is_initialized = True

        # Get library voice ID
        result = manager.get_library_voice_id("public_id")

        # Should return the registry ID and update LRU order
        assert result == "registry_id"
        assert (
            list(manager.voice_usage_order.keys())[0] == "public_id"
        )  # Should be the most recently used

    def test_get_library_voice_id_premade_voice(self):
        """Test get_library_voice_id with a premade voice."""
        # Create manager
        manager = ElevenLabsVoiceRegistryManager("fake_api_key")

        # Setup voice registry with a premade voice
        manager.voice_registry = {
            "premade_id": ("premade_id", "premade"),
        }

        # Empty LRU order for premade voices
        manager.voice_usage_order = OrderedDict()

        manager.is_initialized = True

        # Get library voice ID
        result = manager.get_library_voice_id("premade_id")

        # Should return the same ID for premade voices (no registry mapping needed)
        assert result == "premade_id"
        # Premade voices should not be in LRU tracking
        assert len(manager.voice_usage_order) == 0

    @patch("script_to_speech.tts_providers.elevenlabs.voice_registry_manager.ElevenLabs")
    def test_get_library_voice_id_not_initialized(self, mock_elevenlabs):
        """Test get_library_voice_id when registry is not initialized."""
        # Setup mock for initialization
        mock_client = MagicMock()
        mock_response = MagicMock()

        # Create mock voice with the same ID we'll request
        mock_voice = Mock()
        mock_voice.voice_id = "public_id"
        mock_voice.category = "premade"
        # No sharing attribute for premade voices
        mock_voice.sharing = None

        mock_response.voices = [mock_voice]
        mock_client.voices.get_all.return_value = mock_response

        mock_elevenlabs.return_value = mock_client

        # Create manager with mocked find_voice_owner
        manager = ElevenLabsVoiceRegistryManager("fake_api_key")
        manager.client = mock_client
        manager._find_voice_owner = MagicMock(return_value="owner_id")

        # Voice registry not initialized
        manager.is_initialized = False

        # Get library voice ID should initialize the registry first
        result = manager.get_library_voice_id("public_id")

        # Should initialize registry and return voice ID
        assert result == "public_id"
        assert manager.is_initialized is True
        mock_client.voices.get_all.assert_called_once()

    @patch("script_to_speech.tts_providers.elevenlabs.voice_registry_manager.ElevenLabs")
    def test_get_library_voice_id_add_new_voice(self, mock_elevenlabs):
        """Test get_library_voice_id when adding a new voice to registry."""
        # Create manager with mocked methods
        manager = ElevenLabsVoiceRegistryManager("fake_api_key")
        manager.client = MagicMock()
        manager._find_voice_owner = MagicMock(return_value="owner_id")
        manager._add_voice_to_registry = MagicMock()

        # Empty registry initially
        manager.voice_registry = {}
        manager.voice_usage_order = OrderedDict()
        manager.is_initialized = True

        # After adding voice, update registry
        manager._add_voice_to_registry.side_effect = lambda *args: setattr(
            manager, "voice_registry", {"public_id": ("registry_id", "cloned")}
        )

        # Get library voice ID for non-existent voice
        result = manager.get_library_voice_id("public_id")

        # Should find owner, add voice to registry, and return registry ID
        manager._find_voice_owner.assert_called_once_with("public_id")
        manager._add_voice_to_registry.assert_called_once_with("public_id", "owner_id")
        assert result == "registry_id"

    def test_get_library_voice_id_make_room_first(self):
        """Test get_library_voice_id when registry is full and needs space."""
        # Create manager with mocked methods
        manager = ElevenLabsVoiceRegistryManager("fake_api_key")
        manager._find_voice_owner = MagicMock(return_value="owner_id")
        manager._add_voice_to_registry = MagicMock()
        manager._make_room_in_registry = MagicMock()

        # Setup registry with 30 non-premade voices (full)
        manager.voice_registry = {}
        for i in range(30):
            manager.voice_registry[f"public_id{i}"] = (f"registry_id{i}", "cloned")

        manager.voice_usage_order = OrderedDict()
        for i in range(30):
            manager.voice_usage_order[f"public_id{i}"] = None

        manager.is_initialized = True

        # After adding voice, update registry
        manager._add_voice_to_registry.side_effect = lambda *args: setattr(
            manager,
            "voice_registry",
            {**manager.voice_registry, "new_public_id": ("new_registry_id", "cloned")},
        )

        # Get library voice ID for non-existent voice
        result = manager.get_library_voice_id("new_public_id")

        # Should make room, find owner, add voice to registry, and return registry ID
        manager._make_room_in_registry.assert_called_once()
        manager._find_voice_owner.assert_called_once_with("new_public_id")
        manager._add_voice_to_registry.assert_called_once_with(
            "new_public_id", "owner_id"
        )
        assert result == "new_registry_id"

    def test_get_library_voice_id_owner_not_found(self):
        """Test get_library_voice_id when voice owner cannot be found."""
        # Create manager with mocked methods
        manager = ElevenLabsVoiceRegistryManager("fake_api_key")
        manager._find_voice_owner = MagicMock(return_value=None)

        # Empty registry
        manager.voice_registry = {}
        manager.voice_usage_order = OrderedDict()
        manager.is_initialized = True

        # Get library voice ID should raise RuntimeError
        with pytest.raises(RuntimeError, match="Could not find owner for voice"):
            manager.get_library_voice_id("public_id")

        # Should attempt to find owner
        manager._find_voice_owner.assert_called_once_with("public_id")

    def test_lru_behavior_with_multiple_accesses(self):
        """Test LRU behavior when accessing multiple voices in different order."""
        # Create manager
        manager = ElevenLabsVoiceRegistryManager("fake_api_key")

        # Setup registry with 3 non-premade voices
        manager.voice_registry = {
            "public_id1": ("registry_id1", "cloned"),
            "public_id2": ("registry_id2", "cloned"),
            "public_id3": ("registry_id3", "cloned"),
        }

        # Initial LRU order: 1, 2, 3
        manager.voice_usage_order = OrderedDict()
        manager.voice_usage_order["public_id1"] = None
        manager.voice_usage_order["public_id2"] = None
        manager.voice_usage_order["public_id3"] = None

        manager.is_initialized = True

        # Access voices in order: 2, 3, 1, 3
        manager.get_library_voice_id("public_id2")
        manager.get_library_voice_id("public_id3")
        manager.get_library_voice_id("public_id1")
        manager.get_library_voice_id("public_id3")

        # Final LRU order should be: 2, 1, 3 (from least to most recently used)
        expected_order = ["public_id2", "public_id1", "public_id3"]
        assert list(manager.voice_usage_order.keys()) == expected_order
