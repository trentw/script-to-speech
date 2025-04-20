import unittest
from unittest.mock import MagicMock, patch

from tts_providers.dummy_common.mixin import DummyProviderMixin


class TestDummyProviderMixin(unittest.TestCase):
    """Tests for the DummyProviderMixin class."""

    def test_get_yaml_instructions(self):
        """Test that YAML instructions are returned."""
        instructions = DummyProviderMixin.get_yaml_instructions()
        self.assertIsInstance(instructions, str)
        self.assertIn("Dummy TTS Provider Configuration", instructions)

    def test_get_required_fields(self):
        """Test that required fields are returned."""
        fields = DummyProviderMixin.get_required_fields()
        self.assertEqual(fields, [])  # No required fields for dummy providers

    def test_get_optional_fields(self):
        """Test that optional fields are returned."""
        fields = DummyProviderMixin.get_optional_fields()
        self.assertIn("dummy_id", fields)
        self.assertIn("dummy_request_time", fields)
        self.assertIn("dummy_request_additional_delay", fields)
        self.assertIn("dummy_generate_silent", fields)

    def test_validate_speaker_config_valid(self):
        """Test validation with valid configurations."""
        # Empty config
        DummyProviderMixin.validate_speaker_config({})

        # Config with all optional fields
        config = {
            "dummy_id": "test_id",
            "dummy_request_time": 0.5,
            "dummy_request_additional_delay": 0.3,
            "dummy_generate_silent": True,
        }
        DummyProviderMixin.validate_speaker_config(config)

    def test_validate_speaker_config_invalid(self):
        """Test validation with invalid configurations."""
        # Invalid id type
        with self.assertRaises(ValueError):
            DummyProviderMixin.validate_speaker_config({"dummy_id": 123})

        # Invalid dummy_request_time type
        with self.assertRaises(ValueError):
            DummyProviderMixin.validate_speaker_config({"dummy_request_time": "0.5"})

        # Invalid dummy_request_additional_delay type
        with self.assertRaises(ValueError):
            DummyProviderMixin.validate_speaker_config(
                {"dummy_request_additional_delay": "0.3"}
            )

        # Invalid dummy_generate_silent type
        with self.assertRaises(ValueError):
            DummyProviderMixin.validate_speaker_config(
                {"dummy_generate_silent": "true"}
            )

    def test_get_speaker_identifier(self):
        """Test that speaker identifiers are generated correctly."""
        # With custom ID
        config = {"dummy_id": "test_id"}
        identifier = DummyProviderMixin.get_speaker_identifier(config)
        self.assertEqual(identifier, "dummy_id_test_id")

        # With empty ID
        config = {"dummy_id": ""}
        identifier = DummyProviderMixin.get_speaker_identifier(config)
        self.assertEqual(identifier, "dummy_standard_voice")

        # With no ID
        config = {}
        identifier = DummyProviderMixin.get_speaker_identifier(config)
        self.assertEqual(identifier, "dummy_standard_voice")

        # With silent flag
        config = {"dummy_generate_silent": True}
        identifier = DummyProviderMixin.get_speaker_identifier(config)
        self.assertEqual(identifier, "dummy_silent_voice")

        # With both ID and silent flag (ID takes precedence)
        config = {"dummy_id": "test_id", "dummy_generate_silent": True}
        identifier = DummyProviderMixin.get_speaker_identifier(config)
        self.assertEqual(identifier, "dummy_id_test_id")

    def test_get_max_download_threads(self):
        """Test that max download threads is returned."""
        threads = DummyProviderMixin.get_max_download_threads()
        self.assertEqual(threads, 5)

    def test_instantiate_client(self):
        """Test that a client can be instantiated."""
        # Instead of trying to mock the backend, let's modify our test to check
        # that the client is a DummyTTSClient instance
        client = DummyProviderMixin.instantiate_client()

        # Verify the client is of the correct type
        from dummy_tts_backend.backend import DummyTTSClient

        self.assertIsInstance(client, DummyTTSClient)

    def test_generate_dummy_audio(self):
        """Test that dummy audio generation works correctly."""
        # Create mock client
        mock_client = MagicMock()
        mock_client.generate_audio.return_value = b"test_audio"

        # Test with minimal config
        config = {}
        audio = DummyProviderMixin._generate_dummy_audio(
            mock_client, config, "test text"
        )
        self.assertEqual(audio, b"test_audio")
        mock_client.generate_audio.assert_called_with(
            text="test text",
            request_time=None,
            additional_delay=None,
            generate_silent=False,
        )

        # Test with full config
        config = {
            "dummy_request_time": 0.5,
            "dummy_request_additional_delay": 0.3,
            "dummy_generate_silent": True,
        }
        audio = DummyProviderMixin._generate_dummy_audio(
            mock_client, config, "test text"
        )
        self.assertEqual(audio, b"test_audio")
        mock_client.generate_audio.assert_called_with(
            text="test text",
            request_time=0.5,
            additional_delay=0.3,
            generate_silent=True,
        )


if __name__ == "__main__":
    unittest.main()
