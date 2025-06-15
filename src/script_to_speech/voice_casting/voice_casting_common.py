"""Common utilities for voice casting CLI tools."""

import sys
import traceback
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Optional

import yaml


def handle_cli_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator for common CLI error handling.

    Handles FileNotFoundError, ValueError, yaml.YAMLError, and generic exceptions
    with appropriate error messages and exit codes.
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except FileNotFoundError as e:
            print(f"\nError: {e}", file=sys.stderr)
            sys.exit(1)
        except ValueError as e:
            print(f"\nError: {e}", file=sys.stderr)
            sys.exit(1)
        except yaml.YAMLError as e:
            print(f"\nError processing YAML: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"\nAn unexpected error occurred:", file=sys.stderr)
            traceback.print_exc()
            sys.exit(1)

    return wrapper


def read_prompt_file(
    prompt_file_path: Optional[Path], default_filename: str, parent_dir: Path
) -> str:
    """
    Read prompt content from a custom or default prompt file.

    Args:
        prompt_file_path: Optional custom prompt file path
        default_filename: Name of the default prompt file
        parent_dir: Directory where the default prompt file should be located

    Returns:
        The content of the prompt file

    Raises:
        FileNotFoundError: If neither custom nor default prompt file exists
    """
    if prompt_file_path:
        actual_prompt_file = prompt_file_path
    else:
        default_prompt_path = parent_dir / default_filename
        if default_prompt_path.is_file():
            actual_prompt_file = default_prompt_path
        else:
            raise FileNotFoundError(
                f"Default prompt file '{default_filename}' not found in {parent_dir}"
            )

    with open(actual_prompt_file, "r", encoding="utf-8") as f:
        return f.read()
