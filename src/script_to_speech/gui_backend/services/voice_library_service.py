"""Voice library integration service."""

import logging
from typing import Dict, List, Optional, Any

from script_to_speech.voice_library.voice_library import VoiceLibrary

from ..models import (
    VoiceEntry, VoiceDetails, VoiceProperties, VoiceDescription, VoiceTags
)

logger = logging.getLogger(__name__)


class VoiceLibraryService:
    """Service for voice library integration."""
    
    def __init__(self) -> None:
        """Initialize the voice library service."""
        self._voice_library = VoiceLibrary()
        self._voices_cache: Dict[str, List[VoiceEntry]] = {}
        self._load_voice_library()
    
    def _load_voice_library(self) -> None:
        """Load and cache voice library data."""
        try:
            # Get all available providers by scanning the voice library directory
            all_providers = self._get_available_providers_from_filesystem()
            
            for provider in all_providers:
                try:
                    voices = self._get_provider_voices(provider)
                    self._voices_cache[provider] = voices
                    logger.info(f"Loaded {len(voices)} voices for provider: {provider}")
                except Exception as e:
                    logger.warning(f"Failed to load voices for provider {provider}: {e}")
                    self._voices_cache[provider] = []
                    
        except Exception as e:
            logger.error(f"Failed to load voice library: {e}")
    
    def _get_available_providers_from_filesystem(self) -> List[str]:
        """Get available providers by scanning the voice library directory."""
        try:
            from script_to_speech.voice_library.constants import REPO_VOICE_LIBRARY_PATH
            
            providers = []
            if REPO_VOICE_LIBRARY_PATH.exists():
                for provider_dir in REPO_VOICE_LIBRARY_PATH.iterdir():
                    if (provider_dir.is_dir() and 
                        not provider_dir.name.startswith('.') and 
                        not provider_dir.name.startswith('dummy_')):
                        # Check if directory has any .yaml files
                        yaml_files = list(provider_dir.glob("*.yaml"))
                        if yaml_files:
                            providers.append(provider_dir.name)
            
            return providers
        except Exception as e:
            logger.error(f"Failed to scan voice library directory: {e}")
            return []
    
    def _get_provider_voices(self, provider: str) -> List[VoiceEntry]:
        """Get all voices for a specific provider."""
        voices = []
        
        try:
            # Get voice IDs for the provider by loading voice data directly
            voice_ids = self._get_voice_ids_for_provider(provider)
            
            for voice_id in voice_ids:
                try:
                    voice_entry = self._create_voice_entry(provider, voice_id)
                    if voice_entry:
                        voices.append(voice_entry)
                except Exception as e:
                    logger.warning(f"Failed to create voice entry for {provider}/{voice_id}: {e}")
                    
        except Exception as e:
            logger.warning(f"Failed to get voice IDs for provider {provider}: {e}")
        
        return voices
    
    def _get_voice_ids_for_provider(self, provider: str) -> List[str]:
        """Get all voice IDs for a specific provider by directly reading voice library files."""
        try:
            # Load provider voices to get the voice data
            provider_voices = self._voice_library._load_provider_voices(provider)
            return list(provider_voices.keys())
        except Exception as e:
            logger.warning(f"Failed to get voice IDs for provider {provider}: {e}")
            return []
    
    def _create_voice_entry(self, provider: str, sts_id: str) -> Optional[VoiceEntry]:
        """Create a VoiceEntry from provider and sts_id."""
        try:
            # Get voice data by accessing the internal cache directly
            provider_voices = self._voice_library._load_provider_voices(provider)
            voice_data = provider_voices.get(sts_id)
            if not voice_data:
                return None
            
            # Extract configuration
            config = voice_data.get("config", {})
            
            # Extract voice properties
            voice_properties = None
            if "voice_properties" in voice_data:
                props_data = voice_data["voice_properties"]
                voice_properties = VoiceProperties(
                    accent=props_data.get("accent"),
                    gender=props_data.get("gender"),
                    age=props_data.get("age"),
                    authority=props_data.get("authority"),
                    energy=props_data.get("energy"),
                    pace=props_data.get("pace"),
                    performative=props_data.get("performative"),
                    pitch=props_data.get("pitch"),
                    quality=props_data.get("quality"),
                    range=props_data.get("range")
                )
            
            # Extract description
            description = None
            if "description" in voice_data:
                desc_data = voice_data["description"]
                description = VoiceDescription(
                    provider_name=desc_data.get("provider_name"),
                    provider_description=desc_data.get("provider_description"),
                    provider_use_cases=desc_data.get("provider_use_cases"),
                    custom_description=desc_data.get("custom_description"),
                    perceived_age=desc_data.get("perceived_age")
                )
            
            # Extract tags
            tags = None
            if "tags" in voice_data:
                tags_data = voice_data["tags"]
                tags = VoiceTags(
                    provider_use_cases=tags_data.get("provider_use_cases"),
                    custom_tags=tags_data.get("custom_tags"),
                    character_types=tags_data.get("character_types")
                )
            
            # Extract preview URL
            preview_url = voice_data.get("preview_url")
            
            return VoiceEntry(
                sts_id=sts_id,
                provider=provider,
                config=config,
                voice_properties=voice_properties,
                description=description,
                tags=tags,
                preview_url=preview_url
            )
            
        except Exception as e:
            logger.error(f"Failed to create voice entry for {provider}/{sts_id}: {e}")
            return None
    
    def get_available_providers(self) -> List[str]:
        """Get list of providers with voice library data."""
        return list(self._voices_cache.keys())
    
    def get_provider_voices(self, provider: str) -> List[VoiceEntry]:
        """Get all voices for a specific provider."""
        return self._voices_cache.get(provider, [])
    
    def get_voice_details(self, provider: str, sts_id: str) -> Optional[VoiceDetails]:
        """Get detailed information about a specific voice."""
        try:
            # Create basic voice entry
            voice_entry = self._create_voice_entry(provider, sts_id)
            if not voice_entry:
                return None
            
            # Get expanded configuration
            expanded_config = {}
            try:
                expanded_config = self._voice_library.expand_config(provider, sts_id)
            except Exception as e:
                logger.warning(f"Failed to expand config for {provider}/{sts_id}: {e}")
                expanded_config = voice_entry.config
            
            return VoiceDetails(
                sts_id=voice_entry.sts_id,
                provider=voice_entry.provider,
                config=voice_entry.config,
                voice_properties=voice_entry.voice_properties,
                description=voice_entry.description,
                tags=voice_entry.tags,
                preview_url=voice_entry.preview_url,
                expanded_config=expanded_config
            )
            
        except Exception as e:
            logger.error(f"Failed to get voice details for {provider}/{sts_id}: {e}")
            return None
    
    def expand_sts_id(self, provider: str, sts_id: str) -> Dict[str, Any]:
        """Expand an sts_id to full provider configuration."""
        try:
            return self._voice_library.expand_config(provider, sts_id)
        except Exception as e:
            logger.error(f"Failed to expand sts_id {provider}/{sts_id}: {e}")
            return {}
    
    def search_voices(
        self, 
        query: Optional[str] = None,
        provider: Optional[str] = None,
        gender: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[VoiceEntry]:
        """Search voices based on criteria."""
        all_voices = []
        
        # Get voices from specified provider or all providers
        if provider:
            if provider in self._voices_cache:
                all_voices = self._voices_cache[provider]
        else:
            for provider_voices in self._voices_cache.values():
                all_voices.extend(provider_voices)
        
        # Apply filters
        filtered_voices = all_voices
        
        if query:
            query_lower = query.lower()
            filtered_voices = [
                voice for voice in filtered_voices
                if (query_lower in voice.sts_id.lower() or
                    (voice.description and voice.description.provider_name and 
                     query_lower in voice.description.provider_name.lower()) or
                    (voice.description and voice.description.custom_description and
                     query_lower in voice.description.custom_description.lower()))
            ]
        
        if gender:
            filtered_voices = [
                voice for voice in filtered_voices
                if (voice.voice_properties and 
                    voice.voice_properties.gender and
                    voice.voice_properties.gender.lower() == gender.lower())
            ]
        
        if tags:
            filtered_voices = [
                voice for voice in filtered_voices
                if (voice.tags and voice.tags.custom_tags and
                    any(tag.lower() in [t.lower() for t in voice.tags.custom_tags] for tag in tags))
            ]
        
        return filtered_voices
    
    def get_voice_stats(self) -> Dict[str, Any]:
        """Get statistics about the voice library."""
        stats = {
            "total_voices": 0,
            "providers": {},
            "genders": {},
            "languages": set()
        }
        
        for provider, voices in self._voices_cache.items():
            stats["providers"][provider] = len(voices)
            stats["total_voices"] += len(voices)
            
            for voice in voices:
                if voice.voice_properties and voice.voice_properties.gender:
                    gender = voice.voice_properties.gender
                    stats["genders"][gender] = stats["genders"].get(gender, 0) + 1
                
                if voice.voice_properties and voice.voice_properties.accent:
                    stats["languages"].add(voice.voice_properties.accent)
        
        stats["languages"] = list(stats["languages"])
        
        return stats


# Global instance
voice_library_service = VoiceLibraryService()