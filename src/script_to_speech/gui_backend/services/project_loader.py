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

    json_path = input_path / f"{project_name}.json"
    voice_config_path = input_path / f"{project_name}_voice_config.yaml"

    # Validate paths exist
    if not json_path.exists():
        raise FileNotFoundError(f"Screenplay JSON not found: {json_path}")
    if not voice_config_path.exists():
        raise FileNotFoundError(f"Voice config not found: {voice_config_path}")

    # Create cache folder if it doesn't exist
    cache_folder.mkdir(parents=True, exist_ok=True)

    # Load dialogues
    dialogues = load_json_chunks(str(json_path))
    logger.info(f"Loaded {len(dialogues)} dialogue chunks")

    # Load voice config
    with open(voice_config_path, "r") as f:
        tts_config_data = yaml.safe_load(f)

    # Initialize TTS provider manager
    tts_manager = TTSProviderManager(
        config_data=tts_config_data,
        overall_provider=None,
        dummy_tts_provider_override=False,
    )

    # Load text processor configs (project-specific or default)
    text_processor_configs = get_text_processor_configs(json_path, None)
    processor = TextProcessorManager(text_processor_configs)

    return dialogues, tts_manager, processor, cache_folder
