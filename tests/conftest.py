"""
Global pytest configuration file.
"""

import sys
from pathlib import Path

# Add the project root directory to Python path so tests can import modules properly
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
