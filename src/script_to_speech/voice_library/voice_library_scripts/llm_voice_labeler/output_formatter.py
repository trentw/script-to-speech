"""Format consensus results into a valid voices.yaml file."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from script_to_speech.utils.logging import get_screenplay_logger

logger = get_screenplay_logger("llm_voice_labeler.output_formatter")


def format_voices_yaml(
    provider_name: str,
    input_config: Dict[str, Any],
    consensus_results: Dict[str, Tuple[Dict[str, Any], List[str]]],
    provider_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Convert consensus results into a voices.yaml structure.

    Args:
        provider_name: TTS provider name
        input_config: Original input config with voice entries
        consensus_results: Dict of sts_id -> (consensus, flags)
        provider_metadata: Optional provider_metadata section

    Returns:
        Dict ready to be dumped as voices.yaml
    """
    output: Dict[str, Any] = {}

    if provider_metadata:
        output["provider_metadata"] = provider_metadata

    voices: Dict[str, Any] = {}
    input_voices = input_config.get("voices", {})

    for sts_id, (consensus, flags) in consensus_results.items():
        if "error" in consensus:
            logger.warning(f"Skipping {sts_id}: {consensus['error']}")
            continue

        voice_entry: Dict[str, Any] = {}

        # Config from input config
        if sts_id in input_voices:
            voice_entry["config"] = input_voices[sts_id]["config"]

        # Voice properties from consensus
        vp = consensus.get("voice_properties", {})
        if vp:
            voice_entry["voice_properties"] = {}
            # Enum properties first
            for prop in ["accent", "gender"]:
                if prop in vp:
                    voice_entry["voice_properties"][prop] = vp[prop]
            # Range properties
            for prop in [
                "age",
                "authority",
                "energy",
                "pace",
                "performative",
                "pitch",
                "quality",
                "range",
            ]:
                if prop in vp:
                    voice_entry["voice_properties"][prop] = vp[prop]
            # Text properties
            if (
                "special_vocal_characteristics" in vp
                and vp["special_vocal_characteristics"]
            ):
                voice_entry["voice_properties"]["special_vocal_characteristics"] = vp[
                    "special_vocal_characteristics"
                ]

        # Description from consensus + provider_info
        desc: Dict[str, Any] = {}
        provider_info = input_voices.get(sts_id, {}).get("provider_info", {})
        if provider_info.get("provider_name"):
            desc["provider_name"] = provider_info["provider_name"]
        if provider_info.get("provider_description"):
            desc["provider_description"] = provider_info["provider_description"]
        if provider_info.get("provider_use_cases"):
            desc["provider_use_cases"] = provider_info["provider_use_cases"]

        consensus_desc = consensus.get("description", {})
        if consensus_desc.get("custom_description"):
            desc["custom_description"] = consensus_desc["custom_description"]
        if consensus_desc.get("perceived_age"):
            desc["perceived_age"] = consensus_desc["perceived_age"]

        if desc:
            voice_entry["description"] = desc

        # Tags from consensus
        tags: Dict[str, Any] = {}
        consensus_tags = consensus.get("tags", {})
        if provider_info.get("provider_use_cases"):
            # Convert provider use cases to tag format
            use_cases = provider_info["provider_use_cases"]
            if isinstance(use_cases, str):
                use_cases_tags = [
                    uc.strip().lower().replace(" ", "_") for uc in use_cases.split(",")
                ]
            else:
                use_cases_tags = use_cases
            tags["provider_use_cases"] = use_cases_tags

        if consensus_tags.get("character_types"):
            tags["character_types"] = consensus_tags["character_types"]
        if consensus_tags.get("custom_tags"):
            tags["custom_tags"] = consensus_tags["custom_tags"]

        if tags:
            voice_entry["tags"] = tags

        # Preview URL from input config
        preview_url = input_voices.get(sts_id, {}).get("preview_url")
        if preview_url:
            voice_entry["preview_url"] = preview_url

        voices[sts_id] = voice_entry

    output["voices"] = voices
    return output


def write_voices_yaml(
    output_data: Dict[str, Any],
    output_path: Path,
) -> None:
    """Write voices.yaml to disk."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        yaml.dump(output_data, f, default_flow_style=False, sort_keys=False)

    logger.info(f"Wrote voices.yaml to {output_path}")


def print_summary(
    consensus_results: Dict[str, Tuple[Dict[str, Any], List[str]]],
) -> None:
    """Print a summary of the labeling results including flagged issues."""
    total = len(consensus_results)
    successful = sum(1 for _, (c, _) in consensus_results.items() if "error" not in c)
    failed = total - successful

    print(f"\n{'=' * 60}")
    print(f"Voice Labeling Summary")
    print(f"{'=' * 60}")
    print(f"Total voices: {total}")
    print(f"Successful:   {successful}")
    if failed:
        print(f"Failed:       {failed}")

    # Collect all flags
    all_flags: List[str] = []
    flagged_voices: List[str] = []
    for sts_id, (_, flags) in consensus_results.items():
        if flags:
            flagged_voices.append(sts_id)
            for f in flags:
                all_flags.append(f"{sts_id}: {f}")

    if all_flags:
        print(f"\nFlagged issues ({len(all_flags)}):")
        for flag in all_flags:
            print(f"  - {flag}")
    else:
        print("\nNo flagged issues.")

    print(f"{'=' * 60}\n")
