"""Utility functions for voice library casting prompt generation."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml

from ..voice_library.schema_utils import load_merged_schemas_for_providers
from ..voice_library.voice_library import VoiceLibrary
from ..voice_library.voice_library_config import (
    get_additional_voice_casting_instructions,
    get_conflicting_ids,
    load_config,
)
from .voice_casting_common import read_prompt_file

DEFAULT_VOICE_LIBRARY_PROMPT_FILENAME = "default_voice_library_casting_prompt.txt"


def _filter_provider_voices(
    provider_name: str,
    provider_data: Dict[str, Any],
    config: Dict[str, Any],
) -> Dict[str, Any]:
    """Filters the voice library data for a provider based on include/exclude rules."""
    included_ids: Optional[List[str]] = config.get("included_sts_ids", {}).get(
        provider_name
    )
    excluded_ids: Set[str] = set(
        config.get("excluded_sts_ids", {}).get(provider_name, [])
    )

    voice_list = (
        provider_data.get("voices", {})
        if isinstance(provider_data, dict)
        else provider_data
    )
    if not voice_list:
        return {}

    # Start with included voices, or all voices if no include list is specified
    if included_ids is not None:
        filtered_voices = {
            sts_id: details
            for sts_id, details in voice_list.items()
            if sts_id in included_ids
        }
    else:
        filtered_voices = voice_list.copy()

    # Exclude voices from the result
    if excluded_ids:
        filtered_voices = {
            sts_id: details
            for sts_id, details in filtered_voices.items()
            if sts_id not in excluded_ids
        }

    # Reconstruct the original structure if necessary
    if isinstance(provider_data, dict) and "voices" in provider_data:
        provider_data["voices"] = filtered_voices
        return provider_data

    return filtered_voices


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
    4. Filtered voice library data for each specified provider based on `voice_library_config`.

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
        ValueError: If provider voice library files are not found or if there's a
                    configuration conflict.
        yaml.YAMLError: If the voice config file is not valid YAML.
    """
    # Load and validate voice library config
    voice_lib_config = load_config()
    conflicts = get_conflicting_ids(voice_lib_config)
    if conflicts:
        error_messages = [
            f"Provider '{provider}': Conflicting ID(s) {', '.join(ids)}"
            for provider, ids in conflicts.items()
        ]
        raise ValueError(
            "Validation FAILED. Found conflicting IDs in include and exclude lists:\n"
            + "\n".join(error_messages)
        )

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

    # 1. Read Prompt Content
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

    # 3. Load Merged Voice Library Schema (global + all provider schemas)
    try:
        merged_schema = load_merged_schemas_for_providers(providers)
        schema_content = yaml.dump(merged_schema, sort_keys=False, indent=2, width=1000)
    except ValueError as e:
        raise ValueError(f"Error loading voice library schema: {e}")
    except Exception as e:
        raise ValueError(f"Error processing voice library schema: {e}")

    # 4. Load and Filter Voice Library Data for Each Provider using VoiceLibrary class
    voice_library = VoiceLibrary()
    provider_contents = {}
    for provider in providers:
        try:
            # Load merged voice data (project + user, with user overrides)
            provider_voices = voice_library._load_provider_voices(provider)

            # Reconstruct the provider data structure for filtering
            provider_data = {"voices": provider_voices}

            # Apply filtering based on voice library config
            filtered_data = _filter_provider_voices(
                provider, provider_data, voice_lib_config
            )

            # Convert to YAML for output
            provider_contents[provider] = yaml.dump(
                filtered_data, sort_keys=False, indent=2, width=1000
            )
        except Exception as e:
            raise ValueError(
                f"Error processing voice library data for provider '{provider}': {e}"
            )

    # 5. Extract additional voice casting instructions
    additional_instructions = get_additional_voice_casting_instructions(
        voice_lib_config
    )

    # 6. Assemble Output Content
    output_content_parts = [
        prompt_content,
        "\n\n--- VOICE LIBRARY SCHEMA ---\n\n",
        schema_content,
        "\n\n--- VOICE CONFIGURATION ---\n\n",
        voice_config_content,
    ]

    for provider in providers:
        provider_header = f"\n\n--- VOICE LIBRARY DATA ({provider.upper()}) ---\n\n"
        output_content_parts.append(provider_header)

        # Add additional instructions if they exist for this provider
        if provider in additional_instructions:
            instructions_text = f"When casting for this provider ({provider}), please abide by the following instructions. These instructions are only for this provider:\n\n"
            for instruction in additional_instructions[provider]:
                instructions_text += f"- {instruction}\n"
            instructions_text += "\n"
            output_content_parts.append(instructions_text)

        output_content_parts.append(provider_contents[provider])

    final_output_content = "".join(output_content_parts)

    # 7. Write Output File
    output_file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file_path, "w", encoding="utf-8") as f:
        f.write(final_output_content)

    return output_file_path
