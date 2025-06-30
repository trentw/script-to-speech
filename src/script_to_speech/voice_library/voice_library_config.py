"""
Module for handling voice library configurations.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Set, Union

import yaml

from ..utils.dict_utils import deep_merge
from .constants import REPO_CONFIG_PATH, USER_CONFIG_PATH


def find_yaml_files(directory: Path) -> List[Path]:
    """Finds all .yaml or .yml files in a directory, including subdirectories."""
    if not directory.is_dir():
        return []
    return list(directory.rglob("*.yaml")) + list(directory.rglob("*.yml"))


def load_config() -> Dict[str, Any]:
    """
    Loads voice library configurations from repo and user paths and merges them.

    1. Finds all YAML files in REPO_CONFIG_PATH.
    2. Finds all YAML files in USER_CONFIG_PATH.
    3. Merges repo configs first, then merges user configs on top.
    """
    all_config_files = find_yaml_files(REPO_CONFIG_PATH) + find_yaml_files(
        USER_CONFIG_PATH
    )

    if not all_config_files:
        return {}

    merged_config: Dict[str, Any] = {}
    for file_path in all_config_files:
        try:
            with open(file_path, "r") as f:
                config_data = yaml.safe_load(f)
                if config_data:  # Ensure file is not empty
                    merged_config = deep_merge(merged_config, config_data)
        except yaml.YAMLError as e:
            print(f"Warning: Could not parse YAML file {file_path}. Error: {e}")
            continue

    return merged_config


def get_conflicting_ids(config: Dict[str, Any]) -> Dict[str, Set[str]]:
    """
    Finds conflicting sts_ids that are in both include and exclude lists for a provider.
    """
    conflicts: Dict[str, Set[str]] = {}
    included_ids = config.get("included_sts_ids", {})
    excluded_ids = config.get("excluded_sts_ids", {})

    if not isinstance(included_ids, dict) or not isinstance(excluded_ids, dict):
        return {}

    all_providers = set(included_ids.keys()) | set(excluded_ids.keys())

    for provider in all_providers:
        provider_includes = set(included_ids.get(provider) or [])
        provider_excludes = set(excluded_ids.get(provider) or [])

        intersection = provider_includes.intersection(provider_excludes)
        if intersection:
            conflicts[provider] = intersection

    return conflicts


def get_empty_include_lists(config: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Finds providers with empty include_sts_ids lists.
    """
    empty_lists: Dict[str, List[str]] = {}
    included_ids = config.get("included_sts_ids", {})

    if not isinstance(included_ids, dict):
        return {}

    for provider, ids in included_ids.items():
        if ids is None or (isinstance(ids, list) and len(ids) == 0):
            empty_lists[provider] = ids or []

    return empty_lists
