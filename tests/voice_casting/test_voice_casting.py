import sys
from pathlib import Path

import pytest

from script_to_speech.voice_casting import character_notes_cli
from script_to_speech.voice_casting.character_notes_utils import (
    generate_voice_casting_prompt_file,
)


def test_generate_prompt_file_txt(tmp_path: Path):
    # Arrange
    screenplay_path = tmp_path / "sample_screenplay.txt"
    screenplay_path.write_text("CHARACTER: Hello World\n")
    config_path = tmp_path / "tts_provider_config.yaml"
    config_path.write_text("provider: dummy\n")

    # Act
    output_path = generate_voice_casting_prompt_file(
        source_screenplay_path=screenplay_path,
        tts_provider_config_path=config_path,
        prompt_file_path=None,
    )

    # Assert
    assert output_path.exists()
    content = output_path.read_text()
    assert "--- TTS PROVIDER CONFIG ---" in content
    assert "--- SCREENPLAY TEXT ---" in content
    assert "CHARACTER: Hello World" in content


def test_generate_prompt_file_invalid_extension(tmp_path: Path):
    screenplay_path = tmp_path / "sample_screenplay.doc"
    screenplay_path.write_text("dummy")
    config_path = tmp_path / "tts_provider_config.yaml"
    config_path.write_text("provider: dummy\n")

    with pytest.raises(ValueError):
        generate_voice_casting_prompt_file(
            source_screenplay_path=screenplay_path,
            tts_provider_config_path=config_path,
            prompt_file_path=None,
        )


def test_cli_success(monkeypatch, tmp_path, capsys):
    # Arrange
    screenplay_path = tmp_path / "s.txt"
    screenplay_path.write_text("hi")
    config_path = tmp_path / "c.yaml"
    config_path.write_text("provider: dummy")
    dummy_output = tmp_path / "input" / "s" / "s_voice_casting_prompt.txt"
    dummy_output.parent.mkdir(parents=True, exist_ok=True)
    dummy_output.write_text("content")

    def fake_generate(*args, **kwargs):
        return dummy_output

    monkeypatch.setattr(
        character_notes_cli, "generate_voice_casting_prompt_file", fake_generate
    )
    test_args = [
        "prog",
        str(screenplay_path),
        str(config_path),
    ]
    monkeypatch.setattr(sys, "argv", test_args)

    # Act
    character_notes_cli.main()
    captured = capsys.readouterr()

    # Assert
    assert "Successfully generated voice casting prompt file" in captured.out
    assert str(dummy_output.resolve()) in captured.out


def test_cli_file_not_found(monkeypatch, tmp_path):
    # Arrange
    screenplay_path = tmp_path / "missing.txt"
    config_path = tmp_path / "c.yaml"
    config_path.write_text("provider: dummy")

    def fake_generate(*args, **kwargs):
        raise FileNotFoundError("missing file")

    monkeypatch.setattr(
        character_notes_cli, "generate_voice_casting_prompt_file", fake_generate
    )
    test_args = [
        "prog",
        str(screenplay_path),
        str(config_path),
    ]
    monkeypatch.setattr(sys, "argv", test_args)

    # Act / Assert
    with pytest.raises(SystemExit) as e:
        character_notes_cli.main()
    assert e.value.code == 1
