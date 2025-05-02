from pathlib import Path
from typing import List, Optional

# Default processor configuration path
DEFAULT_PROCESSOR_CONFIG = Path(
    "src/script_to_speech/text_processors/configs/default_processor_config.yaml"
)


def get_processor_configs(
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
        return [DEFAULT_PROCESSOR_CONFIG]

    # Check for matching config file using Path methods
    chunk_dir = chunk_file_path.parent
    chunk_name = chunk_file_path.stem
    custom_config = chunk_dir / f"{chunk_name}_processor_config.yaml"

    # If matching config exists, return default + custom
    if custom_config.exists():
        return [DEFAULT_PROCESSOR_CONFIG, custom_config]

    # Otherwise return default only
    return [DEFAULT_PROCESSOR_CONFIG]
