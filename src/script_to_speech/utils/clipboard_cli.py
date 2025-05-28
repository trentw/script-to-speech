"""CLI wrapper to copy the full contents of a file to the system clipboard.

Usage:
    sts-copy-to-clipboard <file_path>

The entry point is wired up in pyproject.toml as:
    sts-copy-to-clipboard = "script_to_speech.utils.clipboard_cli:main"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .clipboard_utils import copy_text_to_clipboard


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Copy a file’s contents to the system clipboard.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("file", type=Path, help="Path to the file to copy")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    try:
        text = args.file.read_text(encoding="utf-8")
    except Exception as exc:
        print(f"[ERROR] Cannot read {args.file}: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        copy_text_to_clipboard(text, label=args.file.name)
    except RuntimeError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        print(
            "\nNote: Clipboard access requires a desktop environment.", file=sys.stderr
        )
        print(
            f"You can view the file contents with: cat '{args.file}'", file=sys.stderr
        )
        print(
            f"Or copy it locally with: cat '{args.file}' | pbcopy (macOS) or xclip (Linux)",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
