"""Main script: LLM-assisted voice labeling for new TTS providers.

Generates audio samples, analyzes them with multimodal LLMs via OpenRouter,
builds consensus across multiple runs/models, and outputs a valid voices.yaml.
"""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from script_to_speech.utils.env_utils import load_environment_variables
from script_to_speech.utils.logging import get_screenplay_logger
from script_to_speech.voice_library.constants import USER_VOICE_LIBRARY_PATH
from script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.audio_analyzer import (
    DEFAULT_MODELS,
    analyze_voice_batch,
)
from script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.consensus import (
    aggregate_runs,
    build_voice_consensus,
)
from script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.output_formatter import (
    format_voices_yaml,
    print_summary,
    write_voices_yaml,
)
from script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.prompt_builder import (
    build_system_prompt,
)
from script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.sample_generator import (
    generate_dual_samples,
    generate_input_template,
    generate_samples,
    load_input_config,
)

logger = get_screenplay_logger("llm_voice_labeler")


def get_argument_parser() -> argparse.ArgumentParser:
    """Creates and returns the argument parser for this script."""
    parser = argparse.ArgumentParser(
        description="LLM-assisted voice labeling for new TTS providers."
    )
    parser.add_argument("provider", help="The TTS provider to label voices for.")
    parser.add_argument(
        "--input-config",
        help="Path to provider input config YAML (sts_id mapping + provider metadata).",
    )
    parser.add_argument(
        "--generate-input-template",
        action="store_true",
        help="Auto-generate a starter input config from the provider's voice IDs.",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=3,
        help="Number of LLM iterations per voice per model (default: 3).",
    )
    parser.add_argument(
        "--models",
        type=str,
        default=",".join(DEFAULT_MODELS),
        help=f"Comma-separated OpenRouter model IDs (default: {','.join(DEFAULT_MODELS)}).",
    )
    parser.add_argument(
        "--skip-audio-gen",
        action="store_true",
        help="Skip audio generation, reuse existing samples.",
    )
    parser.add_argument(
        "--audio-dir",
        help="Directory containing pre-generated audio samples.",
    )
    parser.add_argument(
        "--output-dir",
        help="Output directory for results (default: auto-generated).",
    )
    parser.add_argument(
        "--sts-ids",
        type=str,
        help="Comma-separated list of specific sts_ids to process.",
    )
    parser.add_argument(
        "--dual-clips",
        action="store_true",
        help="Generate neutral + expressive audio clips per voice (recommended).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be done without calling LLMs.",
    )
    parser.add_argument(
        "--from-raw-results",
        type=str,
        help="Path to a raw_results/ directory from a previous run. "
        "Skips audio generation and LLM analysis, rebuilds consensus + voices.yaml.",
    )
    return parser


def run(args: argparse.Namespace) -> None:
    """Main execution function for the script."""
    load_environment_variables(verbose=False)

    provider = args.provider
    models = [m.strip() for m in args.models.split(",")]
    sts_ids = [v.strip() for v in args.sts_ids.split(",")] if args.sts_ids else None

    # Handle --generate-input-template
    if args.generate_input_template:
        template = generate_input_template(provider)
        output_path = Path(f"{provider}_voice_input.yaml")
        with open(output_path, "w") as f:
            yaml.dump(template, f, default_flow_style=False, sort_keys=False)
        print(f"Generated input template: {output_path}")
        voices = template.get("voices", {})
        if len(voices) == 1 and "example_voice_id" in voices:
            print(f"\nNote: Provider '{provider}' does not have a built-in voice list.")
            print(
                "The template contains a single example entry. Copy/paste it for each "
                "voice you want to label, replacing the placeholder values."
            )
        print(f"\nEdit this file to add provider_info metadata, then run:")
        print(
            f"  sts-voice-library-run-script llm_voice_labeler {provider} "
            f"--input-config {output_path} --dual-clips"
        )
        return

    # Handle --from-raw-results (crash recovery)
    if args.from_raw_results:
        if not args.input_config:
            print("Error: --input-config is required with --from-raw-results.")
            return
        input_config = load_input_config(args.input_config)
        raw_results_path = Path(args.from_raw_results)
        if not raw_results_path.exists():
            print(f"Error: Raw results directory not found: {raw_results_path}")
            return
        _rebuild_from_raw_results(provider, input_config, raw_results_path, sts_ids)
        return

    # Load input config
    if not args.input_config:
        print(
            "Error: --input-config is required. Use --generate-input-template to create one."
        )
        return

    input_config = load_input_config(args.input_config)
    voices = input_config["voices"]

    # Setup output directory (defaults to output/ which is gitignored)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = Path("output") / f"llm_labeler_{provider}_{timestamp}"

    audio_dir = Path(args.audio_dir) if args.audio_dir else output_dir / "audio"
    raw_results_dir = output_dir / "raw_results"
    consensus_dir = output_dir / "consensus"

    # Filter voices if needed
    if sts_ids:
        voices = {k: v for k, v in voices.items() if k in sts_ids}
        if not voices:
            print(f"Error: None of the specified voice IDs found in input config.")
            return

    dual_clips = args.dual_clips

    print(f"Provider: {provider}")
    print(f"Voices:   {len(voices)}")
    print(f"Models:   {', '.join(models)}")
    print(f"Iterations per model: {args.iterations}")
    print(f"Dual clips: {dual_clips}")
    print(f"Output:   {output_dir}")
    print()

    if args.dry_run:
        print("DRY RUN - would process these voices:")
        for sts_id, entry in voices.items():
            config = entry.get("config", {})
            provider_info = entry.get("provider_info", {})
            name = provider_info.get("provider_name", config.get("voice_id", "?"))
            print(f"  {sts_id}: {name}")
        total_calls = len(voices) * args.iterations * len(models)
        print(f"\nTotal LLM calls: {total_calls}")
        return

    # Step 1: Generate audio samples
    if args.skip_audio_gen:
        logger.info("Skipping audio generation, using existing samples")
        audio_paths = _discover_audio_files(
            str(audio_dir), provider, voices, dual_clips
        )
    elif dual_clips:
        logger.info("Step 1: Generating dual audio samples (neutral + expressive)")
        audio_paths = generate_dual_samples(
            provider, input_config, str(audio_dir), sts_ids
        )
    else:
        logger.info("Step 1: Generating audio samples")
        audio_paths = generate_samples(provider, input_config, str(audio_dir), sts_ids)

    if not audio_paths:
        print("Error: No audio samples available. Cannot proceed.")
        return

    print(f"Audio samples: {len(audio_paths)}/{len(voices)}")

    # Step 2: Build prompt
    logger.info("Step 2: Building analysis prompt")
    system_prompt = build_system_prompt(dual_clips=dual_clips)

    # Step 3: LLM analysis
    logger.info("Step 3: Running LLM analysis")
    all_model_results: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}

    for model in models:
        logger.info(f"Analyzing with model: {model}")
        model_results_dir = raw_results_dir / _safe_model_name(model)
        model_results = analyze_voice_batch(
            model=model,
            system_prompt=system_prompt,
            voices=voices,
            audio_paths=audio_paths,
            iterations=args.iterations,
            input_config=input_config,
            raw_results_dir=model_results_dir,
        )
        all_model_results[model] = model_results

    # Step 4: Build consensus
    logger.info("Step 4: Building consensus")
    consensus_results = build_voice_consensus(all_model_results)

    # Save per-model consensus
    per_model_dir = consensus_dir / "per_model"
    per_model_dir.mkdir(parents=True, exist_ok=True)
    for model in models:
        model_consensus: Dict[str, Any] = {}
        for sts_id in audio_paths:
            runs = all_model_results.get(model, {}).get(sts_id, [])
            if runs:
                result, flags = aggregate_runs(runs)
                model_consensus[sts_id] = {"result": result, "flags": flags}
        model_path = per_model_dir / f"{_safe_model_name(model)}.json"
        with open(model_path, "w") as f:
            json.dump(model_consensus, f, indent=2)

    # Save final consensus
    final_dir = consensus_dir / "final"
    final_dir.mkdir(parents=True, exist_ok=True)
    for sts_id, (result, flags) in consensus_results.items():
        result_path = final_dir / f"{sts_id}.json"
        with open(result_path, "w") as f:
            json.dump({"result": result, "flags": flags}, f, indent=2)

    # Step 5: Output voices.yaml
    logger.info("Step 5: Generating voices.yaml")
    output_data = format_voices_yaml(provider, input_config, consensus_results)

    # Write to output directory
    output_yaml_path = output_dir / "voices.yaml"
    write_voices_yaml(output_data, output_yaml_path)

    # Also write to user voice library path for direct use
    # If processing a subset (--sts-ids), merge with existing file to avoid data loss
    user_output_path = USER_VOICE_LIBRARY_PATH / provider / "voices.yaml"
    if sts_ids and user_output_path.exists():
        with open(user_output_path, "r") as f:
            existing_data = yaml.safe_load(f) or {}
        existing_voices = existing_data.get("voices", {})
        existing_voices.update(output_data.get("voices", {}))
        output_data["voices"] = existing_voices
        if (
            "provider_metadata" in existing_data
            and "provider_metadata" not in output_data
        ):
            output_data["provider_metadata"] = existing_data["provider_metadata"]
    write_voices_yaml(output_data, user_output_path)
    print(f"Also wrote to user voice library: {user_output_path}")

    # Print summary
    print_summary(consensus_results)


def _load_raw_results(
    raw_results_dir: Path,
) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    """Load raw results from disk into the all_model_results structure.

    Scans subdirectories of raw_results_dir (each representing a model),
    and globs for {sts_id}_run{N}.json files.

    Returns:
        Dict of model_name -> {sts_id -> [run_results]}
    """
    import re

    all_model_results: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}

    if not raw_results_dir.exists():
        return all_model_results

    for model_dir in sorted(raw_results_dir.iterdir()):
        if not model_dir.is_dir():
            continue

        model_name = model_dir.name
        model_results: Dict[str, List[Dict[str, Any]]] = {}

        for result_file in sorted(model_dir.glob("*_run*.json")):
            match = re.match(r"^(.+)_run(\d+)\.json$", result_file.name)
            if not match:
                continue

            sts_id = match.group(1)
            with open(result_file, "r") as f:
                result = json.load(f)

            if sts_id not in model_results:
                model_results[sts_id] = []
            model_results[sts_id].append(result)

        if model_results:
            all_model_results[model_name] = model_results
            logger.info(
                f"Loaded {sum(len(v) for v in model_results.values())} results "
                f"for {len(model_results)} voices from {model_name}"
            )

    return all_model_results


def _rebuild_from_raw_results(
    provider: str,
    input_config: Dict[str, Any],
    raw_results_dir: Path,
    sts_ids: Optional[List[str]] = None,
) -> None:
    """Rebuild consensus + voices.yaml from existing raw results on disk."""
    output_dir = raw_results_dir.parent
    consensus_dir = output_dir / "consensus"

    all_model_results = _load_raw_results(raw_results_dir)
    if not all_model_results:
        print(f"Error: No raw results found in {raw_results_dir}")
        return

    # Filter by sts_ids if specified
    if sts_ids:
        for model_name in all_model_results:
            all_model_results[model_name] = {
                k: v for k, v in all_model_results[model_name].items() if k in sts_ids
            }

    total_voices: set[str] = set()
    for model_results in all_model_results.values():
        total_voices.update(model_results.keys())

    print(f"Rebuilding from raw results:")
    print(f"  Models: {len(all_model_results)}")
    print(f"  Voices: {len(total_voices)}")
    print()

    # Build consensus (Steps 4-5 from normal run)
    logger.info("Building consensus from raw results")
    consensus_results = build_voice_consensus(all_model_results)

    # Save per-model consensus
    per_model_dir = consensus_dir / "per_model"
    per_model_dir.mkdir(parents=True, exist_ok=True)
    for model_name, model_results in all_model_results.items():
        model_consensus: Dict[str, Any] = {}
        for sts_id, runs in model_results.items():
            if runs:
                result, flags = aggregate_runs(runs)
                model_consensus[sts_id] = {"result": result, "flags": flags}
        model_path = per_model_dir / f"{model_name}.json"
        with open(model_path, "w") as f:
            json.dump(model_consensus, f, indent=2)

    # Save final consensus
    final_dir = consensus_dir / "final"
    final_dir.mkdir(parents=True, exist_ok=True)
    for sts_id, (result, flags) in consensus_results.items():
        result_path = final_dir / f"{sts_id}.json"
        with open(result_path, "w") as f:
            json.dump({"result": result, "flags": flags}, f, indent=2)

    # Output voices.yaml
    logger.info("Generating voices.yaml")
    output_data = format_voices_yaml(provider, input_config, consensus_results)

    output_yaml_path = output_dir / "voices.yaml"
    write_voices_yaml(output_data, output_yaml_path)

    user_output_path = USER_VOICE_LIBRARY_PATH / provider / "voices.yaml"
    if sts_ids and user_output_path.exists():
        with open(user_output_path, "r") as f:
            existing_data = yaml.safe_load(f) or {}
        existing_voices = existing_data.get("voices", {})
        existing_voices.update(output_data.get("voices", {}))
        output_data["voices"] = existing_voices
        if (
            "provider_metadata" in existing_data
            and "provider_metadata" not in output_data
        ):
            output_data["provider_metadata"] = existing_data["provider_metadata"]
    write_voices_yaml(output_data, user_output_path)
    print(f"Also wrote to user voice library: {user_output_path}")

    print_summary(consensus_results)


def _safe_model_name(model: str) -> str:
    """Convert model ID to safe directory name."""
    return model.replace("/", "_").replace(":", "_")


def _discover_audio_files(
    audio_dir: str,
    provider: str,
    voices: Dict[str, Any],
    dual_clips: bool = False,
) -> Dict[str, Any]:
    """Discover existing audio files matching voice entries.

    Returns:
        If dual_clips=False: Dict of sts_id -> audio_path_str
        If dual_clips=True: Dict of sts_id -> {"neutral": path, "expressive": path}
    """
    audio_paths: Dict[str, Any] = {}
    audio_path = Path(audio_dir)

    if not audio_path.exists():
        logger.warning(f"Audio directory does not exist: {audio_dir}")
        return audio_paths

    for sts_id in voices:
        if dual_clips:
            neutral = audio_path / f"{provider}_{sts_id}_neutral.mp3"
            expressive = audio_path / f"{provider}_{sts_id}_expressive.mp3"
            if neutral.exists() and expressive.exists():
                audio_paths[sts_id] = {
                    "neutral": str(neutral),
                    "expressive": str(expressive),
                }
        else:
            expected = audio_path / f"{provider}_{sts_id}.mp3"
            if expected.exists():
                audio_paths[sts_id] = str(expected)
            else:
                # Search for any file containing the sts_id
                for f in audio_path.iterdir():
                    if sts_id in f.name and f.suffix in (".mp3", ".wav", ".ogg"):
                        audio_paths[sts_id] = str(f)
                        break

    return audio_paths


if __name__ == "__main__":
    parser = get_argument_parser()
    args = parser.parse_args()
    run(args)
