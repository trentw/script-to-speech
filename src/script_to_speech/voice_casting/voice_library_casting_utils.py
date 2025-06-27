"""Utility functions for voice library casting prompt generation."""

from pathlib import Path
from typing import List, Optional

import yaml

from .voice_casting_common import read_prompt_file

DEFAULT_VOICE_LIBRARY_PROMPT_FILENAME = "default_voice_library_casting_prompt.txt"


def generate_voice_library_casting_prompt_file(
    voice_config_path: Path,
    providers: List[str],
    prompt_file_path: Optional[Path] = None,
    output_file_path: Optional[Path] = None,
) -> Path:
    """
    Generates a text file to be used as a prompt for an LLM to assist with voice casting
    using voice library data.

    The output file will contain:
    1. A prompt description (either from the provided `prompt_file_path` or a default).
    2. A header and the voice library schema for reference.
    3. A header and the content of the `voice_config_path` YAML file.
    4. Headers and voice library data for each specified provider.

    Args:
        voice_config_path: Path to the voice configuration YAML file.
        providers: List of provider names to include voice library data for.
        prompt_file_path: Optional path to a custom prompt text file. If None,
                          a default prompt will be used.
        output_file_path: Optional path for the output file. If None, will be generated
                         based on the voice config file name.

    Returns:
        The Path object of the generated output file.

    Raises:
        FileNotFoundError: If any of the required input files are not found.
        ValueError: If provider voice library files are not found or paths are invalid.
        yaml.YAMLError: If the voice config file is not valid YAML.
    """
    # Validate input paths
    if not voice_config_path.is_file():
        raise FileNotFoundError(f"Voice config file not found: {voice_config_path}")
    if prompt_file_path and not prompt_file_path.is_file():
        raise FileNotFoundError(f"Custom prompt file not found: {prompt_file_path}")

    # Determine output file path
    if output_file_path is None:
        config_name = voice_config_path.stem
        output_dir = voice_config_path.parent
        output_file_name = f"{config_name}_voice_library_casting_prompt.txt"
        output_file_path = output_dir / output_file_name

    # 1. Read Prompt Content using shared function
    prompt_content = read_prompt_file(
        prompt_file_path=prompt_file_path,
        default_filename=DEFAULT_VOICE_LIBRARY_PROMPT_FILENAME,
        parent_dir=Path(__file__).parent,
    )

    # 2. Read Voice Configuration
    try:
        with open(voice_config_path, "r", encoding="utf-8") as f:
            voice_config_content = f.read()
    except Exception as e:
        raise yaml.YAMLError(
            f"Error reading voice config file {voice_config_path}: {e}"
        )

    # 3. Read Voice Library Schema
    voice_library_data_dir = (
        Path(__file__).parent.parent / "voice_library" / "voice_library_data"
    )
    schema_file = voice_library_data_dir / "voice_library_schema.yaml"

    if not schema_file.is_file():
        raise FileNotFoundError(f"Voice library schema file not found: {schema_file}")

    try:
        with open(schema_file, "r", encoding="utf-8") as f:
            schema_content = f.read()
    except Exception as e:
        raise ValueError(f"Error reading voice library schema file: {e}")

    # 4. Read Voice Library Data for Each Provider
    provider_contents = {}

    for provider in providers:
        provider_voices_file = voice_library_data_dir / provider / "voices.yaml"
        if not provider_voices_file.is_file():
            raise FileNotFoundError(
                f"Voice library file not found for provider '{provider}': {provider_voices_file}"
            )

        try:
            with open(provider_voices_file, "r", encoding="utf-8") as f:
                provider_contents[provider] = f.read()
        except Exception as e:
            raise ValueError(
                f"Error reading voice library file for provider '{provider}': {e}"
            )

    # 5. Assemble Output Content
    output_content_parts = [prompt_content]

    output_content_parts.extend(
        [
            "\n\n--- VOICE LIBRARY SCHEMA ---\n\n",
            schema_content,
            "\n\n--- VOICE CONFIGURATION ---\n\n",
            voice_config_content,
        ]
    )

    for provider in providers:
        provider_header = f"\n\n--- VOICE LIBRARY DATA ({provider.upper()}) ---\n\n"
        output_content_parts.extend(
            [
                provider_header,
                provider_contents[provider],
            ]
        )

    final_output_content = "".join(output_content_parts)

    # 6. Write Output File
    output_file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file_path, "w", encoding="utf-8") as f:
        f.write(final_output_content)

    return output_file_path
