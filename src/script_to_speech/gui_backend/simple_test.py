#!/usr/bin/env python3
"""Simple test script for the GUI backend without heavy dependencies."""

from script_to_speech.gui_backend.models import ProviderField, FieldType, ProviderInfo


def test_models():
    """Test the Pydantic models."""
    print("Testing Pydantic models...")

    # Test ProviderField
    field = ProviderField(
        name="voice",
        type=FieldType.STRING,
        required=True,
        description="Voice identifier",
        options=["alloy", "echo", "fable"],
    )
    print(f"Created field: {field.name} ({field.type})")

    # Test ProviderInfo
    info = ProviderInfo(
        identifier="test",
        name="Test Provider",
        required_fields=[field],
        optional_fields=[],
        max_threads=2,
    )
    print(
        f"Created provider info: {info.name} with {len(info.required_fields)} required fields"
    )

    print("✓ Models test passed!")


def test_config():
    """Test the configuration."""
    from script_to_speech.gui_backend.config import settings

    print(f"Host: {settings.HOST}")
    print(f"Port: {settings.PORT}")
    print(f"Audio output dir: {settings.AUDIO_OUTPUT_DIR}")
    print("✓ Config test passed!")


if __name__ == "__main__":
    test_models()
    test_config()
    print("\nSimple backend test completed!")
