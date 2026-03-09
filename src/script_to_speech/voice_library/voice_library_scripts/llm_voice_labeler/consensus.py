"""Multi-run/multi-model consensus aggregation for voice analysis results."""

import statistics
from collections import Counter
from typing import Any, Dict, List, Tuple

from script_to_speech.utils.logging import get_screenplay_logger

logger = get_screenplay_logger("llm_voice_labeler.consensus")

# Properties by type
RANGE_PROPERTIES = [
    "age",
    "authority",
    "energy",
    "pace",
    "performative",
    "pitch",
    "quality",
    "range",
]
ENUM_PROPERTIES = ["accent", "gender"]
TEXT_PROPERTIES = ["special_vocal_characteristics"]


def aggregate_runs(
    runs: List[Dict[str, Any]],
) -> Tuple[Dict[str, Any], List[str]]:
    """Aggregate multiple LLM runs for a single voice into consensus.

    Args:
        runs: List of raw result dicts from analyze_voice()

    Returns:
        Tuple of (consensus_result, list_of_flags)
        consensus_result has same structure as individual runs
        flags list issues like enum ties, high variance, etc.
    """
    # Filter out error results
    valid_runs = [r for r in runs if "error" not in r]
    if not valid_runs:
        return {"error": "All runs failed"}, ["all_runs_failed"]

    flags: List[str] = []
    consensus: Dict[str, Any] = {
        "voice_properties": {},
        "description": {},
        "tags": {},
    }

    # Aggregate voice_properties
    vp_results = [r.get("voice_properties", {}) for r in valid_runs]

    # Range properties: use median
    for prop in RANGE_PROPERTIES:
        values = [
            vp.get(prop)
            for vp in vp_results
            if vp.get(prop) is not None and isinstance(vp.get(prop), (int, float))
        ]
        if values:
            median_val = statistics.median(values)
            # Round to nearest 0.05
            consensus["voice_properties"][prop] = round(round(median_val * 20) / 20, 2)

            # Flag high variance
            if len(values) >= 3:
                stdev = statistics.stdev(values)
                if stdev > 0.15:
                    flags.append(
                        f"high_variance:{prop} (stdev={stdev:.2f}, values={values})"
                    )

    # Enum properties: use mode
    for prop in ENUM_PROPERTIES:
        values = [
            vp.get(prop)
            for vp in vp_results
            if vp.get(prop) is not None and isinstance(vp.get(prop), str)
        ]
        if values:
            counter = Counter(values)
            most_common = counter.most_common()
            consensus["voice_properties"][prop] = most_common[0][0]

            # Flag ties
            if len(most_common) > 1 and most_common[0][1] == most_common[1][1]:
                tied = [item[0] for item in most_common if item[1] == most_common[0][1]]
                flags.append(f"enum_tie:{prop} ({tied})")

    # Find representative run once (closest to consensus medians)
    representative_idx = _find_representative_run(valid_runs, consensus)
    rep_run = valid_runs[representative_idx]

    # Text properties: pick from representative run
    rep_vp = rep_run.get("voice_properties", {})
    for prop in TEXT_PROPERTIES:
        values = [vp.get(prop) for vp in vp_results if vp.get(prop) is not None]
        if values:
            consensus["voice_properties"][prop] = rep_vp.get(prop, values[0])

    # Description and reasoning: use representative run
    rep_desc = rep_run.get("description", {})
    consensus["description"]["custom_description"] = rep_desc.get(
        "custom_description", ""
    )
    consensus["description"]["perceived_age"] = rep_desc.get("perceived_age", "")

    # Preserve reasoning from representative run (for debugging and review)
    rep_reasoning = rep_run.get("reasoning")
    if rep_reasoning:
        consensus["reasoning"] = rep_reasoning

    # Tags: include items appearing in >= 50% of runs
    tag_results = [r.get("tags", {}) for r in valid_runs]
    threshold = len(valid_runs) / 2.0

    for tag_field in ["character_types", "custom_tags"]:
        all_items: List[str] = []
        for tr in tag_results:
            items = tr.get(tag_field, [])
            if isinstance(items, list):
                all_items.extend(items)

        counter = Counter(all_items)
        consensus_items = [
            item for item, count in counter.most_common() if count >= threshold
        ]
        consensus["tags"][tag_field] = consensus_items

    return consensus, flags


def _find_representative_run(
    runs: List[Dict[str, Any]], consensus: Dict[str, Any]
) -> int:
    """Find the run closest to the consensus medians (most representative).

    Returns the index of the most representative run.
    """
    if len(runs) <= 1:
        return 0

    consensus_vp = consensus.get("voice_properties", {})
    best_idx = 0
    best_distance = float("inf")

    for i, run in enumerate(runs):
        run_vp = run.get("voice_properties", {})
        distance = 0.0
        count = 0
        for prop in RANGE_PROPERTIES:
            if prop in consensus_vp and prop in run_vp:
                c_val = consensus_vp[prop]
                r_val = run_vp[prop]
                if isinstance(c_val, (int, float)) and isinstance(r_val, (int, float)):
                    distance += abs(c_val - r_val)
                    count += 1
        if count > 0:
            distance /= count
        if distance < best_distance:
            best_distance = distance
            best_idx = i

    return best_idx


def merge_model_consensuses(
    per_model: Dict[str, Tuple[Dict[str, Any], List[str]]],
) -> Tuple[Dict[str, Any], List[str]]:
    """Merge consensus results from multiple models into a final consensus.

    Args:
        per_model: Dict of model_name -> (consensus_result, flags)

    Returns:
        Tuple of (final_consensus, all_flags)
    """
    if len(per_model) == 1:
        model_name = list(per_model.keys())[0]
        result, flags = per_model[model_name]
        return result, [f"[{model_name}] {f}" for f in flags]

    all_flags: List[str] = []
    # Collect flags from individual models
    for model_name, (_, flags) in per_model.items():
        all_flags.extend(f"[{model_name}] {f}" for f in flags)

    # Treat each model's consensus as a "run" and aggregate again
    model_results = [result for result, _ in per_model.values()]
    final, merge_flags = aggregate_runs(model_results)
    all_flags.extend(f"[cross-model] {f}" for f in merge_flags)

    return final, all_flags


def build_voice_consensus(
    all_results: Dict[str, Dict[str, List[Dict[str, Any]]]],
) -> Dict[str, Tuple[Dict[str, Any], List[str]]]:
    """Build consensus for all voices across all models.

    Args:
        all_results: Dict of model_name -> {sts_id -> [run_results]}

    Returns:
        Dict of sts_id -> (final_consensus, flags)
    """
    # Collect all sts_ids across models
    all_sts_ids: set = set()
    for model_results in all_results.values():
        all_sts_ids.update(model_results.keys())

    final_results: Dict[str, Tuple[Dict[str, Any], List[str]]] = {}

    for sts_id in sorted(all_sts_ids):
        # Per-model consensus for this voice
        per_model: Dict[str, Tuple[Dict[str, Any], List[str]]] = {}

        for model_name, model_results in all_results.items():
            runs = model_results.get(sts_id, [])
            if runs:
                consensus, flags = aggregate_runs(runs)
                per_model[model_name] = (consensus, flags)

        if per_model:
            final, flags = merge_model_consensuses(per_model)
            final_results[sts_id] = (final, flags)
        else:
            final_results[sts_id] = ({"error": "No results"}, ["no_results"])

    return final_results
