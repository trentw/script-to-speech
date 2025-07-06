"""
Main script to fetch available voices from a TTS provider and generate a configuration file.
"""

import argparse
import importlib.util
import sys
from pathlib import Path
from typing import Any, Dict

import yaml

from script_to_speech.voice_library.constants import USER_CONFIG_PATH
from script_to_speech.voice_library.voice_library_script_utils import (
    find_provider_specific_file,
)


def get_argument_parser() -> argparse.ArgumentParser:
    """Creates and returns the argument parser for this script."""
    parser = argparse.ArgumentParser(
        description="Fetch available voices from a provider and create a config file."
    )
    parser.add_argument("provider", help="The TTS provider to fetch voices from.")
    parser.add_argument(
        "--file_name",
        help="Optional: The base name of the output YAML file.",
        default=None,
    )
    return parser


def run(args: argparse.Namespace) -> None:
    """Main execution function for the script."""
    provider = args.provider
    file_name = args.file_name
    if file_name is None:
        file_name = f"{provider}_fetched_voices.yaml"
    elif not (file_name.endswith(".yaml") or file_name.endswith(".yml")):
        file_name += ".yaml"

    fetcher_path = find_provider_specific_file(
        "fetch_available_voices", provider, "fetch_provider_voices.py"
    )

    if not fetcher_path:
        print(f"No voice fetching script found for provider: {provider}")
        return

    try:
        spec = importlib.util.spec_from_file_location("provider_fetcher", fetcher_path)
        if spec and spec.loader:
            provider_fetcher = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(provider_fetcher)
            voices = provider_fetcher.fetch_voices()
        else:
            raise ImportError(f"Could not load module from {fetcher_path}")
    except Exception as e:
        print(f"Error loading or running provider script {fetcher_path}: {e}")
        return

    output_data: Dict[str, Any] = {"included_sts_ids": {provider: voices}}

    output_dir = USER_CONFIG_PATH
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / file_name

    if output_file.exists():
        print(f"File {output_file} already exists. Overwriting.")

    with open(output_file, "w") as f:
        yaml.dump(output_data, f, default_flow_style=False, sort_keys=False)

    print(f"Successfully wrote voice list to {output_file}")


if __name__ == "__main__":
    parser = get_argument_parser()
    args = parser.parse_args()
    run(args)
