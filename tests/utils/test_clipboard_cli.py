import sys
import tempfile
from unittest import mock

import pytest

from src.script_to_speech.utils import clipboard_cli


def test_main_success(monkeypatch):
    # Arrange
    with tempfile.NamedTemporaryFile("w+", encoding="utf-8", delete=False) as tmp:
        tmp.write("abc\ndef")
        tmp.flush()
        file_path = tmp.name

    monkeypatch.setattr(sys, "argv", ["sts-copy-to-clipboard", file_path])
    mock_copy = mock.Mock()
    monkeypatch.setattr(
        "src.script_to_speech.utils.clipboard_cli.copy_text_to_clipboard", mock_copy
    )

    # Act
    clipboard_cli.main()

    # Assert
    mock_copy.assert_called_once()
    args, kwargs = mock_copy.call_args
    assert args[0] == "abc\ndef"
    assert kwargs["label"] in file_path


def test_main_file_not_found(monkeypatch, capsys):
    # Arrange
    fake_path = "/nonexistent/file.txt"
    monkeypatch.setattr(sys, "argv", ["sts-copy-to-clipboard", fake_path])

    # Act
    with pytest.raises(SystemExit) as excinfo:
        clipboard_cli.main()
    # Assert
    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "[ERROR]" in captured.err
    assert fake_path in captured.err


def test_main_clipboard_error(monkeypatch, tmp_path, capsys):
    # Arrange
    file_path = tmp_path / "file.txt"
    file_path.write_text("data", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["sts-copy-to-clipboard", str(file_path)])

    def fail_copy(*a, **kw):
        raise RuntimeError("no clipboard")

    monkeypatch.setattr(
        "src.script_to_speech.utils.clipboard_cli.copy_text_to_clipboard", fail_copy
    )

    # Act
    with pytest.raises(SystemExit) as excinfo:
        clipboard_cli.main()
    # Assert
    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "[ERROR]" in captured.err
    assert "no clipboard" in captured.err
