#!/usr/bin/env python3
"""Check that all version files are in sync.

Reads the version from pyproject.toml (source of truth) and verifies
all other version files match. Exits with code 1 if any mismatch is found.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

VERSION_FILES = {
    "pyproject.toml": (
        re.compile(r'^version\s*=\s*"([^"]+)"', re.MULTILINE),
        ROOT / "pyproject.toml",
    ),
    "_version.py": (
        re.compile(r'^__version__\s*=\s*"([^"]+)"', re.MULTILINE),
        ROOT / "src" / "script_to_speech" / "_version.py",
    ),
    "tauri.conf.json": (
        None,  # JSON parsing
        ROOT / "gui" / "frontend" / "src-tauri" / "tauri.conf.json",
    ),
    "Cargo.toml": (
        re.compile(r'^version\s*=\s*"([^"]+)"', re.MULTILINE),
        ROOT / "gui" / "frontend" / "src-tauri" / "Cargo.toml",
    ),
    "package.json": (
        None,  # JSON parsing
        ROOT / "gui" / "frontend" / "package.json",
    ),
}


def get_version(name: str, pattern, path: Path) -> str | None:
    if not path.exists():
        return None
    content = path.read_text()
    if pattern is None:
        data = json.loads(content)
        return data.get("version")
    match = pattern.search(content)
    return match.group(1) if match else None


def main() -> int:
    versions: dict[str, str | None] = {}
    for name, (pattern, path) in VERSION_FILES.items():
        versions[name] = get_version(name, pattern, path)

    source = versions["pyproject.toml"]
    if source is None:
        print("ERROR: Could not read version from pyproject.toml")
        return 1

    ok = True
    for name, version in versions.items():
        status = "OK" if version == source else "MISMATCH"
        if version != source:
            ok = False
        print(f"  {name:20s} {version or 'NOT FOUND':>10s}  {status}")

    if ok:
        print(f"\nAll versions in sync: {source}")
    else:
        print(f"\nExpected all versions to be: {source}")
        print("Run: uv run bump-my-version bump --new-version <version> patch")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
