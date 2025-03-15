from collections import OrderedDict
from typing import Dict, Optional, Tuple

import requests
from elevenlabs.client import ElevenLabs

from utils.logging import get_screenplay_logger

# Get logger for this module
logger = get_screenplay_logger("tts_providers.elevenlabs.registry")


class ElevenLabsVoiceRegistryManager:
    """
    Manages the voice registry for ElevenLabs, handling the 30-voice limit and ID mapping.

    This class manages the complexity of ElevenLabs' voice system by:
    - Maintaining mapping between public voice IDs and user-specific registry IDs
    - Managing the 30-voice limit in the user's voice registry using LRU eviction

    The manager abstracts away the difference between public voice IDs (which are consistent
    across users) and registry voice IDs (which are specific to each user's registry).
    """

    def __init__(self, api_key: str, debug: bool = False):
        self.api_key = api_key
        self.client = ElevenLabs(api_key=api_key)
        # Maps public_voice_id -> (registry_voice_id, category)
        self.voice_registry: Dict[str, Tuple[str, str]] = {}
        # Maintains order of voice usage for LRU management
        self.voice_usage_order = OrderedDict()
        self.is_initialized = False

    def _initialize_voice_registry(self) -> None:
        """
        Initialize the voice registry by querying current voices.
        Maps public voice IDs to registry-specific IDs while maintaining LRU order.
        """
        logger.info("Initializing voice registry mapping")
        response = self.client.voices.get_all()

        # Clear existing registry
        self.voice_registry.clear()

        # Keep track of currently valid voice IDs
        current_voice_ids = set()

        # Build new voice registry
        for voice in response.voices:
            logger.debug(f"\nVoice object details:")
            logger.debug(f"Voice ID: {voice.voice_id}")
            logger.debug(f"Name: {getattr(voice, 'name', 'N/A')}")
            logger.debug(f"Category: {voice.category}")

            # Log sharing attribute details
            if hasattr(voice, "sharing"):
                logger.debug(f"Has sharing attribute: {voice.sharing is not None}")
                if voice.sharing is not None:
                    logger.debug(
                        f"Original voice ID: {getattr(voice.sharing, 'original_voice_id', None)}"
                    )

            try:
                # Handle premade voices (no sharing attribute)
                if not hasattr(voice, "sharing") or voice.sharing is None:
                    public_id = voice.voice_id
                    registry_id = voice.voice_id
                    category = getattr(voice, "category", "premade")
                # Handle shared/cloned voices
                else:
                    public_id = voice.sharing.original_voice_id or voice.voice_id
                    registry_id = voice.voice_id
                    category = voice.category

                # Store in registry - always add all voices
                self.voice_registry[public_id] = (registry_id, category)

                logger.debug(
                    f"Added voice to registry:"
                    f"\n  Public ID: {public_id}"
                    f"\n  Registry ID: {registry_id}"
                    f"\n  Category: {category}"
                )
            except Exception as e:
                logger.error(f"Error processing voice: {e}")

            # Add to LRU if not premade
            if category != "premade":
                current_voice_ids.add(public_id)

            logger.debug(
                f"Successfully mapped voice:"
                f"\n  Public ID: {public_id}"
                f"\n  Registry ID: {registry_id}"
                f"\n  Category: {category}"
            )

        # Prune LRU of voices that no longer exist while maintaining order
        valid_usage_order = OrderedDict()
        for voice_id in list(self.voice_usage_order.keys()):
            if voice_id in current_voice_ids:
                valid_usage_order[voice_id] = None

        # Add any new non-premade voices to LRU tracking
        for voice_id in current_voice_ids:
            if voice_id not in valid_usage_order:
                valid_usage_order[voice_id] = None

        self.voice_usage_order = valid_usage_order

        logger.info(
            f"Initialized voice registry with {len(self.voice_registry)} voices "
            f"({len(self.voice_usage_order)} non-premade)"
        )
        self.is_initialized = True

    def _find_voice_owner(self, public_voice_id: str) -> Optional[str]:
        """
        Find the public owner ID for a voice using the registry search.

        Args:
            public_voice_id: The public ID of the voice to look up

        Returns:
            Optional[str]: The public owner ID of the voice, if found
        """
        logger.debug(f"Searching for owner of voice {public_voice_id}")
        response = self.client.voices.get_shared(search=public_voice_id)

        for voice in response.voices:
            if voice.voice_id == public_voice_id:
                logger.debug(
                    f"Found owner {voice.public_owner_id} for voice {public_voice_id}"
                )
                return voice.public_owner_id

        return None

    def _add_voice_to_registry(
        self, public_voice_id: str, public_owner_id: str
    ) -> None:
        """
        Add a voice to the user's voice registry and refresh registry state.

        Args:
            public_voice_id: The public ID of the voice to add
            public_owner_id: The public ID of the voice's owner

        Raises:
            RuntimeError: If the voice cannot be added to the registry
        """
        logger.info(f"Adding voice {public_voice_id} to registry")
        url = f"https://api.elevenlabs.io/v1/voices/add/{public_owner_id}/{public_voice_id}"

        headers = {"Content-Type": "application/json", "xi-api-key": self.api_key}

        # Use the public voice ID as the name in the registry
        payload = {"new_name": public_voice_id}

        response = requests.post(url, json=payload, headers=headers)
        if not response.ok:
            error_msg = f"Failed to add voice to registry: {response.text}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        logger.info(f"Successfully added voice {public_voice_id} to registry")
        # Refresh voice registry and LRU state
        self._initialize_voice_registry()

    def _remove_voice_from_registry(self, registry_voice_id: str) -> None:
        """
        Remove a voice from the user's voice registry and refresh registry state.

        Args:
            registry_voice_id: The registry-specific ID of the voice to remove

        Raises:
            RuntimeError: If the voice cannot be removed from the registry
        """
        logger.info(f"Removing voice {registry_voice_id} from registry")
        url = f"https://api.elevenlabs.io/v1/voices/{registry_voice_id}"

        headers = {"xi-api-key": self.api_key}

        response = requests.delete(url, headers=headers)
        if not response.ok:
            error_msg = f"Failed to remove voice from registry: {response.text}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        logger.info(f"Successfully removed voice {registry_voice_id}")
        # Refresh voice registry and LRU state
        self._initialize_voice_registry()

    def _make_room_in_registry(self) -> None:
        """
        Make room in the voice registry by removing a voice using LRU policy.

        Raises:
            RuntimeError: If no removable voices are found in the registry
        """
        # Try to remove least recently used voice first
        if self.voice_usage_order:
            lru_public_id = next(iter(self.voice_usage_order))
            lru_registry_id = self.voice_registry[lru_public_id][0]
            logger.info(
                f"Removing least recently used voice {lru_public_id} "
                f"(registry ID: {lru_registry_id})"
            )
            self._remove_voice_from_registry(lru_registry_id)
            return

        # If no LRU history, remove a random non-premade voice
        for public_id, (registry_id, category) in self.voice_registry.items():
            if category != "premade":
                logger.info(
                    f"Removing random non-premade voice {public_id} "
                    f"(registry ID: {registry_id})"
                )
                self._remove_voice_from_registry(registry_id)
                return

        error_msg = "No removable voices found in registry"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    def get_library_voice_id(self, public_voice_id: str) -> str:
        """
        Get or create a registry voice ID for a public voice ID.

        This method:
        1. Checks if the voice is already in the user's registry
        2. If not, makes room in the registry if needed (removing least used voice)
        3. Adds the voice to the registry if necessary
        4. Returns the registry-specific voice ID for use with the API

        Args:
            public_voice_id: The public voice ID to process

        Returns:
            str: The voice ID to use in the user's registry

        Raises:
            RuntimeError: If the voice cannot be added to the registry
        """
        # Initialize if needed
        if not self.is_initialized:
            self._initialize_voice_registry()

        # Verify initialization was successful
        if not self.is_initialized:
            raise RuntimeError("Voice registry initialization failed")

        # Update LRU cache if it's a non-premade voice
        if public_voice_id in self.voice_usage_order:
            self.voice_usage_order.move_to_end(public_voice_id)

        # Check if voice is already in registry
        if public_voice_id in self.voice_registry:
            registry_id, _ = self.voice_registry[public_voice_id]
            return registry_id

        # Count non-premade voices
        non_premade_count = sum(
            1 for _, category in self.voice_registry.values() if category != "premade"
        )

        # Make room if needed
        if non_premade_count >= 30:
            self._make_room_in_registry()

        # Find voice owner
        public_owner_id = self._find_voice_owner(public_voice_id)
        if not public_owner_id:
            error_msg = f"Could not find owner for voice {public_voice_id}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        # Add voice to registry
        self._add_voice_to_registry(public_voice_id, public_owner_id)

        # Return the new registry ID (voice registry was refreshed in _add_voice_to_registry)
        return self.voice_registry[public_voice_id][0]
