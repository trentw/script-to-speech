"""Shared loader for project analysis contexts.

Used by services that need to run the audio-generation planning phase for a
project (review, chunk inventory). Everything is recomputed from the on-disk
sources of truth: the screenplay JSON, the voice config, and the
text-processor config.
"""

import logging
from pathlib import Path
from typing import Tuple

import yaml

from script_to_speech.audio_generation.utils import load_json_chunks
from script_to_speech.text_processors.processor_manager import TextProcessorManager
from script_to_speech.text_processors.utils import get_text_processor_configs
from script_to_speech.tts_providers.tts_provider_manager import TTSProviderManager

from ..config import settings

logger = logging.getLogger(__name__)


def load_project_text_context(
    project_name: str,
) -> Tuple[list, TextProcessorManager]:
    """Load only the screenplay chunks and text processor for a project.

    Lighter sibling of ``load_project_analysis_context`` for callers that
    never plan audio (e.g. PDF anchoring): requires no voice config and
    builds no TTS provider manager.

    Args:
        project_name: Name of the project

    Returns:
        Tuple of (dialogues, processor)

    Raises:
        FileNotFoundError: If the screenplay JSON doesn't exist
    """
    json_path = settings.WORKSPACE_DIR / "input" / project_name / f"{project_name}.json"
    if not json_path.exists():
        raise FileNotFoundError(f"Screenplay JSON not found: {json_path}")

    dialogues = load_json_chunks(str(json_path))
    logger.info(f"Loaded {len(dialogues)} dialogue chunks")

    # Load text processor configs (project-specific or default)
    text_processor_configs = get_text_processor_configs(json_path, None)
    processor = TextProcessorManager(text_processor_configs)

    return dialogues, processor


def load_project_analysis_context(
    project_name: str,
) -> Tuple[list, TTSProviderManager, TextProcessorManager, Path]:
    """Load everything needed to plan audio generation for a project.

    Args:
        project_name: Name of the project

    Returns:
        Tuple of (dialogues, tts_manager, processor, cache_folder)

    Raises:
        FileNotFoundError: If required files don't exist
    """
    workspace_dir = settings.WORKSPACE_DIR

    # Build paths
    input_path = workspace_dir / "input" / project_name
    output_path = workspace_dir / "output" / project_name
    cache_folder = output_path / "cache"

    voice_config_path = input_path / f"{project_name}_voice_config.yaml"

    dialogues, processor = load_project_text_context(project_name)

    if not voice_config_path.exists():
        raise FileNotFoundError(f"Voice config not found: {voice_config_path}")

    # Create cache folder if it doesn't exist
    cache_folder.mkdir(parents=True, exist_ok=True)

    # Load voice config
    with open(voice_config_path, "r") as f:
        tts_config_data = yaml.safe_load(f)

    # Initialize TTS provider manager
    tts_manager = TTSProviderManager(
        config_data=tts_config_data,
        overall_provider=None,
        dummy_tts_provider_override=False,
    )

    return dialogues, tts_manager, processor, cache_folder
