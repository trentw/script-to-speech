import logging
from collections import OrderedDict
from typing import Dict, Optional, Tuple
from elevenlabs.client import ElevenLabs
import requests


class ElevenLabsVoiceLibraryManager:
    """Manages the voice library for ElevenLabs, handling the 30-voice limit and ID mapping."""

    def __init__(self, api_key: str, debug: bool = False):
        self.api_key = api_key
        self.client = ElevenLabs(api_key=api_key)
        # Maps public_voice_id -> (library_voice_id, category)
        self.voice_library: Dict[str, Tuple[str, str]] = {}
        self.voice_lru = OrderedDict()  # Maintains order of voice usage
        self.is_initialized = False

        # Setup logging
        self.logger = logging.getLogger('ElevenLabsVoiceLibraryManager')
        level = logging.DEBUG if debug else logging.INFO
        self.logger.setLevel(level)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def _initialize_voice_library(self) -> None:
        """
        Initialize the voice library by querying current voices.
        Maintains LRU order while ensuring consistency with actual voice library.
        """
        self.logger.info("Initializing voice library mapping")
        response = self.client.voices.get_all()

        # Clear existing voice library
        self.voice_library.clear()

        # Keep track of currently valid voice IDs
        current_voice_ids = set()

        # Build new voice library
        for voice in response.voices:
            if self.logger.isEnabledFor(logging.DEBUG):
                self.logger.debug(f"\nVoice object details:")
                self.logger.debug(f"Voice ID: {voice.voice_id}")
                self.logger.debug(f"Name: {getattr(voice, 'name', 'N/A')}")
                self.logger.debug(f"Category: {voice.category}")

                # Log sharing attribute details
                if hasattr(voice, 'sharing'):
                    self.logger.debug(
                        f"Has sharing attribute: {voice.sharing is not None}")
                    if voice.sharing is not None:
                        self.logger.debug(
                            f"Original voice ID: {getattr(voice.sharing, 'original_voice_id', None)}")

            # Handle premade voices (no sharing attribute)
            if not hasattr(voice, 'sharing') or voice.sharing is None:
                public_id = voice.voice_id
                library_id = voice.voice_id
                category = getattr(voice, 'category', 'premade')
            # Handle shared/cloned voices
            else:
                public_id = voice.sharing.original_voice_id or voice.voice_id
                library_id = voice.voice_id
                category = voice.category

            self.voice_library[public_id] = (library_id, category)

            # Add to LRU if not premade
            if category != "premade":
                current_voice_ids.add(public_id)

            self.logger.debug(
                f"Successfully mapped voice:"
                f"\n  Public ID: {public_id}"
                f"\n  Library ID: {library_id}"
                f"\n  Category: {category}"
            )

        # Prune LRU of voices that no longer exist while maintaining order
        valid_lru = OrderedDict()
        for voice_id in list(self.voice_lru.keys()):
            if voice_id in current_voice_ids:
                valid_lru[voice_id] = None
        self.voice_lru = valid_lru

        self.logger.info(
            f"Initialized voice library with {len(self.voice_library)} voices "
            f"({len(self.voice_lru)} non-premade)"
        )
        self.is_initialized = True

    def _find_voice_owner(self, public_voice_id: str) -> Optional[str]:
        """
        Find the public owner ID for a voice using the library search.
        """
        self.logger.debug(f"Searching for owner of voice {public_voice_id}")
        response = self.client.voices.get_shared(search=public_voice_id)

        for voice in response.voices:
            if voice.voice_id == public_voice_id:
                self.logger.debug(
                    f"Found owner {voice.public_owner_id} for voice {public_voice_id}"
                )
                return voice.public_owner_id

        return None

    def _add_voice_to_library(self, public_voice_id: str, public_owner_id: str) -> None:
        """
        Add a voice to the user's voice library and refresh local state.
        """
        self.logger.info(f"Adding voice {public_voice_id} to library")
        url = f"https://api.elevenlabs.io/v1/voices/add/{public_owner_id}/{public_voice_id}"

        headers = {
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }

        # Use the public voice ID as the name in the library
        payload = {"new_name": public_voice_id}

        response = requests.post(url, json=payload, headers=headers)
        if not response.ok:
            raise RuntimeError(
                f"Failed to add voice to library: {response.text}")

        self.logger.info(
            f"Successfully added voice {public_voice_id} to library")

        # Refresh voice library and LRU state
        self._initialize_voice_library()

    def _remove_voice_from_library(self, library_voice_id: str) -> None:
        """
        Remove a voice from the user's voice library and refresh local state.
        """
        self.logger.info(f"Removing voice {library_voice_id} from library")
        url = f"https://api.elevenlabs.io/v1/voices/{library_voice_id}"

        headers = {"xi-api-key": self.api_key}

        response = requests.delete(url, headers=headers)
        if not response.ok:
            raise RuntimeError(
                f"Failed to remove voice from library: {response.text}")

        self.logger.info(f"Successfully removed voice {library_voice_id}")

        # Refresh voice library and LRU state
        self._initialize_voice_library()

    def _make_room_in_library(self) -> None:
        """
        Make room in the voice library by removing a voice.
        """
        # Try to remove least recently used voice first
        if self.voice_lru:
            lru_public_id = next(iter(self.voice_lru))
            lru_library_id = self.voice_library[lru_public_id][0]
            self.logger.info(
                f"Removing least recently used voice {lru_public_id} "
                f"(library ID: {lru_library_id})"
            )
            self._remove_voice_from_library(lru_library_id)
            return

        # If no LRU history, remove a random non-premade voice
        for public_id, (library_id, category) in self.voice_library.items():
            if category != "premade":
                self.logger.info(
                    f"Removing random non-premade voice {public_id} "
                    f"(library ID: {library_id})"
                )
                self._remove_voice_from_library(library_id)
                return

        raise RuntimeError("No removable voices found in library")

    def get_library_voice_id(self, public_voice_id: str) -> str:
        """
        Get or create a library voice ID for a public voice ID.

        Args:
            public_voice_id: The public voice ID to process

        Returns:
            str: The voice ID to use in the user's library

        Raises:
            RuntimeError: If the voice cannot be added to the library
        """
        # Initialize if needed
        if not self.is_initialized:
            self._initialize_voice_library()

        # Update LRU cache if it's a non-premade voice
        if public_voice_id in self.voice_lru:
            self.voice_lru.move_to_end(public_voice_id)

        # Check if voice is already in library
        if public_voice_id in self.voice_library:
            library_id, _ = self.voice_library[public_voice_id]
            return library_id

        # Count non-premade voices
        non_premade_count = sum(
            1 for _, category in self.voice_library.values()
            if category != "premade"
        )

        # Make room if needed
        if non_premade_count >= 30:
            self._make_room_in_library()

        # Find voice owner
        public_owner_id = self._find_voice_owner(public_voice_id)
        if not public_owner_id:
            raise RuntimeError(
                f"Could not find owner for voice {public_voice_id}")

        # Add voice to library
        self._add_voice_to_library(public_voice_id, public_owner_id)

        # Return the new library ID (voice library was refreshed in _add_voice_to_library)
        return self.voice_library[public_voice_id][0]
