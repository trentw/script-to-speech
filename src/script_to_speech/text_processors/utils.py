import os
from typing import List, Optional

# Default processor configuration path
DEFAULT_PROCESSOR_CONFIG = (
    "src/script_to_speech/text_processors/configs/default_processor_config.yaml"
)


def get_processor_configs(
    chunk_file_path: Optional[str] = None, cmd_line_configs: Optional[List[str]] = None
) -> List[str]:
    """
    Generate a list of processor config paths based on input parameters.

    Args:
        chunk_file_path: Optional path to the .json chunk file
        cmd_line_configs: Optional list of config paths from command line arguments

    Returns:
        List[str]: Array of config file paths to use

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

    # Check for matching config file
    chunk_dir = os.path.dirname(chunk_file_path)
    chunk_name = os.path.splitext(os.path.basename(chunk_file_path))[0]
    custom_config = os.path.join(chunk_dir, f"{chunk_name}_processor_config.yaml")

    # If matching config exists, return default + custom
    if os.path.exists(custom_config):
        return [DEFAULT_PROCESSOR_CONFIG, custom_config]

    # Otherwise return default only
    return [DEFAULT_PROCESSOR_CONFIG]
