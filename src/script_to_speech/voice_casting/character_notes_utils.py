"""Utility functions for voice casting prompt generation."""

import tempfile
from pathlib import Path
from typing import Optional

import yaml

from script_to_speech.parser.utils.text_utils import extract_text_preserving_whitespace

from .voice_casting_common import read_prompt_file

DEFAULT_PROMPT_FILENAME = "default_character_notes_prompt.txt"


def generate_voice_casting_prompt_file(
    source_screenplay_path: Path,
    tts_provider_config_path: Path,
    prompt_file_path: Optional[Path] = None,
) -> Path:
    """
    Generates a text file to be used as a prompt for an LLM to assist with voice casting.

    The output file will contain:
    1. A prompt description (either from the provided `prompt_file_path` or a default).
    2. A header and the content of the `tts_provider_config_path` YAML file.
    3. A header and the text content of the `source_screenplay_path` (PDF or TXT).

    Args:
        source_screenplay_path: Path to the source screenplay file (.txt or .pdf).
        tts_provider_config_path: Path to the TTS provider configuration YAML file.
        prompt_file_path: Optional path to a custom prompt text file. If None,
                          a default prompt will be used.

    Returns:
        The Path object of the generated output file.

    Raises:
        FileNotFoundError: If any of the required input files are not found.
        ValueError: If the screenplay file type is unsupported or if paths are invalid.
        yaml.YAMLError: If the TTS provider config file is not valid YAML.
    """
    # Validate input paths
    if not source_screenplay_path.is_file():
        raise FileNotFoundError(
            f"Source screenplay file not found: {source_screenplay_path}"
        )
    if not tts_provider_config_path.is_file():
        raise FileNotFoundError(
            f"TTS provider config file not found: {tts_provider_config_path}"
        )
    if prompt_file_path and not prompt_file_path.is_file():
        raise FileNotFoundError(f"Custom prompt file not found: {prompt_file_path}")

    # Determine screenplay name and output directory
    # Use source file's parent directory - this is already the correct workspace location
    screenplay_name = source_screenplay_path.stem
    input_dir = source_screenplay_path.parent

    # Determine output file path
    output_file_name = f"{screenplay_name}_character_notes_prompt.txt"
    output_file_path = input_dir / output_file_name

    # 1. Read Prompt Content using shared function
    prompt_content = read_prompt_file(
        prompt_file_path=prompt_file_path,
        default_filename=DEFAULT_PROMPT_FILENAME,
        parent_dir=Path(__file__).parent,
    )

    # 2. Read TTS Provider Config
    try:
        with open(tts_provider_config_path, "r", encoding="utf-8") as f:
            # We just need the text dump, not to parse it as YAML for this function
            tts_provider_config_content = f.read()
    except Exception as e:
        raise yaml.YAMLError(
            f"Error reading TTS provider config file {tts_provider_config_path}: {e}"
        )

    # 3. Read/Extract Screenplay Text
    screenplay_text_processed_lines = []
    file_extension = source_screenplay_path.suffix.lower()

    if file_extension == ".pdf":
        # extract_text_preserving_whitespace writes to a file and returns the text.
        # We need a temporary file for its output_file argument.
        with tempfile.NamedTemporaryFile(
            mode="w+", delete=False, suffix=".txt", encoding="utf-8"
        ) as tmp_pdf_text_out:
            try:
                extracted_text = extract_text_preserving_whitespace(
                    pdf_path=str(source_screenplay_path),
                    output_file=tmp_pdf_text_out.name,
                )
                raw_screenplay_text = extracted_text
            finally:
                # Ensure temporary file is cleaned up
                Path(tmp_pdf_text_out.name).unlink(missing_ok=True)

        screenplay_text_processed_lines = [
            line.strip() for line in raw_screenplay_text.splitlines()
        ]

    elif file_extension == ".txt":
        with open(source_screenplay_path, "r", encoding="utf-8") as f:
            raw_screenplay_text = f.read()
        screenplay_text_processed_lines = [
            line.strip() for line in raw_screenplay_text.splitlines()
        ]
    else:
        raise ValueError(
            f"Unsupported screenplay file type: {file_extension}. Please use .txt or .pdf."
        )

    processed_screenplay_text = "\n".join(screenplay_text_processed_lines)

    # 4. Assemble Output Content
    output_content_parts = [
        prompt_content,
        "\n\n--- TTS PROVIDER CONFIG ---\n\n",
        tts_provider_config_content,
        "\n\n--- SCREENPLAY TEXT ---\n\n",
        processed_screenplay_text,
    ]
    final_output_content = "".join(output_content_parts)

    # 5. Write Output File
    with open(output_file_path, "w", encoding="utf-8") as f:
        f.write(final_output_content)

    return output_file_path
