import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

def create_default_config() -> Dict[str, Any]:
    """
    Create a default optional configuration dictionary.
    
    Returns:
        Default configuration dictionary
    """
    return {
        "id3_tag_config": {
            "title": "",
            "screenplay_author": "",
            "date": ""
        }
    }

def write_config_file(config_path: str, config: Dict[str, Any]) -> None:
    """
    Write a configuration dictionary to a file.
    
    Args:
        config_path: Path to write the configuration file
        config: Configuration dictionary to write
    """
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

def get_optional_config_path(json_path: str) -> str:
    """
    Get the path for an optional configuration file based on a JSON file path.
    
    Args:
        json_path: Path to the JSON file
        
    Returns:
        Path to the optional configuration file
    """
    json_path_obj = Path(json_path)
    base_name = json_path_obj.stem
    parent_dir = json_path_obj.parent
    
    config_filename = f"{base_name}_optional_config.yaml"
    config_path = parent_dir / config_filename
    
    return str(config_path)

def generate_optional_config(json_path: str) -> str:
    """
    Generate an optional configuration file for a screenplay JSON file.
    The file will be named [json_filename]_optional_config.yaml and placed in the same directory.
    If the file already exists, it will not be overwritten.
    
    Args:
        json_path: Path to the JSON file
        
    Returns:
        Path to the generated or existing config file
    """
    config_path = get_optional_config_path(json_path)
    
    # Check if the file already exists
    if os.path.exists(config_path):
        return config_path
    
    # Create and write default configuration
    config = create_default_config()
    write_config_file(config_path, config)
    
    return config_path