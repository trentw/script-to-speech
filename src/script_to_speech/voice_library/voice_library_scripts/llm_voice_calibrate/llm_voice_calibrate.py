"""Calibration script: validates LLM voice analysis prompt against known hand-labeled voices.

Runs multimodal LLMs on voices with known labels (OpenAI, ElevenLabs),
compares results to ground truth, and produces an accuracy report.
"""

import argparse
import json
import statistics
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from script_to_speech.utils.env_utils import load_environment_variables
from script_to_speech.utils.logging import get_screenplay_logger
from script_to_speech.voice_library.constants import REPO_VOICE_LIBRARY_PATH

logger = get_screenplay_logger("llm_voice_calibrate")

# Import shared modules from llm_voice_labeler
from script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.audio_analyzer import (
    DEFAULT_MODELS,
    analyze_voice_batch,
)
from script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.consensus import (
    ENUM_PROPERTIES,
    RANGE_PROPERTIES,
    aggregate_runs,
)
from script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.prompt_builder import (
    build_system_prompt,
)
from script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.sample_generator import (
    collect_calibration_audio,
)

KNOWN_PROVIDERS = {
    "openai": {
        "voices_files": ["voices.yaml"],
    },
    "elevenlabs": {
        "voices_files": ["voices_premade.yaml", "voices.yaml"],
    },
}


def get_argument_parser() -> argparse.ArgumentParser:
    """Creates and returns the argument parser for this script."""
    parser = argparse.ArgumentParser(
        description="Calibrate LLM voice analysis against known hand-labeled voices."
    )
    parser.add_argument(
        "--providers",
        type=str,
        default="openai",
        help="Comma-separated known providers to calibrate against (default: openai).",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=3,
        help="LLM iterations per voice per model (default: 3).",
    )
    parser.add_argument(
        "--models",
        type=str,
        default=",".join(DEFAULT_MODELS),
        help=f"Comma-separated OpenRouter model IDs (default: {','.join(DEFAULT_MODELS)}).",
    )
    parser.add_argument(
        "--output-dir",
        help="Output directory for calibration report (default: auto-generated).",
    )
    parser.add_argument(
        "--sts-ids",
        type=str,
        help="Comma-separated specific sts_ids to test (default: all).",
    )
    parser.add_argument(
        "--dual-clips",
        action="store_true",
        help="Generate both neutral and expressive audio clips per voice.",
    )
    parser.add_argument(
        "--reuse-audio-from",
        type=str,
        help="Reuse audio from a previous calibration run directory instead of regenerating.",
    )
    return parser


def run(args: argparse.Namespace) -> None:
    """Main execution function for the script."""
    load_environment_variables(verbose=False)

    providers = [p.strip() for p in args.providers.split(",")]
    models = [m.strip() for m in args.models.split(",")]
    sts_ids = [v.strip() for v in args.sts_ids.split(",")] if args.sts_ids else None

    # Validate providers
    for provider in providers:
        if provider not in KNOWN_PROVIDERS:
            print(
                f"Error: Unknown calibration provider '{provider}'. "
                f"Known providers: {', '.join(KNOWN_PROVIDERS.keys())}"
            )
            return

    # Setup output directory (defaults to output/ which is gitignored)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = (
        Path(args.output_dir)
        if args.output_dir
        else (Path("output") / f"llm_calibrate_{timestamp}")
    )

    dual_clips = args.dual_clips

    print(f"Calibration Settings:")
    print(f"  Providers:  {', '.join(providers)}")
    print(f"  Models:     {', '.join(models)}")
    print(f"  Iterations: {args.iterations}")
    print(f"  Dual clips: {dual_clips}")
    print(f"  Output:     {output_dir}")
    print()

    # Step 1: Generate/collect audio for known voices
    all_ground_truth: Dict[str, Dict[str, Any]] = {}  # sts_id -> voice entry
    all_audio_paths: Dict[str, Any] = (
        {}
    )  # sts_id -> path or {"neutral": ..., "expressive": ...}

    reuse_audio_dir = (
        Path(args.reuse_audio_from) / "audio" if args.reuse_audio_from else None
    )

    for provider in providers:
        provider_info = KNOWN_PROVIDERS[provider]
        voices_files = provider_info["voices_files"]

        if reuse_audio_dir:
            audio_dir = str(reuse_audio_dir / provider)
        else:
            audio_dir = str(output_dir / "audio" / provider)
        logger.info(f"Generating audio for {provider} calibration voices")

        for voices_file in voices_files:
            voices_path = str(REPO_VOICE_LIBRARY_PATH / provider / voices_file)
            if not Path(voices_path).exists():
                continue

            # If reusing audio, discover existing files instead of regenerating
            if reuse_audio_dir:
                with open(voices_path, "r") as f:
                    voice_data = yaml.safe_load(f)
                voices_in_file = voice_data.get("voices", {})
                for sts_id, voice_entry in voices_in_file.items():
                    if sts_ids and sts_id not in sts_ids:
                        continue
                    prefixed_id = f"{provider}/{sts_id}"
                    if prefixed_id in all_ground_truth:
                        continue
                    if dual_clips:
                        neutral = Path(audio_dir) / f"{provider}_{sts_id}_neutral.mp3"
                        expressive = (
                            Path(audio_dir) / f"{provider}_{sts_id}_expressive.mp3"
                        )
                        if neutral.exists() and expressive.exists():
                            all_ground_truth[prefixed_id] = voice_entry
                            all_audio_paths[prefixed_id] = {
                                "neutral": str(neutral),
                                "expressive": str(expressive),
                            }
                    else:
                        single = Path(audio_dir) / f"{provider}_{sts_id}.mp3"
                        if single.exists():
                            all_ground_truth[prefixed_id] = voice_entry
                            all_audio_paths[prefixed_id] = str(single)
            else:
                calibration_data = collect_calibration_audio(
                    provider_name=provider,
                    voices_yaml_path=voices_path,
                    output_dir=audio_dir,
                    sts_ids=sts_ids,
                    dual_clips=dual_clips,
                )

                for sts_id, (audio_info, voice_entry) in calibration_data.items():
                    prefixed_id = f"{provider}/{sts_id}"
                    if prefixed_id not in all_ground_truth:
                        all_ground_truth[prefixed_id] = voice_entry
                        all_audio_paths[prefixed_id] = audio_info

    if not all_audio_paths:
        print("Error: No calibration audio generated. Cannot proceed.")
        return

    print(f"Calibration voices: {len(all_audio_paths)}")

    # Step 2: Run LLM analysis
    system_prompt = build_system_prompt(providers, dual_clips=dual_clips)

    # Build a simple voices dict for the batch analyzer
    voices_for_analysis: Dict[str, Dict[str, Any]] = {
        sts_id: {} for sts_id in all_audio_paths
    }

    all_model_results: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    for model in models:
        logger.info(f"Running calibration with model: {model}")
        model_results = analyze_voice_batch(
            model=model,
            system_prompt=system_prompt,
            voices=voices_for_analysis,
            audio_paths=all_audio_paths,
            iterations=args.iterations,
        )
        all_model_results[model] = model_results

    # Step 3: Compare to ground truth
    report = build_calibration_report(all_model_results, all_ground_truth)

    # Save report
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "calibration_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    # Save raw results
    raw_dir = output_dir / "raw_results"
    for model, model_results in all_model_results.items():
        model_dir = raw_dir / model.replace("/", "_")
        model_dir.mkdir(parents=True, exist_ok=True)
        for sts_id, runs in model_results.items():
            safe_id = sts_id.replace("/", "_")
            for i, run_result in enumerate(runs):
                result_path = model_dir / f"{safe_id}_run{i + 1}.json"
                with open(result_path, "w") as f:
                    json.dump(run_result, f, indent=2)

    # Print report
    print_calibration_report(report)
    print(f"\nFull report saved to: {report_path}")


def build_calibration_report(
    all_model_results: Dict[str, Dict[str, List[Dict[str, Any]]]],
    ground_truth: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Build calibration report comparing LLM results to ground truth.

    Returns a structured report with per-model, per-property accuracy metrics.
    """
    report: Dict[str, Any] = {
        "models": {},
        "summary": {},
    }

    for model, model_results in all_model_results.items():
        model_report: Dict[str, Any] = {
            "range_properties": {},
            "enum_properties": {},
            "per_voice": {},
        }

        # Aggregate per-property errors
        range_errors: Dict[str, List[float]] = {p: [] for p in RANGE_PROPERTIES}
        enum_matches: Dict[str, List[bool]] = {p: [] for p in ENUM_PROPERTIES}

        for sts_id, runs in model_results.items():
            if sts_id not in ground_truth:
                continue

            gt = ground_truth[sts_id]
            gt_vp = gt.get("voice_properties", {})

            # Build consensus from runs
            consensus, flags = aggregate_runs(runs)
            consensus_vp = consensus.get("voice_properties", {})

            voice_report: Dict[str, Any] = {"errors": {}, "flags": flags}

            # Range property errors (absolute difference)
            for prop in RANGE_PROPERTIES:
                if prop in gt_vp and prop in consensus_vp:
                    gt_val = gt_vp[prop]
                    pred_val = consensus_vp[prop]
                    if isinstance(gt_val, (int, float)) and isinstance(
                        pred_val, (int, float)
                    ):
                        error = abs(gt_val - pred_val)
                        range_errors[prop].append(error)
                        voice_report["errors"][prop] = {
                            "ground_truth": gt_val,
                            "predicted": pred_val,
                            "error": round(error, 3),
                        }

            # Enum property matches
            for prop in ENUM_PROPERTIES:
                if prop in gt_vp and prop in consensus_vp:
                    match = gt_vp[prop] == consensus_vp[prop]
                    enum_matches[prop].append(match)
                    voice_report["errors"][prop] = {
                        "ground_truth": gt_vp[prop],
                        "predicted": consensus_vp[prop],
                        "match": match,
                    }

            model_report["per_voice"][sts_id] = voice_report

        # Aggregate range property stats
        for prop, errors in range_errors.items():
            if errors:
                model_report["range_properties"][prop] = {
                    "mean_absolute_error": round(statistics.mean(errors), 3),
                    "median_absolute_error": round(statistics.median(errors), 3),
                    "max_error": round(max(errors), 3),
                    "n": len(errors),
                }

        # Aggregate enum property stats
        for prop, matches in enum_matches.items():
            if matches:
                accuracy = sum(matches) / len(matches)
                model_report["enum_properties"][prop] = {
                    "accuracy": round(accuracy, 3),
                    "correct": sum(matches),
                    "total": len(matches),
                }

        # Overall range MAE
        all_errors = [e for errors in range_errors.values() for e in errors]
        if all_errors:
            model_report["overall_range_mae"] = round(statistics.mean(all_errors), 3)

        report["models"][model] = model_report

    # Cross-model summary
    if len(report["models"]) > 1:
        model_maes = {
            model: data.get("overall_range_mae", float("inf"))
            for model, data in report["models"].items()
        }
        report["summary"]["best_range_model"] = min(
            model_maes, key=lambda m: model_maes[m]
        )
        report["summary"]["model_range_maes"] = model_maes

    return report


def print_calibration_report(report: Dict[str, Any]) -> None:
    """Print a human-readable calibration report."""
    print(f"\n{'=' * 60}")
    print("Calibration Report")
    print(f"{'=' * 60}")

    for model, data in report.get("models", {}).items():
        print(f"\nModel: {model}")
        print(f"  Overall Range MAE: {data.get('overall_range_mae', 'N/A')}")

        print("  Range Properties:")
        for prop, stats in data.get("range_properties", {}).items():
            mae = stats.get("mean_absolute_error", "N/A")
            print(f"    {prop:20s} MAE={mae}")

        print("  Enum Properties:")
        for prop, stats in data.get("enum_properties", {}).items():
            acc = stats.get("accuracy", "N/A")
            correct = stats.get("correct", 0)
            total = stats.get("total", 0)
            print(f"    {prop:20s} accuracy={acc} ({correct}/{total})")

        # Show per-voice errors for worst performers
        per_voice = data.get("per_voice", {})
        if per_voice:
            # Find voices with highest total error
            voice_total_errors = {}
            for sts_id, vdata in per_voice.items():
                total_error = sum(
                    e.get("error", 0)
                    for e in vdata.get("errors", {}).values()
                    if isinstance(e.get("error"), (int, float))
                )
                voice_total_errors[sts_id] = total_error

            worst = sorted(
                voice_total_errors.items(), key=lambda x: x[1], reverse=True
            )[:5]
            if worst:
                print("  Worst voices (by total error):")
                for sts_id, total_err in worst:
                    print(f"    {sts_id}: total_error={total_err:.3f}")

    summary = report.get("summary", {})
    if summary.get("best_range_model"):
        print(f"\nBest model for range properties: {summary['best_range_model']}")

    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    parser = get_argument_parser()
    args = parser.parse_args()
    run(args)
