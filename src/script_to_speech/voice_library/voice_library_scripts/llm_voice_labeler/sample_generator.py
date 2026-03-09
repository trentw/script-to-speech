"""Audio sample generation for LLM voice labeling."""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from script_to_speech.tts_providers.tts_provider_manager import TTSProviderManager
from script_to_speech.utils.generate_standalone_speech import generate_standalone_speech
from script_to_speech.utils.logging import get_screenplay_logger

logger = get_screenplay_logger("llm_voice_labeler.sample_generator")

NEUTRAL_EVALUATION_TEXT = (
    "Thank you for joining us today. The weather forecast calls for partly cloudy "
    "skies with a high near seventy-two degrees. In other news, the downtown farmers "
    "market will be open this Saturday from eight until noon. Vendors will offer fresh "
    "produce, baked goods, and local crafts. The city council met last Tuesday to "
    "discuss the proposed changes to the parking regulations on Main Street. After "
    "reviewing public comments, they voted to table the motion until next month. "
    "For more information, please visit the community website or contact the parks "
    "department during regular business hours. We appreciate your patience as we "
    "work through these updates."
)

EXPRESSIVE_EVALUATION_TEXT = (
    "The morning sun cast long shadows across the quiet village square. "
    '"Good heavens, what happened here?" she gasped, staring at the overturned cart. '
    "He spoke slowly and deliberately, explaining each step of the ancient process "
    "that had been passed down through generations of craftsmen. "
    '"Is anyone even listening to me anymore?" he muttered under his breath. '
    "The wind howled through the canyon, carrying with it the distant echo of thunder. "
    '"Run! Get to the shelter before the storm hits!" the old farmer shouted. '
    "She leaned in close and whispered, barely audible above the crackling fire, "
    '"I know exactly what you did last summer." '
    "The children laughed and played in the garden while their grandmother "
    "watched from the porch, a warm smile spreading across her weathered face. "
    '"Well, that was certainly unexpected," he chuckled, shaking his head in disbelief.'
)

# Legacy alias
EVALUATION_TEXT = EXPRESSIVE_EVALUATION_TEXT


def slugify_voice_id(voice_id: str) -> str:
    """Convert a voice ID like 'English_WiseScholar' to 'wise_scholar'."""
    # Remove common prefixes (including typos in Minimax API)
    name = re.sub(r"^(English|Eglish|Enlish|BritishChild)_", "", voice_id)
    # Insert underscore before uppercase letters (camelCase -> camel_Case)
    name = re.sub(r"(?<=[a-z])(?=[A-Z])", "_", name)
    # Insert underscore between consecutive uppercase and lowercase (ABCDef -> ABC_Def)
    name = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", "_", name)
    # Replace hyphens and spaces with underscores
    name = re.sub(r"[-\s]+", "_", name)
    return name.lower()


def load_input_config(config_path: str) -> Dict[str, Any]:
    """Load and validate a provider input config YAML file."""
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    if not isinstance(config, dict) or "voices" not in config:
        raise ValueError("Input config must contain a 'voices' section")

    voices = config["voices"]
    if not isinstance(voices, dict):
        raise ValueError("'voices' section must be a dictionary")

    for sts_id, entry in voices.items():
        if not isinstance(entry, dict):
            raise ValueError(f"Voice entry '{sts_id}' must be a dictionary")
        if "config" not in entry:
            raise ValueError(f"Voice entry '{sts_id}' must have a 'config' section")

    return config


def generate_input_template(provider_name: str) -> Dict[str, Any]:
    """Auto-generate a starter input config from a provider's VALID_VOICE_IDS."""
    from script_to_speech.utils.generate_standalone_speech import get_provider_class

    provider_class = get_provider_class(provider_name)

    voice_ids: List[str] = []
    if hasattr(provider_class, "VALID_VOICE_IDS"):
        voice_ids = sorted(provider_class.VALID_VOICE_IDS)
    else:
        voice_ids = ["example_voice_id"]

    required_fields = provider_class.get_required_fields()

    voices: Dict[str, Any] = {}
    for vid in voice_ids:
        sts_id = slugify_voice_id(vid)
        config: Dict[str, Any] = {}
        # Populate the required field (typically 'voice_id')
        for field in required_fields:
            if field == "voice_id":
                config["voice_id"] = vid
            elif field != "provider":
                config[field] = ""
        voices[sts_id] = {"config": config}

    return {"voices": voices}


def _generate_single_sample(
    provider_name: str,
    sts_id: str,
    config: Dict[str, Any],
    text: str,
    output_dir: str,
    filename_suffix: str = "",
) -> Optional[str]:
    """Generate a single audio sample. Returns the audio path or None on failure."""
    voice_config = config.copy()
    voice_config["provider"] = provider_name
    tts_provider_config_data = {"default": voice_config}

    suffix = f"_{filename_suffix}" if filename_suffix else ""
    output_filename = f"{provider_name}_{sts_id}{suffix}"

    try:
        tts_manager = TTSProviderManager(
            config_data=tts_provider_config_data,
            overall_provider=None,
            dummy_tts_provider_override=False,
        )
        generate_standalone_speech(
            tts_manager=tts_manager,
            text=text,
            output_dir=output_dir,
            output_filename=output_filename,
        )
        audio_path = os.path.join(output_dir, f"{output_filename}.mp3")
        if os.path.exists(audio_path):
            return audio_path
        else:
            logger.error(f"  Expected output not found: {audio_path}")
            return None
    except Exception as e:
        logger.error(f"  Error generating sample for {sts_id}: {e}")
        return None


def generate_samples(
    provider_name: str,
    input_config: Dict[str, Any],
    output_dir: str,
    sts_ids: Optional[List[str]] = None,
    text: Optional[str] = None,
) -> Dict[str, str]:
    """Generate audio samples for voices defined in the input config.

    Args:
        provider_name: TTS provider name (e.g., 'minimax')
        input_config: Parsed input config with voice entries
        output_dir: Directory for output audio files
        sts_ids: Optional list of specific sts_ids to process
        text: Optional custom evaluation text

    Returns:
        Dict mapping sts_id -> audio file path
    """
    eval_text = text or EVALUATION_TEXT
    os.makedirs(output_dir, exist_ok=True)

    voices = input_config["voices"]
    audio_paths: Dict[str, str] = {}

    entries = [(k, v) for k, v in voices.items() if not sts_ids or k in sts_ids]
    total = len(entries)

    for i, (sts_id, entry) in enumerate(entries):
        logger.info(f"Generating sample {i + 1}/{total}: {sts_id}")
        audio_path = _generate_single_sample(
            provider_name, sts_id, entry["config"], eval_text, output_dir
        )
        if audio_path:
            audio_paths[sts_id] = audio_path
            logger.info(f"  -> {audio_path}")

    logger.info(f"Generated {len(audio_paths)}/{total} audio samples")
    return audio_paths


def generate_dual_samples(
    provider_name: str,
    input_config: Dict[str, Any],
    output_dir: str,
    sts_ids: Optional[List[str]] = None,
) -> Dict[str, Dict[str, str]]:
    """Generate both neutral and expressive audio samples per voice.

    Returns:
        Dict mapping sts_id -> {"neutral": path, "expressive": path}
    """
    os.makedirs(output_dir, exist_ok=True)

    voices = input_config["voices"]
    audio_paths: Dict[str, Dict[str, str]] = {}

    entries = [(k, v) for k, v in voices.items() if not sts_ids or k in sts_ids]
    total = len(entries)

    for i, (sts_id, entry) in enumerate(entries):
        paths: Dict[str, str] = {}

        logger.info(f"Generating neutral sample {i + 1}/{total}: {sts_id}")
        neutral_path = _generate_single_sample(
            provider_name,
            sts_id,
            entry["config"],
            NEUTRAL_EVALUATION_TEXT,
            output_dir,
            "neutral",
        )
        if neutral_path:
            paths["neutral"] = neutral_path
            logger.info(f"  -> {neutral_path}")

        logger.info(f"Generating expressive sample {i + 1}/{total}: {sts_id}")
        expressive_path = _generate_single_sample(
            provider_name,
            sts_id,
            entry["config"],
            EXPRESSIVE_EVALUATION_TEXT,
            output_dir,
            "expressive",
        )
        if expressive_path:
            paths["expressive"] = expressive_path
            logger.info(f"  -> {expressive_path}")

        if paths:
            audio_paths[sts_id] = paths

    logger.info(f"Generated dual samples for {len(audio_paths)}/{total} voices")
    return audio_paths


def collect_calibration_audio(
    provider_name: str,
    voices_yaml_path: str,
    output_dir: str,
    sts_ids: Optional[List[str]] = None,
    text: Optional[str] = None,
    dual_clips: bool = False,
) -> Dict[str, Tuple[Any, Dict[str, Any]]]:
    """Generate audio for known/calibration voices and return paths with labels.

    Args:
        provider_name: TTS provider name
        voices_yaml_path: Path to the provider's voices.yaml (hand-labeled)
        output_dir: Directory for output audio files
        sts_ids: Optional specific sts_ids to process
        text: Optional custom evaluation text (ignored if dual_clips=True)
        dual_clips: If True, generate both neutral and expressive clips

    Returns:
        If dual_clips=False: Dict mapping sts_id -> (audio_path_str, voice_entry)
        If dual_clips=True: Dict mapping sts_id -> ({"neutral": path, "expressive": path}, voice_entry)
    """
    with open(voices_yaml_path, "r") as f:
        voice_data = yaml.safe_load(f)

    voices = voice_data.get("voices", {})
    if not voices:
        raise ValueError(f"No voices found in {voices_yaml_path}")

    # Build input config from voices.yaml
    input_config_voices: Dict[str, Any] = {}
    for sts_id, entry in voices.items():
        if sts_ids and sts_id not in sts_ids:
            continue
        if "config" in entry:
            input_config_voices[sts_id] = {"config": entry["config"]}

    input_config = {"voices": input_config_voices}

    if dual_clips:
        audio_paths = generate_dual_samples(
            provider_name, input_config, output_dir, sts_ids
        )
        result: Dict[str, Tuple[Any, Dict[str, Any]]] = {}
        for sts_id, paths_dict in audio_paths.items():
            result[sts_id] = (paths_dict, voices[sts_id])
        return result
    else:
        audio_paths_single = generate_samples(
            provider_name, input_config, output_dir, sts_ids, text
        )
        result = {}
        for sts_id, audio_path in audio_paths_single.items():
            result[sts_id] = (audio_path, voices[sts_id])
        return result
