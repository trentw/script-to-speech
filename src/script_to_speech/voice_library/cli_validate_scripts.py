"""
CLI for validating voice library scripts.
"""

import argparse
import importlib.util
from pathlib import Path

from .constants import REPO_VOICE_LIBRARY_SCRIPTS_PATH, USER_VOICE_LIBRARY_SCRIPTS_PATH


def validate_scripts(project_only: bool = False) -> bool:
    """Validates all available voice library scripts."""
    all_valid = True
    script_names = set()

    def _validate_dir(path: Path, is_user: bool) -> None:
        nonlocal all_valid
        if not path.is_dir():
            return

        for item in path.iterdir():
            script_name = ""
            is_valid_script = False

            if item.is_dir() and (item / f"{item.name}.py").is_file():
                script_name = item.name
                script_path = item / f"{item.name}.py"
                is_valid_script = True
            elif item.is_file() and item.suffix == ".py" and item.stem != "__init__":
                script_name = item.stem
                script_path = item
                is_valid_script = True

            if not is_valid_script:
                continue

            if script_name in script_names:
                print(f"Error: Duplicate script name '{script_name}' found.")
                all_valid = False
            script_names.add(script_name)

            try:
                spec = importlib.util.spec_from_file_location(script_name, script_path)
                if not spec or not spec.loader:
                    raise ImportError()
                script_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(script_module)

                if not hasattr(script_module, "get_argument_parser") or not hasattr(
                    script_module, "run"
                ):
                    print(
                        f"Error: Script '{script_name}' does not have get_argument_parser() and run() functions."
                    )
                    all_valid = False
            except Exception as e:
                print(f"Error loading script '{script_name}': {e}")
                all_valid = False

    _validate_dir(REPO_VOICE_LIBRARY_SCRIPTS_PATH, is_user=False)
    if not project_only:
        _validate_dir(USER_VOICE_LIBRARY_SCRIPTS_PATH, is_user=True)

    return all_valid


def main() -> int:
    """Main entry point for validating voice library scripts."""
    parser = argparse.ArgumentParser(description="Validate voice library scripts.")
    parser.add_argument(
        "--project-only",
        action="store_true",
        help="Only validate scripts within the project source code.",
    )
    args = parser.parse_args()

    if validate_scripts(args.project_only):
        print("All voice library scripts are valid.")
        return 0
    else:
        print("Voice library script validation failed.")
        return 1


if __name__ == "__main__":
    exit(main())
