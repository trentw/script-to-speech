#!/usr/bin/env python3
"""Quick test script for the GUI backend."""

import sys
import os
from pathlib import Path

# Add the script-to-speech source to the Python path
STS_SRC_PATH = Path(__file__).parent.parent.parent.parent / "src"
sys.path.insert(0, str(STS_SRC_PATH))

from script_to_speech.gui_backend.services.provider_service import provider_service
from script_to_speech.gui_backend.services.voice_library_service import voice_library_service


def test_provider_service():
    """Test the provider service."""
    print("Testing Provider Service...")
    
    providers = provider_service.get_available_providers()
    print(f"Available providers: {providers}")
    
    if providers:
        provider = providers[0]
        info = provider_service.get_provider_info(provider)
        print(f"\nProvider {provider} info:")
        print(f"  Required fields: {[f.name for f in info.required_fields]}")
        print(f"  Optional fields: {[f.name for f in info.optional_fields]}")
        
        # Test validation
        test_config = {}
        result = provider_service.validate_config(provider, test_config)
        print(f"  Validation result: valid={result.valid}, errors={result.errors}")


def test_voice_library_service():
    """Test the voice library service."""
    print("\nTesting Voice Library Service...")
    
    providers = voice_library_service.get_available_providers()
    print(f"Voice library providers: {providers}")
    
    if providers:
        provider = providers[0]
        voices = voice_library_service.get_provider_voices(provider)
        print(f"\nProvider {provider} has {len(voices)} voices")
        
        if voices:
            voice = voices[0]
            print(f"  Sample voice: {voice.sts_id}")
            if voice.preview_url:
                print(f"  Preview URL: {voice.preview_url}")
            
            # Test getting details
            details = voice_library_service.get_voice_details(provider, voice.sts_id)
            if details:
                print(f"  Voice details loaded: {len(details.expanded_config)} config items")


if __name__ == "__main__":
    test_provider_service()
    test_voice_library_service()
    print("\nBackend services test completed!")