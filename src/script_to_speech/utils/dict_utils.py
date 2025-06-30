"""Dictionary utility functions."""

from typing import Any, Dict, List


def deep_merge(d1: Dict[str, Any], d2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively merges two dictionaries.

    - For keys where both values are lists, it merges the lists and removes duplicates.
    - For keys where both values are dictionaries, it merges them recursively.
    - Otherwise, the value from the second dictionary (d2) overwrites the first (d1).
    """
    merged = d1.copy()
    for key, value in d2.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = deep_merge(merged[key], value)
        elif (
            key in merged and isinstance(merged[key], list) and isinstance(value, list)
        ):
            # Create a new list to avoid modifying the original
            new_list = merged[key][:]
            new_list.extend(v for v in value if v not in new_list)
            merged[key] = new_list
        else:
            merged[key] = value
    return merged
