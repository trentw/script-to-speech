"""
CLI for running voice library scripts.
"""

import argparse
import importlib.util
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple

from .constants import REPO_VOICE_LIBRARY_SCRIPTS_PATH, USER_VOICE_LIBRARY_SCRIPTS_PATH


def find_scripts() -> Dict[str, Path]:
    """Finds all available voice library scripts."""
    scripts: Dict[str, Path] = {}

    # Find repo scripts first
    if REPO_VOICE_LIBRARY_SCRIPTS_PATH.is_dir():
        for path in REPO_VOICE_LIBRARY_SCRIPTS_PATH.iterdir():
            if path.is_dir() and (path / f"{path.name}.py").is_file():
                scripts[path.name] = path / f"{path.name}.py"
            elif path.is_file() and path.suffix == ".py":
                scripts[path.stem] = path

    # Find user scripts, overwriting repo scripts if names conflict
    if USER_VOICE_LIBRARY_SCRIPTS_PATH.is_dir():
        for path in USER_VOICE_LIBRARY_SCRIPTS_PATH.iterdir():
            if path.is_dir() and (path / f"{path.name}.py").is_file():
                scripts[path.name] = path / f"{path.name}.py"
            elif path.is_file() and path.suffix == ".py":
                scripts[path.stem] = path

    return scripts


def main() -> int:
    """Main entry point for running voice library scripts."""
    available_scripts = find_scripts()

    parser = argparse.ArgumentParser(
        description="Run a voice library script.",
        usage="sts-voice-library-run-script <script_name> [<args>].",
    )
    parser.add_argument(
        "script_name",
        choices=sorted(available_scripts.keys()),
        help="The name of the script to run.",
    )

    if len(sys.argv) < 2:
        parser.print_help()
        return 1

    script_name = sys.argv[1]
    if script_name not in available_scripts:
        parser.print_help()
        return 1

    script_path = available_scripts[script_name]

    try:
        spec = importlib.util.spec_from_file_location(script_name, script_path)
        if not spec or not spec.loader:
            raise ImportError(f"Could not create spec for module at {script_path}")

        script_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(script_module)

        if not hasattr(script_module, "get_argument_parser") or not hasattr(
            script_module, "run"
        ):
            print(
                f"Error: Script {script_name} does not conform to the required interface. Both `run` and `get_argument_parser` methods expected"
            )
            return 1

        # Get the script's own parser and parse the rest of the args
        script_parser = script_module.get_argument_parser()
        script_args = script_parser.parse_args(sys.argv[2:])

        # Run the script
        script_module.run(script_args)

    except Exception as e:
        print(f"Error running script {script_name}: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
