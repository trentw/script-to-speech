"""Command-line interface for voice library operations."""

import argparse
import sys
from typing import Optional

from .validator import VoiceLibraryValidator


def validate_voice_libraries(project_only: bool = False) -> int:
    """
    Validate voice library files.

    Args:
        project_only: If True, validate only project voice library.
                     If False, validate both project and user voice libraries.

    Returns:
        0 if valid, 1 if errors found
    """
    scope = "*project* voice library files" if project_only else "voice library files"
    print(f"Validating {scope}...")

    validator = VoiceLibraryValidator(project_only=project_only)
    is_valid, errors = validator.validate_all()

    if is_valid:
        print(f"✓ All {scope} are valid!")
        return 0
    else:
        print(f"\n❌ Found {len(errors)} voice library validation error(s):\n")
        for error in errors:
            print(f"  • {error}")
        return 1


def main() -> None:
    """Main entry point for sts-validate-voice-libraries command."""
    parser = argparse.ArgumentParser(description="Validate voice library YAML files")
    parser.add_argument(
        "--project-only",
        action="store_true",
        help="Validate only project voice library (not user voice library)",
    )

    args = parser.parse_args()
    sys.exit(validate_voice_libraries(project_only=args.project_only))
