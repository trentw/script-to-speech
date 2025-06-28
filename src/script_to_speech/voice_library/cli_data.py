"""Command-line interface for voice library operations."""

import sys
from typing import Optional

from .validator import VoiceLibraryValidator


def validate_voice_libraries() -> int:
    """
    Validate all voice library files.

    Returns:
        0 if valid, 1 if errors found
    """
    print("Validating voice library files...")

    validator = VoiceLibraryValidator()
    is_valid, errors = validator.validate_all()

    if is_valid:
        print("✓ All voice library files are valid!")
        return 0
    else:
        print(f"\n❌ Found {len(errors)} voice library validation error(s):\n")
        for error in errors:
            print(f"  • {error}")
        return 1


def main() -> None:
    """Main entry point for sts-validate-voice-libraries command."""
    sys.exit(validate_voice_libraries())
