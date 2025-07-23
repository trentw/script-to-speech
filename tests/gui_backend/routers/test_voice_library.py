"""Tests for voice library router endpoints."""

from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from script_to_speech.gui_backend.models import (
    VoiceDescription,
    VoiceDetails,
    VoiceEntry,
    VoiceProperties,
    VoiceTags,
)
from script_to_speech.gui_backend.services.voice_library_service import (
    voice_library_service,
)


class TestVoiceLibraryProviders:
    """Tests for GET /voice-library/providers endpoint."""

    @pytest.fixture
    def mock_voice_library_service(self):
        """Mock the voice library service."""
        with (
            patch.object(
                voice_library_service, "get_available_providers"
            ) as mock_get_providers,
            patch.object(
                voice_library_service, "get_provider_voices"
            ) as mock_get_voices,
            patch.object(
                voice_library_service, "get_voice_details"
            ) as mock_get_details,
            patch.object(voice_library_service, "search_voices") as mock_search,
            patch.object(voice_library_service, "get_voice_stats") as mock_get_stats,
            patch.object(voice_library_service, "expand_sts_id") as mock_expand,
        ):
            # Create a mock object with all the methods
            mock = type(
                "MockService",
                (),
                {
                    "get_available_providers": mock_get_providers,
                    "get_provider_voices": mock_get_voices,
                    "get_voice_details": mock_get_details,
                    "search_voices": mock_search,
                    "get_voice_stats": mock_get_stats,
                    "expand_sts_id": mock_expand,
                },
            )()
            yield mock

    def test_get_voice_library_providers_success(
        self, client: TestClient, mock_voice_library_service
    ):
        """Test successful retrieval of voice library providers."""
        # Arrange
        expected_providers = ["openai", "elevenlabs", "cartesia"]
        mock_voice_library_service.get_available_providers.return_value = (
            expected_providers
        )

        # Act
        response = client.get("/api/voice-library/providers")

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert response_data == expected_providers
        mock_voice_library_service.get_available_providers.assert_called_once()

    def test_get_voice_library_providers_empty(
        self, client: TestClient, mock_voice_library_service
    ):
        """Test providers endpoint when no providers are available."""
        # Arrange
        mock_voice_library_service.get_available_providers.return_value = []

        # Act
        response = client.get("/api/voice-library/providers")

        # Assert
        assert response.status_code == 200
        assert response.json() == []

    def test_get_voice_library_providers_service_error(
        self, client: TestClient, mock_voice_library_service
    ):
        """Test handling of service errors in providers endpoint."""
        # Arrange
        mock_voice_library_service.get_available_providers.side_effect = Exception(
            "Service error"
        )

        # Act
        response = client.get("/api/voice-library/providers")

        # Assert
        assert response.status_code == 500
        assert "Failed to get providers" in response.json()["detail"]


class TestProviderVoices:
    """Tests for GET /voice-library/{provider} endpoint."""

    @pytest.fixture
    def mock_voice_library_service(self):
        """Mock the voice library service."""
        with (
            patch.object(
                voice_library_service, "get_available_providers"
            ) as mock_get_providers,
            patch.object(
                voice_library_service, "get_provider_voices"
            ) as mock_get_voices,
            patch.object(
                voice_library_service, "get_voice_details"
            ) as mock_get_details,
            patch.object(voice_library_service, "search_voices") as mock_search,
            patch.object(voice_library_service, "get_voice_stats") as mock_get_stats,
            patch.object(voice_library_service, "expand_sts_id") as mock_expand,
        ):
            # Create a mock object with all the methods
            mock = type(
                "MockService",
                (),
                {
                    "get_available_providers": mock_get_providers,
                    "get_provider_voices": mock_get_voices,
                    "get_voice_details": mock_get_details,
                    "search_voices": mock_search,
                    "get_voice_stats": mock_get_stats,
                    "expand_sts_id": mock_expand,
                },
            )()
            yield mock

    @pytest.fixture
    def sample_voice_entries(self) -> List[VoiceEntry]:
        """Create sample VoiceEntry objects for testing."""
        return [
            VoiceEntry(
                sts_id="alloy",
                provider="openai",
                config={"voice": "alloy", "model": "tts-1"},
                voice_properties=VoiceProperties(gender="neutral", age=0.5, energy=0.7),
                description=VoiceDescription(
                    provider_name="Alloy",
                    provider_description="A balanced, neutral voice",
                ),
                tags=VoiceTags(
                    custom_tags=["neutral", "clear"],
                    character_types=["narrator", "young adult"],
                ),
                preview_url="https://example.com/preview/alloy.mp3",
            ),
            VoiceEntry(
                sts_id="echo",
                provider="openai",
                config={"voice": "echo", "model": "tts-1"},
                voice_properties=VoiceProperties(gender="male", age=0.6, energy=0.8),
                description=VoiceDescription(
                    provider_name="Echo", provider_description="Clear male voice"
                ),
            ),
        ]

    def test_get_provider_voices_success(
        self, client: TestClient, mock_voice_library_service, sample_voice_entries
    ):
        """Test successful retrieval of voices for a provider."""
        # Arrange
        provider = "openai"
        mock_voice_library_service.get_provider_voices.return_value = (
            sample_voice_entries
        )
        mock_voice_library_service.get_available_providers.return_value = [
            "openai",
            "elevenlabs",
        ]

        # Act
        response = client.get(f"/api/voice-library/{provider}")

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data) == 2
        assert response_data[0]["sts_id"] == "alloy"
        assert response_data[0]["provider"] == "openai"
        assert response_data[0]["config"] == {"voice": "alloy", "model": "tts-1"}
        mock_voice_library_service.get_provider_voices.assert_called_once_with(provider)

    def test_get_provider_voices_empty_provider(
        self, client: TestClient, mock_voice_library_service
    ):
        """Test retrieval of voices for provider with no voices."""
        # Arrange
        provider = "openai"
        mock_voice_library_service.get_provider_voices.return_value = []
        mock_voice_library_service.get_available_providers.return_value = ["openai"]

        # Act
        response = client.get(f"/api/voice-library/{provider}")

        # Assert
        assert response.status_code == 200
        assert response.json() == []

    def test_get_provider_voices_nonexistent_provider(
        self, client: TestClient, mock_voice_library_service
    ):
        """Test retrieval of voices for non-existent provider."""
        # Arrange
        provider = "nonexistent"
        mock_voice_library_service.get_provider_voices.return_value = []
        mock_voice_library_service.get_available_providers.return_value = [
            "openai",
            "elevenlabs",
        ]

        # Act
        response = client.get(f"/api/voice-library/{provider}")

        # Assert
        assert response.status_code == 404
        assert f"Provider {provider} not found" in response.json()["detail"]

    def test_get_provider_voices_service_error(
        self, client: TestClient, mock_voice_library_service
    ):
        """Test handling of service errors when getting provider voices."""
        # Arrange
        provider = "openai"
        mock_voice_library_service.get_provider_voices.side_effect = Exception(
            "Service error"
        )

        # Act
        response = client.get(f"/api/voice-library/{provider}")

        # Assert
        assert response.status_code == 500
        assert "Failed to get voices" in response.json()["detail"]


class TestVoiceDetails:
    """Tests for GET /voice-library/{provider}/{sts_id} endpoint."""

    @pytest.fixture
    def mock_voice_library_service(self):
        """Mock the voice library service."""
        with (
            patch.object(
                voice_library_service, "get_available_providers"
            ) as mock_get_providers,
            patch.object(
                voice_library_service, "get_provider_voices"
            ) as mock_get_voices,
            patch.object(
                voice_library_service, "get_voice_details"
            ) as mock_get_details,
            patch.object(voice_library_service, "search_voices") as mock_search,
            patch.object(voice_library_service, "get_voice_stats") as mock_get_stats,
            patch.object(voice_library_service, "expand_sts_id") as mock_expand,
        ):
            # Create a mock object with all the methods
            mock = type(
                "MockService",
                (),
                {
                    "get_available_providers": mock_get_providers,
                    "get_provider_voices": mock_get_voices,
                    "get_voice_details": mock_get_details,
                    "search_voices": mock_search,
                    "get_voice_stats": mock_get_stats,
                    "expand_sts_id": mock_expand,
                },
            )()
            yield mock

    @pytest.fixture
    def sample_voice_details(self) -> VoiceDetails:
        """Create sample VoiceDetails object for testing."""
        return VoiceDetails(
            sts_id="alloy",
            provider="openai",
            config={"voice": "alloy", "model": "tts-1"},
            voice_properties=VoiceProperties(
                gender="neutral", age=0.5, energy=0.7, pitch=0.6, quality=0.9
            ),
            description=VoiceDescription(
                provider_name="Alloy",
                provider_description="A balanced, neutral voice suitable for various content",
                custom_description="Great for narration and general purpose use",
                perceived_age="young adult",
            ),
            tags=VoiceTags(
                custom_tags=["neutral", "clear", "versatile"],
                character_types=["narrator", "young adult", "professional"],
                provider_use_cases=["audiobooks", "podcasts", "presentations"],
            ),
            preview_url="https://example.com/preview/alloy.mp3",
            expanded_config={
                "voice": "alloy",
                "model": "tts-1",
                "speed": 1.0,
                "response_format": "mp3",
            },
        )

    def test_get_voice_details_success(
        self, client: TestClient, mock_voice_library_service, sample_voice_details
    ):
        """Test successful retrieval of voice details."""
        # Arrange
        provider = "openai"
        sts_id = "alloy"
        mock_voice_library_service.get_voice_details.return_value = sample_voice_details

        # Act
        response = client.get(f"/api/voice-library/{provider}/{sts_id}")

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["sts_id"] == "alloy"
        assert response_data["provider"] == "openai"
        assert response_data["config"]["voice"] == "alloy"
        assert response_data["expanded_config"]["speed"] == 1.0
        assert response_data["voice_properties"]["gender"] == "neutral"
        assert response_data["description"]["provider_name"] == "Alloy"
        assert "neutral" in response_data["tags"]["custom_tags"]
        mock_voice_library_service.get_voice_details.assert_called_once_with(
            provider, sts_id
        )

    def test_get_voice_details_not_found(
        self, client: TestClient, mock_voice_library_service
    ):
        """Test retrieval of non-existent voice details."""
        # Arrange
        provider = "openai"
        sts_id = "nonexistent"
        mock_voice_library_service.get_voice_details.return_value = None

        # Act
        response = client.get(f"/api/voice-library/{provider}/{sts_id}")

        # Assert
        assert response.status_code == 404
        assert f"Voice {provider}/{sts_id} not found" in response.json()["detail"]

    def test_get_voice_details_service_error(
        self, client: TestClient, mock_voice_library_service
    ):
        """Test handling of service errors when getting voice details."""
        # Arrange
        provider = "openai"
        sts_id = "alloy"
        mock_voice_library_service.get_voice_details.side_effect = Exception(
            "Service error"
        )

        # Act
        response = client.get(f"/api/voice-library/{provider}/{sts_id}")

        # Assert
        assert response.status_code == 500
        assert "Failed to get voice details" in response.json()["detail"]


class TestVoiceSearch:
    """Tests for GET /voice-library/search endpoint."""

    @pytest.fixture
    def mock_voice_library_service(self):
        """Mock the voice library service."""
        with (
            patch.object(
                voice_library_service, "get_available_providers"
            ) as mock_get_providers,
            patch.object(
                voice_library_service, "get_provider_voices"
            ) as mock_get_voices,
            patch.object(
                voice_library_service, "get_voice_details"
            ) as mock_get_details,
            patch.object(voice_library_service, "search_voices") as mock_search,
            patch.object(voice_library_service, "get_voice_stats") as mock_get_stats,
            patch.object(voice_library_service, "expand_sts_id") as mock_expand,
        ):
            # Create a mock object with all the methods
            mock = type(
                "MockService",
                (),
                {
                    "get_available_providers": mock_get_providers,
                    "get_provider_voices": mock_get_voices,
                    "get_voice_details": mock_get_details,
                    "search_voices": mock_search,
                    "get_voice_stats": mock_get_stats,
                    "expand_sts_id": mock_expand,
                },
            )()
            yield mock

    @pytest.fixture
    def sample_search_results(self) -> List[VoiceEntry]:
        """Create sample search result VoiceEntry objects."""
        return [
            VoiceEntry(
                sts_id="female_voice_1",
                provider="elevenlabs",
                config={"voice_id": "xyz123"},
                voice_properties=VoiceProperties(gender="female", age=0.4),
                description=VoiceDescription(provider_name="Rachel"),
                tags=VoiceTags(custom_tags=["female", "young"]),
            ),
            VoiceEntry(
                sts_id="female_voice_2",
                provider="openai",
                config={"voice": "shimmer"},
                voice_properties=VoiceProperties(gender="female", age=0.6),
                description=VoiceDescription(provider_name="Shimmer"),
                tags=VoiceTags(custom_tags=["female", "warm"]),
            ),
        ]

    def test_search_voices_by_query(
        self, client: TestClient, mock_voice_library_service, sample_search_results
    ):
        """Test searching voices by text query."""
        # Arrange
        query = "female"
        mock_voice_library_service.search_voices.return_value = sample_search_results

        # Act
        response = client.get(f"/api/voice-library/search?query={query}")

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data) == 2
        assert response_data[0]["sts_id"] == "female_voice_1"
        assert response_data[1]["sts_id"] == "female_voice_2"
        mock_voice_library_service.search_voices.assert_called_once_with(
            query=query, provider=None, gender=None, tags=None
        )

    def test_search_voices_by_provider(
        self, client: TestClient, mock_voice_library_service
    ):
        """Test searching voices by provider."""
        # Arrange
        provider = "openai"
        expected_results = [
            VoiceEntry(
                sts_id="alloy",
                provider="openai",
                config={"voice": "alloy"},
                voice_properties=VoiceProperties(gender="neutral"),
            )
        ]
        mock_voice_library_service.search_voices.return_value = expected_results

        # Act
        response = client.get(f"/api/voice-library/search?provider={provider}")

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data) == 1
        assert response_data[0]["provider"] == "openai"
        mock_voice_library_service.search_voices.assert_called_once_with(
            query=None, provider=provider, gender=None, tags=None
        )

    def test_search_voices_by_gender(
        self, client: TestClient, mock_voice_library_service, sample_search_results
    ):
        """Test searching voices by gender."""
        # Arrange
        gender = "female"
        mock_voice_library_service.search_voices.return_value = sample_search_results

        # Act
        response = client.get(f"/api/voice-library/search?gender={gender}")

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data) == 2
        mock_voice_library_service.search_voices.assert_called_once_with(
            query=None, provider=None, gender=gender, tags=None
        )

    def test_search_voices_by_tags(
        self, client: TestClient, mock_voice_library_service
    ):
        """Test searching voices by tags."""
        # Arrange
        tags = ["warm", "professional"]
        expected_results = [
            VoiceEntry(
                sts_id="professional_voice",
                provider="elevenlabs",
                config={"voice_id": "prof123"},
                tags=VoiceTags(custom_tags=["warm", "professional"]),
            )
        ]
        mock_voice_library_service.search_voices.return_value = expected_results

        # Act
        response = client.get(
            f"/api/voice-library/search?tags={tags[0]}&tags={tags[1]}"
        )

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data) == 1
        mock_voice_library_service.search_voices.assert_called_once_with(
            query=None, provider=None, gender=None, tags=tags
        )

    def test_search_voices_multiple_filters(
        self, client: TestClient, mock_voice_library_service
    ):
        """Test searching voices with multiple filters."""
        # Arrange
        query = "professional"
        provider = "elevenlabs"
        gender = "female"
        expected_results = [
            VoiceEntry(
                sts_id="prof_female",
                provider="elevenlabs",
                config={"voice_id": "xyz789"},
                voice_properties=VoiceProperties(gender="female"),
            )
        ]
        mock_voice_library_service.search_voices.return_value = expected_results

        # Act
        response = client.get(
            f"/api/voice-library/search?query={query}&provider={provider}&gender={gender}"
        )

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data) == 1
        mock_voice_library_service.search_voices.assert_called_once_with(
            query=query, provider=provider, gender=gender, tags=None
        )

    def test_search_voices_no_results(
        self, client: TestClient, mock_voice_library_service
    ):
        """Test searching voices with no matching results."""
        # Arrange
        mock_voice_library_service.search_voices.return_value = []

        # Act
        response = client.get("/api/voice-library/search?query=nonexistent")

        # Assert
        assert response.status_code == 200
        assert response.json() == []

    def test_search_voices_no_filters(
        self, client: TestClient, mock_voice_library_service, sample_search_results
    ):
        """Test searching voices without any filters."""
        # Arrange
        mock_voice_library_service.search_voices.return_value = sample_search_results

        # Act
        response = client.get("/api/voice-library/search")

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data) == 2
        mock_voice_library_service.search_voices.assert_called_once_with(
            query=None, provider=None, gender=None, tags=None
        )

    def test_search_voices_service_error(
        self, client: TestClient, mock_voice_library_service
    ):
        """Test handling of service errors during voice search."""
        # Arrange
        mock_voice_library_service.search_voices.side_effect = Exception("Search error")

        # Act
        response = client.get("/api/voice-library/search?query=test")

        # Assert
        assert response.status_code == 500
        assert "Failed to search voices" in response.json()["detail"]


class TestVoiceLibraryStats:
    """Tests for GET /voice-library/stats endpoint."""

    @pytest.fixture
    def mock_voice_library_service(self):
        """Mock the voice library service."""
        with (
            patch.object(
                voice_library_service, "get_available_providers"
            ) as mock_get_providers,
            patch.object(
                voice_library_service, "get_provider_voices"
            ) as mock_get_voices,
            patch.object(
                voice_library_service, "get_voice_details"
            ) as mock_get_details,
            patch.object(voice_library_service, "search_voices") as mock_search,
            patch.object(voice_library_service, "get_voice_stats") as mock_get_stats,
            patch.object(voice_library_service, "expand_sts_id") as mock_expand,
        ):
            # Create a mock object with all the methods
            mock = type(
                "MockService",
                (),
                {
                    "get_available_providers": mock_get_providers,
                    "get_provider_voices": mock_get_voices,
                    "get_voice_details": mock_get_details,
                    "search_voices": mock_search,
                    "get_voice_stats": mock_get_stats,
                    "expand_sts_id": mock_expand,
                },
            )()
            yield mock

    def test_get_voice_library_stats_success(
        self, client: TestClient, mock_voice_library_service
    ):
        """Test successful retrieval of voice library statistics."""
        # Arrange
        expected_stats = {
            "total_voices": 15,
            "providers": {"openai": 6, "elevenlabs": 9},
            "genders": {"male": 7, "female": 6, "neutral": 2},
            "languages": ["en", "es", "fr"],
        }
        mock_voice_library_service.get_voice_stats.return_value = expected_stats

        # Act
        response = client.get("/api/voice-library/stats")

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert response_data == expected_stats
        assert response_data["total_voices"] == 15
        assert response_data["providers"]["openai"] == 6
        assert response_data["genders"]["male"] == 7
        mock_voice_library_service.get_voice_stats.assert_called_once()

    def test_get_voice_library_stats_empty(
        self, client: TestClient, mock_voice_library_service
    ):
        """Test voice library stats when no data is available."""
        # Arrange
        empty_stats = {
            "total_voices": 0,
            "providers": {},
            "genders": {},
            "languages": [],
        }
        mock_voice_library_service.get_voice_stats.return_value = empty_stats

        # Act
        response = client.get("/api/voice-library/stats")

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert response_data == empty_stats
        assert response_data["total_voices"] == 0

    def test_get_voice_library_stats_service_error(
        self, client: TestClient, mock_voice_library_service
    ):
        """Test handling of service errors when getting voice library stats."""
        # Arrange
        mock_voice_library_service.get_voice_stats.side_effect = Exception(
            "Stats error"
        )

        # Act
        response = client.get("/api/voice-library/stats")

        # Assert
        assert response.status_code == 500
        assert "Failed to get stats" in response.json()["detail"]


class TestStsIdExpansion:
    """Tests for POST /voice-library/{provider}/{sts_id}/expand endpoint."""

    @pytest.fixture
    def mock_voice_library_service(self):
        """Mock the voice library service."""
        with (
            patch.object(
                voice_library_service, "get_available_providers"
            ) as mock_get_providers,
            patch.object(
                voice_library_service, "get_provider_voices"
            ) as mock_get_voices,
            patch.object(
                voice_library_service, "get_voice_details"
            ) as mock_get_details,
            patch.object(voice_library_service, "search_voices") as mock_search,
            patch.object(voice_library_service, "get_voice_stats") as mock_get_stats,
            patch.object(voice_library_service, "expand_sts_id") as mock_expand,
        ):
            # Create a mock object with all the methods
            mock = type(
                "MockService",
                (),
                {
                    "get_available_providers": mock_get_providers,
                    "get_provider_voices": mock_get_voices,
                    "get_voice_details": mock_get_details,
                    "search_voices": mock_search,
                    "get_voice_stats": mock_get_stats,
                    "expand_sts_id": mock_expand,
                },
            )()
            yield mock

    def test_expand_sts_id_success(
        self, client: TestClient, mock_voice_library_service
    ):
        """Test successful expansion of sts_id to full configuration."""
        # Arrange
        provider = "openai"
        sts_id = "alloy"
        expected_config = {
            "voice": "alloy",
            "model": "tts-1",
            "speed": 1.0,
            "response_format": "mp3",
        }
        mock_voice_library_service.expand_sts_id.return_value = expected_config

        # Act
        response = client.post(f"/api/voice-library/{provider}/{sts_id}/expand")

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert response_data == expected_config
        assert response_data["voice"] == "alloy"
        assert response_data["model"] == "tts-1"
        mock_voice_library_service.expand_sts_id.assert_called_once_with(
            provider, sts_id
        )

    def test_expand_sts_id_not_found(
        self, client: TestClient, mock_voice_library_service
    ):
        """Test expansion of non-existent sts_id."""
        # Arrange
        provider = "openai"
        sts_id = "nonexistent"
        mock_voice_library_service.expand_sts_id.return_value = {}

        # Act
        response = client.post(f"/api/voice-library/{provider}/{sts_id}/expand")

        # Assert
        assert response.status_code == 404
        assert f"Voice {provider}/{sts_id} not found" in response.json()["detail"]

    def test_expand_sts_id_service_error(
        self, client: TestClient, mock_voice_library_service
    ):
        """Test handling of service errors during sts_id expansion."""
        # Arrange
        provider = "openai"
        sts_id = "alloy"
        mock_voice_library_service.expand_sts_id.side_effect = Exception(
            "Expansion error"
        )

        # Act
        response = client.post(f"/api/voice-library/{provider}/{sts_id}/expand")

        # Assert
        assert response.status_code == 500
        assert "Failed to expand sts_id" in response.json()["detail"]

    def test_expand_sts_id_empty_config(
        self, client: TestClient, mock_voice_library_service
    ):
        """Test expansion that returns empty configuration."""
        # Arrange
        provider = "elevenlabs"
        sts_id = "empty_voice"
        mock_voice_library_service.expand_sts_id.return_value = None

        # Act
        response = client.post(f"/api/voice-library/{provider}/{sts_id}/expand")

        # Assert
        assert response.status_code == 404
        assert f"Voice {provider}/{sts_id} not found" in response.json()["detail"]
