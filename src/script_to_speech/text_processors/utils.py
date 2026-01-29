import sys
from pathlib import Path
from typing import List, Optional


def _get_default_text_processor_config() -> Path:
    """Get the path to the default text processor config.

    Handles both development and PyInstaller frozen builds.
    Uses sys.frozen (not --production flag) because this may be called from
    multiprocessing workers where sys.argv doesn't persist on macOS.
    """
    if getattr(sys, "frozen", False):
        # Running as PyInstaller bundle - files are in sys._MEIPASS
        # The spec file bundles configs to: script_to_speech/text_processors/configs/
        base_path = Path(getattr(sys, "_MEIPASS", "."))
        return (
            base_path
            / "script_to_speech"
            / "text_processors"
            / "configs"
            / "default_text_processor_config.yaml"
        )
    else:
        # Development mode - use relative path from project root
        return Path(
            "src/script_to_speech/text_processors/configs/default_text_processor_config.yaml"
        )


# Default processor configuration path
DEFAULT_TEXT_PROCESSOR_CONFIG = _get_default_text_processor_config()


def get_text_processor_configs(
    chunk_file_path: Optional[Path] = None,
    cmd_line_configs: Optional[List[Path]] = None,
) -> List[Path]:
    """
    Generate a list of processor config paths based on input parameters.

    Args:
        chunk_file_path: Optional Path to the .json chunk file
        cmd_line_configs: Optional list of config Paths from command line arguments

    Returns:
        List[Path]: Array of config file Paths to use

    Logic:
        - If command line configs are supplied, use only those
        - If chunk file exists and has matching config, use [DEFAULT_CONFIG, chunk_config]
        - Otherwise use [DEFAULT_CONFIG]
    """
    # If command line configs provided, use those exclusively
    if cmd_line_configs and len(cmd_line_configs) > 0:
        return cmd_line_configs

    # If no chunk file path, return default only
    if not chunk_file_path:
        return [DEFAULT_TEXT_PROCESSOR_CONFIG]

    # Check for matching config file using Path methods
    chunk_dir = chunk_file_path.parent
    chunk_name = chunk_file_path.stem
    custom_config = chunk_dir / f"{chunk_name}_text_processor_config.yaml"

    # If matching config exists, return default + custom
    if custom_config.exists():
        return [DEFAULT_TEXT_PROCESSOR_CONFIG, custom_config]

    # Otherwise return default only
    return [DEFAULT_TEXT_PROCESSOR_CONFIG]
