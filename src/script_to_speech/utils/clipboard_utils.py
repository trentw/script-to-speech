"""Clipboard utility functions for script_to_speech.

Provides a single helper to copy arbitrary text to the system clipboard and log
basic statistics about the copied text.
"""

from typing import Optional

import pyperclip

from .logging import get_screenplay_logger

logger = get_screenplay_logger("utils.clipboard_utils")


def copy_text_to_clipboard(text: str, *, label: Optional[str] = None) -> None:
    """Copy text to the system clipboard and emit an INFO log entry.

    Args:
        text: The text to copy.
        label: Optional label for logging, e.g., the originating filename.

    Raises:
        RuntimeError: If ``pyperclip`` cannot find a suitable clipboard
            mechanism on the host system.
    """
    try:
        pyperclip.copy(text)
    except pyperclip.PyperclipException as exc:
        raise RuntimeError(f"Error copying to clipboard: {exc}") from exc

    label = label or "text"
    num_chars = len(text)
    num_lines = text.count("\n") + 1
    logger.info(
        'Copied "%s" to clipboard — %d chars, %d lines', label, num_chars, num_lines
    )
