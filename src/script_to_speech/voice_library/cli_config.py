"""CLI for validating voice library configurations."""

import sys

from .voice_library_config import (
    get_conflicting_ids,
    get_empty_include_lists,
    load_config,
)


def main() -> None:
    """Main validation function for the library config CLI."""
    print("Loading and validating voice library configurations...")
    config = load_config()

    if not config:
        print("No configuration files found. Nothing to validate.")
        sys.exit(0)
        return  # Ensure the function exits here

    conflicts = get_conflicting_ids(config)
    empty_includes = get_empty_include_lists(config)

    if conflicts:
        print(
            "\nValidation FAILED. Found conflicting IDs in include and exclude lists:"
        )
        for provider, ids in conflicts.items():
            print(f"  - Provider: {provider}")
            for an_id in ids:
                print(f"    - ID: {an_id}")
        sys.exit(1)
    elif empty_includes:
        print("\nValidation FAILED. Found providers with empty include_sts_ids lists:")
        for provider in empty_includes.keys():
            print(f"  - Provider: {provider}")
        sys.exit(1)
    else:
        print("\nValidation PASSED. No conflicts or empty include lists found.")
        sys.exit(0)


if __name__ == "__main__":
    main()
