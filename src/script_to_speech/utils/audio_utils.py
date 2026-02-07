import io
import logging
import os
import subprocess
import sys
import tempfile
from typing import Optional

from pydub import AudioSegment
from pydub.silence import detect_silence

# Create a logger for this module
logger = logging.getLogger(__name__)


def _patch_pydub_for_windows() -> None:
    """
    Patch pydub's subprocess calls on Windows to prevent console windows
    and handle the lack of stdin/stdout/stderr in PyInstaller --noconsole builds.

    When PyInstaller bundles an app with --noconsole, there's no stdin/stdout/stderr.
    Subprocess calls that try to inherit these handles will hang or fail with
    "OSError [Error 6] the handle is invalid".

    This patch adds STARTUPINFO with STARTF_USESHOWWINDOW to hide console windows
    and ensures stdin is always PIPE (never None) to prevent hangs.

    See: https://github.com/jiaaro/pydub/issues/586
    See: https://github.com/jiaaro/pydub/issues/698
    See: https://github.com/pyinstaller/pyinstaller/wiki/Recipe-subprocess
    """
    import pydub.audio_segment
    import pydub.utils

    class _WindowsNoConsolePopen(subprocess.Popen):  # type: ignore[type-arg]
        def __init__(self, *args: object, **kwargs: object) -> None:
            # Add STARTUPINFO to hide console window
            if "startupinfo" not in kwargs:
                si = subprocess.STARTUPINFO()  # type: ignore[attr-defined]
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW  # type: ignore[attr-defined]
                kwargs["startupinfo"] = si

            # Ensure stdin is not None (causes hangs in --noconsole builds)
            if kwargs.get("stdin") is None:
                kwargs["stdin"] = subprocess.PIPE

            super().__init__(*args, **kwargs)  # type: ignore[call-overload]

    # Patch pydub.audio_segment which uses `import subprocess` then subprocess.Popen()
    pydub.audio_segment.subprocess.Popen = _WindowsNoConsolePopen  # type: ignore[assignment]

    # Patch pydub.utils which uses `from subprocess import Popen` directly
    pydub.utils.Popen = _WindowsNoConsolePopen  # type: ignore[attr-defined]

    logger.info("Patched pydub subprocess for Windows compatibility")


def configure_ffmpeg() -> None:
    """
    Configure the ffmpeg binary path for pydub using static-ffmpeg.

    This function will:
    1. Use static-ffmpeg to get ffmpeg and ffprobe binaries
    2. Configure pydub to use these binaries
    3. Verify that ffmpeg works correctly

    Raises:
        ImportError: If static-ffmpeg is not installed
        RuntimeError: If ffmpeg verification fails
    """
    # Apply Windows-specific pydub patch before any pydub operations
    if sys.platform == "win32":
        _patch_pydub_for_windows()

    try:
        import static_ffmpeg
        from static_ffmpeg import run

        logger.info("Using static-ffmpeg for ffmpeg binaries")

        # Get the ffmpeg and ffprobe binaries
        ffmpeg_executable, ffprobe_executable = (
            run.get_or_fetch_platform_executables_else_raise()
        )

        # Add to system PATH (for subprocesses that might need it)
        ffmpeg_dir = os.path.dirname(ffmpeg_executable)
        path_separator = ";" if sys.platform == "win32" else ":"
        os.environ["PATH"] = f"{ffmpeg_dir}{path_separator}{os.environ.get('PATH', '')}"

        # Configure pydub with explicit paths
        AudioSegment.converter = ffmpeg_executable
        AudioSegment.ffmpeg = ffmpeg_executable
        AudioSegment.ffprobe = ffprobe_executable

        logger.info(f"static-ffmpeg binaries located at: {ffmpeg_dir}")
        logger.info(f"ffmpeg: {ffmpeg_executable}")
        logger.info(f"ffprobe: {ffprobe_executable}")

        # Verify ffmpeg works
        try:
            test_file = AudioSegment.silent(duration=1)
            # Use delete=False because Windows doesn't allow writing to an open temp file
            tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            tmp_path = tmp.name
            tmp.close()
            try:
                test_file.export(tmp_path, format="mp3")
            finally:
                os.remove(tmp_path)
            logger.info("FFMPEG verification successful")
        except Exception as e:
            raise RuntimeError(f"Failed to verify ffmpeg installation: {e}") from e

    except ImportError:
        raise ImportError(
            "static-ffmpeg is required but not installed. "
            "Please install it with: pip install static-ffmpeg"
        )


def split_audio_on_silence(
    audio_data: bytes,
    min_silence_len: int = 350,  # minimum silence length in ms
    silence_thresh: int = -20,  # silence threshold in dBFS
    keep_silence: int = 700,  # amount of silence to keep in ms
) -> Optional[AudioSegment]:
    """
    Split audio on the first detected silence and return the second part.
    Designed for audio files with format: short sentence, pause, variable audio.

    Args:
        audio_data: Raw audio data in bytes
        min_silence_len: Minimum length of silence to detect (in milliseconds)
        silence_thresh: Silence threshold in dBFS (lower = stricter silence detection)
        keep_silence: Amount of silence to keep around splits (in milliseconds)

    Returns:
        Optional[AudioSegment]: The second part of the audio after the first silence,
                               or None if no silence was detected or other error occurred

    Raises:
        ValueError: If audio_data is empty or invalid
        RuntimeError: If audio processing fails
    """
    if not audio_data:
        raise ValueError("Empty audio data provided")

    try:
        # Load audio from bytes
        audio = AudioSegment.from_mp3(io.BytesIO(audio_data))

        # Detect silence ranges
        silence_ranges = detect_silence(
            audio,
            min_silence_len=min_silence_len,
            silence_thresh=silence_thresh,
            seek_step=1,
        )

        # If no silence detected, return None
        if not silence_ranges:
            return None

        # Get the first silence range
        first_silence = silence_ranges[0]

        # Calculate split point (end of first silence)
        split_point = first_silence[1] - keep_silence

        # Return everything after the split point
        if split_point < len(audio):
            return audio[split_point:]

        return None

    except Exception as e:
        raise RuntimeError(f"Failed to process audio: {str(e)}") from e


def export_audio_segment(
    audio_segment: AudioSegment, output_path: str, format: str = "mp3"
) -> None:
    """
    Export an audio segment to a file with proper error handling.

    Args:
        audio_segment: The AudioSegment to export
        output_path: Path where the audio file should be saved
        format: Output format (default: "mp3")

    Raises:
        ValueError: If audio_segment is None or output_path is empty
        RuntimeError: If export fails
    """
    if audio_segment is None:
        raise ValueError("No audio segment provided")
    if not output_path:
        raise ValueError("No output path provided")

    try:
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Export the audio
        audio_segment.export(output_path, format=format)

        # Verify the file was created
        if not os.path.exists(output_path):
            raise RuntimeError("Export completed but file was not created")

    except Exception as e:
        raise RuntimeError(f"Failed to export audio: {str(e)}") from e
