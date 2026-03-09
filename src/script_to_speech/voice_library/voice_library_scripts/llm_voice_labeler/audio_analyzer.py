"""LLM audio analysis via OpenRouter using OpenAI SDK."""

import base64
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from openai import OpenAI

from script_to_speech.utils.env_utils import load_environment_variables
from script_to_speech.utils.logging import get_screenplay_logger

logger = get_screenplay_logger("llm_voice_labeler.audio_analyzer")

DEFAULT_MODELS = ["google/gemini-3.1-pro-preview"]

# Rate limit retry config
MAX_RETRIES = 5
INITIAL_BACKOFF = 2.0
BACKOFF_FACTOR = 2.0


def get_openrouter_client() -> OpenAI:
    """Create an OpenAI client pointed at OpenRouter."""
    load_environment_variables(verbose=False)
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENROUTER_API_KEY environment variable is not set. "
            "Get your key at https://openrouter.ai/keys"
        )
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )


def encode_audio_base64(audio_path: str) -> str:
    """Read an audio file and return base64-encoded string."""
    with open(audio_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def analyze_voice(
    client: OpenAI,
    model: str,
    system_prompt: str,
    user_message: str,
    audio_path: Optional[str] = None,
    audio_paths: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Send audio to an LLM for voice analysis.

    Args:
        client: OpenRouter-configured OpenAI client
        model: OpenRouter model ID
        system_prompt: System prompt with schema and calibration
        user_message: Per-voice user message with provider context
        audio_path: Path to a single audio file (legacy single-clip mode)
        audio_paths: Dict of clip_type -> path (e.g., {"neutral": ..., "expressive": ...})

    Returns:
        Parsed JSON response with voice properties
    """
    # Build user content with audio clip(s)
    user_content: List[Dict[str, Any]] = []

    if audio_paths:
        # Dual-clip mode: add labeled audio clips
        for clip_type, path in audio_paths.items():
            user_content.append({"type": "text", "text": f"[{clip_type.upper()} CLIP]"})
            user_content.append(
                {
                    "type": "input_audio",
                    "input_audio": {
                        "data": encode_audio_base64(path),
                        "format": Path(path).suffix.lstrip("."),
                    },
                }
            )
    elif audio_path:
        # Single-clip mode (legacy)
        user_content.append(
            {
                "type": "input_audio",
                "input_audio": {
                    "data": encode_audio_base64(audio_path),
                    "format": Path(audio_path).suffix.lstrip("."),
                },
            }
        )
    else:
        raise ValueError("Either audio_path or audio_paths must be provided")

    user_content.append({"type": "text", "text": user_message})

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    # Try with json_object response format; fall back without if unsupported
    use_json_format = True
    backoff = INITIAL_BACKOFF
    attempt = 0

    while attempt < MAX_RETRIES:
        try:
            kwargs = {
                "model": model,
                "messages": messages,
                "temperature": 0.3,
            }
            if use_json_format:
                kwargs["response_format"] = {"type": "json_object"}

            response = client.chat.completions.create(**kwargs)  # type: ignore[call-overload]
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from model")

            # Parse JSON, stripping markdown fences if present
            content = content.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(
                    lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
                )

            result: Dict[str, Any] = json.loads(content)
            return result

        except Exception as e:
            error_str = str(e)

            # If model doesn't support json_object, retry without it (don't count as attempt)
            if "response_format" in error_str and use_json_format:
                logger.warning(
                    f"{model} doesn't support json_object response_format, "
                    f"retrying without it"
                )
                use_json_format = False
                continue

            attempt += 1
            is_rate_limit = "rate" in error_str.lower() or "429" in error_str

            if is_rate_limit and attempt < MAX_RETRIES:
                logger.warning(
                    f"Rate limited on {model}, retrying in {backoff:.0f}s "
                    f"(attempt {attempt}/{MAX_RETRIES})"
                )
                time.sleep(backoff)
                backoff *= BACKOFF_FACTOR
                continue

            if attempt < MAX_RETRIES and "json" in error_str.lower():
                logger.warning(
                    f"JSON parse error on {model}, retrying "
                    f"(attempt {attempt}/{MAX_RETRIES}): {error_str[:100]}"
                )
                time.sleep(1)
                continue

            raise

    raise RuntimeError(f"Failed after {MAX_RETRIES} attempts")


def analyze_voice_batch(
    model: str,
    system_prompt: str,
    voices: Dict[str, Dict[str, Any]],
    audio_paths: Dict[str, Any],
    iterations: int = 3,
    input_config: Optional[Dict[str, Any]] = None,
    raw_results_dir: Optional[Path] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """Analyze multiple voices with multiple iterations.

    Args:
        model: OpenRouter model ID
        system_prompt: System prompt with schema and calibration
        voices: Dict of sts_id -> voice entry (from input config)
        audio_paths: Dict of sts_id -> audio_path_str OR {"neutral": path, "expressive": path}
        iterations: Number of analysis iterations per voice
        input_config: Full input config for provider_info lookup

    Returns:
        Dict of sts_id -> list of raw results (one per iteration)
    """
    client = get_openrouter_client()
    results: Dict[str, List[Dict[str, Any]]] = {}

    total = len(audio_paths) * iterations
    current = 0

    from script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.prompt_builder import (
        build_user_message,
    )

    for sts_id, audio_info in audio_paths.items():
        results[sts_id] = []
        voice_entry = voices.get(sts_id, {})
        provider_info = voice_entry.get("provider_info")

        user_msg = build_user_message(provider_info)

        # Determine if single or dual clip mode
        is_dual = isinstance(audio_info, dict)

        for iteration in range(iterations):
            current += 1
            logger.info(
                f"[{current}/{total}] {model} | {sts_id} | iteration {iteration + 1}/{iterations}"
            )

            try:
                if is_dual:
                    result = analyze_voice(
                        client=client,
                        model=model,
                        system_prompt=system_prompt,
                        user_message=user_msg,
                        audio_paths=audio_info,
                    )
                else:
                    result = analyze_voice(
                        client=client,
                        model=model,
                        system_prompt=system_prompt,
                        user_message=user_msg,
                        audio_path=audio_info,
                    )
                results[sts_id].append(result)
                logger.info(f"  -> Success")
                if raw_results_dir:
                    result_path = raw_results_dir / f"{sts_id}_run{iteration + 1}.json"
                    result_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(result_path, "w") as f:
                        json.dump(result, f, indent=2)
            except Exception as e:
                logger.error(f"  -> Error: {e}")
                results[sts_id].append({"error": str(e)})

    return results
