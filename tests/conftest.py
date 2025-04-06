"""
Global pytest configuration file.
"""

import sys
from pathlib import Path

import pytest

# Add the project root directory to Python path so tests can import modules properly
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


def pytest_collection_modifyitems(items):
    """
    Automatically mark all tests as 'unit' unless they have an 'integration' or 'slow' marker.
    This allows running only unit tests with -m "unit" without manually decorating each test.
    """
    for item in items:
        # Skip tests that are already marked as integration or slow
        if any(marker in item.keywords for marker in ["integration", "slow"]):
            continue

        # Mark all other tests as unit tests
        item.add_marker(pytest.mark.unit)
