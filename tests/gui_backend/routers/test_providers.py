"""Tests for providers router endpoints."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


class TestProvidersEndpoints:
    """Tests for TTS providers endpoints."""

    @pytest.fixture
    def mock_provider_service(self):
        """Mock the provider service."""
        with patch(
            "script_to_speech.gui_backend.routers.providers.provider_service"
        ) as mock:
            yield mock

    def test_get_providers_success(self, client: TestClient, mock_provider_service):
        """Test successful retrieval of providers."""
        # Arrange
        expected_providers = ["openai", "elevenlabs", "cartesia"]
        mock_provider_service.get_available_providers.return_value = expected_providers

        # Act
        response = client.get("/api/providers")

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert response_data == expected_providers
        mock_provider_service.get_available_providers.assert_called_once()

    def test_get_providers_empty(self, client: TestClient, mock_provider_service):
        """Test providers endpoint when no providers are available."""
        # Arrange
        mock_provider_service.get_available_providers.return_value = []

        # Act
        response = client.get("/api/providers")

        # Assert
        assert response.status_code == 200
        assert response.json() == []

    def test_get_providers_service_error(
        self, client: TestClient, mock_provider_service
    ):
        """Test handling of service errors in providers endpoint."""
        # Arrange
        mock_provider_service.get_available_providers.side_effect = Exception(
            "Provider service error"
        )

        # Act
        response = client.get("/api/providers")

        # Assert
        assert response.status_code == 500
        assert "Failed to get providers" in response.json()["detail"]

    def test_get_specific_provider_success(
        self, client: TestClient, mock_provider_service
    ):
        """Test successful retrieval of a specific provider."""
        # Arrange
        from script_to_speech.gui_backend.models import (
            FieldType,
            ProviderField,
            ProviderInfo,
        )

        provider_id = "openai"
        expected_provider = ProviderInfo(
            identifier="openai",
            name="Openai",
            description="Openai TTS Provider",
            required_fields=[
                ProviderField(
                    name="voice",
                    type=FieldType.STRING,
                    required=True,
                    description="OpenAI voice identifier",
                    options=["alloy", "echo", "fable", "onyx", "nova", "shimmer"],
                )
            ],
            optional_fields=[
                ProviderField(
                    name="model",
                    type=FieldType.STRING,
                    required=False,
                    description="TTS model",
                )
            ],
            max_threads=4,
        )
        mock_provider_service.get_provider_info.return_value = expected_provider

        # Act
        response = client.get(f"/api/providers/{provider_id}")

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["identifier"] == "openai"
        assert response_data["name"] == "Openai"
        assert len(response_data["required_fields"]) == 1
        assert response_data["required_fields"][0]["name"] == "voice"
        mock_provider_service.get_provider_info.assert_called_once_with(provider_id)

    def test_get_specific_provider_not_found(
        self, client: TestClient, mock_provider_service
    ):
        """Test retrieval of a non-existent provider."""
        # Arrange
        provider_id = "non_existent_provider"
        mock_provider_service.get_provider_info.side_effect = ValueError(
            f"Provider {provider_id} not found"
        )

        # Act
        response = client.get(f"/api/providers/{provider_id}")

        # Assert
        assert response.status_code == 404
        assert f"Provider {provider_id} not found" in response.json()["detail"]

    def test_get_specific_provider_service_error(
        self, client: TestClient, mock_provider_service
    ):
        """Test handling of service errors when getting specific provider."""
        # Arrange
        provider_id = "openai"
        mock_provider_service.get_provider_info.side_effect = Exception("Service error")

        # Act
        response = client.get(f"/api/providers/{provider_id}")

        # Assert
        assert response.status_code == 500
        assert "Failed to get provider info" in response.json()["detail"]


class TestProvidersInfo:
    """Tests for providers info endpoints."""

    @pytest.fixture
    def mock_provider_service(self):
        """Mock the provider service."""
        with patch(
            "script_to_speech.gui_backend.routers.providers.provider_service"
        ) as mock:
            yield mock

    def test_get_all_providers_info_success(
        self, client: TestClient, mock_provider_service
    ):
        """Test successful retrieval of all providers info."""
        # Arrange
        from script_to_speech.gui_backend.models import (
            FieldType,
            ProviderField,
            ProviderInfo,
        )

        expected_providers = [
            ProviderInfo(
                identifier="openai",
                name="Openai",
                description="Openai TTS Provider",
                required_fields=[
                    ProviderField(
                        name="voice",
                        type=FieldType.STRING,
                        required=True,
                        description="OpenAI voice identifier",
                    )
                ],
                optional_fields=[],
                max_threads=4,
            ),
            ProviderInfo(
                identifier="elevenlabs",
                name="Elevenlabs",
                description="Elevenlabs TTS Provider",
                required_fields=[
                    ProviderField(
                        name="voice_id",
                        type=FieldType.STRING,
                        required=True,
                        description="ElevenLabs voice ID",
                    )
                ],
                optional_fields=[],
                max_threads=3,
            ),
        ]
        mock_provider_service.get_all_providers.return_value = expected_providers

        # Act
        response = client.get("/api/providers/info")

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data) == 2
        assert response_data[0]["identifier"] == "openai"
        assert response_data[1]["identifier"] == "elevenlabs"
        mock_provider_service.get_all_providers.assert_called_once()

    def test_get_all_providers_info_empty(
        self, client: TestClient, mock_provider_service
    ):
        """Test providers info endpoint when no providers are available."""
        # Arrange
        mock_provider_service.get_all_providers.return_value = []

        # Act
        response = client.get("/api/providers/info")

        # Assert
        assert response.status_code == 200
        assert response.json() == []

    def test_get_all_providers_info_service_error(
        self, client: TestClient, mock_provider_service
    ):
        """Test handling of service errors in providers info endpoint."""
        # Arrange
        mock_provider_service.get_all_providers.side_effect = Exception(
            "Provider service error"
        )

        # Act
        response = client.get("/api/providers/info")

        # Assert
        assert response.status_code == 500
        assert "Failed to get provider info" in response.json()["detail"]


class TestProviderConfiguration:
    """Tests for provider configuration endpoints."""

    @pytest.fixture
    def mock_provider_service(self):
        """Mock the provider service."""
        with patch(
            "script_to_speech.gui_backend.routers.providers.provider_service"
        ) as mock:
            yield mock

    def test_validate_provider_config_success(
        self, client: TestClient, mock_provider_service
    ):
        """Test successful validation of provider configuration."""
        # Arrange
        provider_id = "openai"
        config = {"model": "tts-1", "speed": 1.0}
        from script_to_speech.gui_backend.models import ValidationResult

        validation_result = ValidationResult(valid=True, errors=[], warnings=[])
        mock_provider_service.validate_config.return_value = validation_result

        # Act
        response = client.post(f"/api/providers/{provider_id}/validate", json=config)

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["valid"] == validation_result.valid
        assert response_data["errors"] == validation_result.errors
        assert response_data["warnings"] == validation_result.warnings
        mock_provider_service.validate_config.assert_called_once_with(
            provider_id, config
        )

    def test_validate_provider_config_invalid(
        self, client: TestClient, mock_provider_service
    ):
        """Test validation of invalid provider configuration."""
        # Arrange
        provider_id = "openai"
        config = {"model": "invalid_model", "speed": -1.0}  # Invalid speed
        from script_to_speech.gui_backend.models import ValidationResult

        validation_result = ValidationResult(
            valid=False,
            errors=[
                "Invalid model: invalid_model",
                "Speed must be between 0.25 and 4.0",
            ],
            warnings=[],
        )
        mock_provider_service.validate_config.return_value = validation_result

        # Act
        response = client.post(f"/api/providers/{provider_id}/validate", json=config)

        # Assert
        assert response.status_code == 200  # Still 200, but validation failed
        response_data = response.json()
        assert response_data["valid"] == validation_result.valid
        assert response_data["errors"] == validation_result.errors
        assert response_data["warnings"] == validation_result.warnings
        assert response_data["valid"] is False
        assert len(response_data["errors"]) == 2

    def test_validate_provider_config_provider_not_found(
        self, client: TestClient, mock_provider_service
    ):
        """Test config validation for non-existent provider."""
        # Arrange
        provider_id = "non_existent"
        config = {"model": "tts-1"}
        mock_provider_service.validate_config.side_effect = ValueError(
            f"Provider {provider_id} not found"
        )

        # Act
        response = client.post(f"/api/providers/{provider_id}/validate", json=config)

        # Assert
        assert response.status_code == 404
        assert f"Provider {provider_id} not found" in response.json()["detail"]

    def test_validate_provider_config_service_error(
        self, client: TestClient, mock_provider_service
    ):
        """Test handling of service errors during config validation."""
        # Arrange
        provider_id = "openai"
        config = {"model": "tts-1"}
        mock_provider_service.validate_config.side_effect = Exception(
            "Validation error"
        )

        # Act
        response = client.post(f"/api/providers/{provider_id}/validate", json=config)

        # Assert
        assert response.status_code == 500
        assert "Failed to validate config" in response.json()["detail"]
