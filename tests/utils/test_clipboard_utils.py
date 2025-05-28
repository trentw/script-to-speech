from unittest import mock

import pyperclip
import pytest

from src.script_to_speech.utils import clipboard_utils


def test_copy_text_to_clipboard_success():
    # Arrange
    text = "hello\nworld"
    label = "myfile.txt"
    with (
        mock.patch(
            "src.script_to_speech.utils.clipboard_utils.pyperclip.copy"
        ) as mock_copy,
        mock.patch.object(clipboard_utils, "logger") as mock_log,
    ):
        # Act
        clipboard_utils.copy_text_to_clipboard(text, label=label)
        # Assert
        mock_copy.assert_called_once_with(text)
        mock_log.info.assert_called_once()
        args, kwargs = mock_log.info.call_args
        assert label == args[1]  # log message contains label as the second argument
        assert "char" in args[0]  # log message mentions chars
        assert "line" in args[0]  # log message mentions lines


def test_copy_text_to_clipboard_raises_on_pyperclip_error():
    # Arrange
    text = "fail"
    with mock.patch(
        "src.script_to_speech.utils.clipboard_utils.pyperclip.copy",
        side_effect=pyperclip.PyperclipException("no clipboard"),
    ):
        # Act & Assert
        with pytest.raises(RuntimeError):
            clipboard_utils.copy_text_to_clipboard(text)
