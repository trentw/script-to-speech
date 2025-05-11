import os
import threading
import time
from typing import Optional

# Constants for the dummy backend
BASE_DELAY_SECONDS = 1.0
VARIABLE_DELAY_MS_PER_CHAR = 3.0
MAX_CONCURRENT_REQUESTS = 5
NEW_ID_LOOKUP_DELAY_SECONDS = 0.5


class DummyTTSBackend:
    """
    A simple, self-contained backend service that simulates the core functionality of a real TTS API.

    This backend:
    - Provides a client interface
    - "Generates" audio by returning pre-defined MP3 byte strings
    - Simulates network/processing delays with configurable timings
    - Simulates rate limiting using a semaphore
    - Includes a mechanism to simulate stateful lookup delays
    - Reads audio assets from files on initialization
    """

    def __init__(self) -> None:
        """Initialize the dummy TTS backend."""
        # Set constants as instance attributes
        self.BASE_DELAY_SECONDS = BASE_DELAY_SECONDS
        self.VARIABLE_DELAY_MS_PER_CHAR = VARIABLE_DELAY_MS_PER_CHAR
        self.MAX_CONCURRENT_REQUESTS = MAX_CONCURRENT_REQUESTS
        self.NEW_ID_LOOKUP_DELAY_SECONDS = NEW_ID_LOOKUP_DELAY_SECONDS

        # Determine asset path relative to backend.py
        current_dir = os.path.dirname(os.path.abspath(__file__))
        asset_dir = os.path.join(current_dir, "assets")

        # Read audio files
        try:
            with open(os.path.join(asset_dir, "dummy_audio.mp3"), "rb") as f:
                self.dummy_audio_bytes = f.read()

            with open(os.path.join(asset_dir, "silent_audio.mp3"), "rb") as f:
                self.silent_audio_bytes = f.read()
        except Exception as e:
            # If files can't be read, create minimal placeholders
            # This is just for testing, so we don't need real audio
            self.dummy_audio_bytes = b"DUMMY_AUDIO_CONTENT"
            self.silent_audio_bytes = b"SILENT_AUDIO_CONTENT"
            print(
                f"Warning: Could not read audio files, using placeholders. Error: {e}"
            )

        # Initialize rate limiter
        self.rate_limiter = threading.Semaphore(MAX_CONCURRENT_REQUESTS)

    def create_client(self) -> "DummyTTSClient":
        """Create and return a client for this backend."""
        return DummyTTSClient(self)


class DummyTTSClient:
    """
    Client for the dummy TTS backend.

    Simulates the behavior of a real TTS API client, including:
    - Generating audio with configurable delays
    - Rate limiting
    - Stateful operations like voice lookup
    """

    def __init__(self, backend: DummyTTSBackend):
        """Initialize the client with a reference to the backend."""
        self.backend = backend

    def generate_audio(
        self,
        text: str,
        request_time: Optional[float] = None,
        additional_delay: Optional[float] = None,
        generate_silent: bool = False,
    ) -> bytes:
        """
        Generate audio for the given text.

        Args:
            text: The text to convert to speech (will return dummy audio file regardless)
            request_time: Optional override for the base request time
            additional_delay: Optional additional delay to add to request time
            generate_silent: Whether to generate silent audio in place of dummy audio file

        Returns:
            bytes: The generated audio data
        """
        # Simulate rate limiting
        with self.backend.rate_limiter:
            # Calculate delay based on text length and optional overrides
            base_delay = (
                request_time
                if request_time is not None
                else self.backend.BASE_DELAY_SECONDS
            )
            char_delay = len(text) * self.backend.VARIABLE_DELAY_MS_PER_CHAR / 1000.0
            extra_delay = additional_delay if additional_delay is not None else 0.0

            total_delay = base_delay + char_delay + extra_delay

            # Simulate processing time
            time.sleep(total_delay)

            # Return the appropriate audio bytes
            if generate_silent:
                return self.backend.silent_audio_bytes
            else:
                return self.backend.dummy_audio_bytes

    def simulate_lookup_delay(self, is_new: bool) -> None:
        """
        Simulate a delay for looking up a voice ID.

        Args:
            is_new: Whether this is a new ID (which takes longer to process)
        """
        if is_new:
            time.sleep(self.backend.NEW_ID_LOOKUP_DELAY_SECONDS)
