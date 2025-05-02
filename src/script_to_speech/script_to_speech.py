import argparse
import json
import logging
import os
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydub import AudioSegment
from tqdm import tqdm

from .audio_generation.models import AudioGenerationTask
from .audio_generation.processing import (
    apply_cache_overrides,
    check_for_silence,
    fetch_and_cache_audio,
    plan_audio_generation,
)
from .audio_generation.reporting import (
    ReportingState,
    print_unified_report,
    recheck_audio_files,
)
from .audio_generation.utils import (
    concatenate_tasks_batched,
    create_output_folders,
    load_json_chunks,
)
from .text_processors.processor_manager import TextProcessorManager
from .text_processors.utils import get_processor_configs
from .tts_providers.tts_provider_manager import TTSProviderManager
from .utils.audio_utils import configure_ffmpeg
from .utils.id3_tag_utils import set_id3_tags_from_config
from .utils.logging import get_screenplay_logger, setup_screenplay_logging

# Define logger for this script
logger = get_screenplay_logger("script_to_speech")


def parse_arguments() -> argparse.Namespace:
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate an audio file from dialogues using screen.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "input_file", help="Path to the input JSON file containing dialogues."
    )
    parser.add_argument(
        "--gap",
        type=int,
        default=500,
        help="Gap duration between dialogues in milliseconds.",
    )
    parser.add_argument(
        "--provider",
        choices=TTSProviderManager.get_available_providers(),
        help="Choose the default TTS provider (if not specified in voice config).",
    )
    parser.add_argument(
        "--tts-config", help="Path to YAML configuration file for TTS provider."
    )
    parser.add_argument(
        "--processor-configs",
        nargs="*",
        help="Path(s) to YAML configuration file(s) for text (pre)processors. "
        "Multiple paths can be provided.",
    )
    parser.add_argument(
        "--ffmpeg-path",
        help="Path to ffmpeg binary or directory containing ffmpeg binaries.",
    )
    parser.add_argument(
        "--check-silence",
        type=float,
        nargs="?",
        const=-40.0,
        metavar="DBFS",
        help="Check audio files for silence. Optional dBFS threshold (default: -40.0). "
        "Applies to both cached and newly generated files.",
    )
    parser.add_argument(
        "--cache-overrides",
        nargs="?",
        const="standalone_speech",  # Default override dir if flag used without value
        default=None,  # Default is None if flag is not used at all
        metavar="PATH",
        help="Path to audio files that will override cache files if present. "
        'If flag is used without path, defaults to "standalone_speech". '
        "If flag is not used, no overrides are applied.",
    )
    parser.add_argument(
        "--optional-config",
        help="Path to optional configuration file for ID3 tags. "
        "If not provided, will look for [input_json]_optional_config.yaml.",
    )
    parser.add_argument(
        "--max-report-misses",
        type=int,
        default=20,
        help="Maximum number of cache misses/silent clips for which to print generation commands.",
    )
    parser.add_argument(
        "--max-report-text",
        type=int,
        default=30,
        help="Maximum text length for clips included in generation commands.",
    )
    parser.add_argument(
        "--concat-batch-size",
        type=int,
        default=250,
        help="Batch size for audio concatenation (number of clips per batch).",
    )
    parser.add_argument(
        "--dummy-provider-override",
        action="store_true",
        help="Override configured providers with dummy providers for testing purposes. "
        "This will replace configured providers with dummy_stateful/dummy_stateless providers.",
    )

    # Mutually exclusive group for run modes
    run_mode_group = parser.add_mutually_exclusive_group()
    run_mode_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Plan audio generation and report cache status without fetching or generating audio.",
    )
    run_mode_group.add_argument(
        "--populate-cache",
        action="store_true",
        help="Plan, fetch/generate, and cache audio files. Skips final output.",
    )

    return parser.parse_args()


def save_modified_json(
    modified_dialogues: List[Dict[str, Any]], output_folder: str, input_file: str
) -> None:
    """Saves the processed dialogue chunks to a JSON file."""
    try:
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        modified_json_path = os.path.join(output_folder, f"{base_name}-modified.json")
        with open(modified_json_path, "w", encoding="utf-8") as f:
            json.dump(modified_dialogues, f, ensure_ascii=False, indent=2)
        logger.info(f"\nProcessed dialogue saved to: {modified_json_path}")
    except Exception as e:
        logger.error(f"Failed to save modified JSON: {e}", exc_info=True)


def find_optional_config(
    args_config_path: Optional[str], input_file_path: str
) -> Optional[str]:
    """Finds the optional config file path, checking default if necessary."""
    if args_config_path:
        if os.path.exists(args_config_path):
            return args_config_path
        else:
            logger.warning(
                f"Specified optional config file not found: {args_config_path}"
            )
            return None

    # Try the default path
    input_path = Path(input_file_path)
    base_name = input_path.stem
    default_config_path = input_path.parent / f"{base_name}_optional_config.yaml"
    if default_config_path.exists():
        logger.info(f"Found default optional config file: {default_config_path}")
        return str(default_config_path)

    return None


def main() -> None:
    """Main execution function."""
    args = parse_arguments()

    # Determine run mode string early for logging/folder creation
    run_mode = (
        "dry-run"
        if args.dry_run
        else "populate-cache" if args.populate_cache else "generate-output"
    )

    logger.info(f"\n--- Setting up for {run_mode.upper()} mode ---")
    # --- Setup ---
    try:
        # Create output folders
        output_folder, cache_folder, output_file, log_file = create_output_folders(
            args.input_file, run_mode, args.dummy_provider_override
        )

        # Setup logging (must happen after log_file path is determined)
        setup_screenplay_logging(log_file)
        logger.info(f"Logging initialized. Log file: {log_file}")
        logger.info(f"Run mode: {run_mode}")
        if args.check_silence is not None:
            logger.info(
                f"Silence checking enabled: Threshold = {args.check_silence} dBFS"
            )
        if args.cache_overrides:
            logger.info(f"Cache overrides enabled. Directory: {args.cache_overrides}")
        if args.dummy_provider_override:
            logger.info("DUMMY PROVIDER OVERRIDE MODE ENABLED")
            logger.info(
                "All configured providers will be replaced with dummy providers and produce dummy audio"
            )
            logger.info(f"Using dummy cache folder: {cache_folder}")
            if output_file:
                logger.info(f"Using dummy output file: {output_file}")
            logger.info("Note: This mode is intended for testing purposes only")

        # Configure ffmpeg
        configure_ffmpeg(args.ffmpeg_path)
        logger.info("FFMPEG configuration successful.")

        # Verify input file exists
        if not os.path.exists(args.input_file):
            raise FileNotFoundError(f"Input file not found: {args.input_file}")

        # Initialize Managers
        tts_config_path = Path(args.tts_config) if args.tts_config else Path("")
        tts_manager = TTSProviderManager(
            tts_config_path, args.provider, args.dummy_provider_override
        )
        logger.info("TTS provider manager initialized.")

        # Convert input file and processor config paths to Path objects
        input_file_path = Path(args.input_file) if args.input_file else None
        cmd_configs_paths = (
            [Path(p) for p in args.processor_configs]
            if args.processor_configs
            else None
        )

        generated_processor_configs = get_processor_configs(
            input_file_path, cmd_configs_paths
        )
        processor = TextProcessorManager(generated_processor_configs)
        logger.info(
            f"Text processor manager initialized with configs: {[str(p) for p in generated_processor_configs]}"  # Log as strings
        )

        # Load dialogues
        logger.info(f"Loading dialogues from: {args.input_file}")
        dialogues = load_json_chunks(args.input_file)
        logger.info(f"Loaded {len(dialogues)} dialogue chunks.")

    except Exception as e:
        logger.error(f"Setup failed: {e}", exc_info=True)
        sys.exit(1)  # Exit if setup fails

    # --- Core Processing ---
    combined_reporting_state = ReportingState()
    all_tasks: List[AudioGenerationTask] = []

    try:
        # 1. Plan Generation (Common to all modes)
        logger.info("\n--- Planning Audio Generation ---")
        all_tasks, plan_reporting_state = plan_audio_generation(
            dialogues=dialogues,
            tts_provider_manager=tts_manager,
            processor=processor,
            cache_folder=cache_folder,
            cache_overrides_dir=args.cache_overrides,
        )
        # Merge initial planning report state
        combined_reporting_state.cache_misses.update(plan_reporting_state.cache_misses)

        # Extract modified dialogues for saving later
        modified_dialogues = [task.processed_dialogue for task in all_tasks]

        # --- Mode-Specific Actions ---

        # 2. Apply Cache Overrides (not for dry-run, modifies tasks in-place)
        if not args.dry_run and args.cache_overrides:
            logger.info("\n--- Applying Cache Overrides ---")
            apply_cache_overrides(
                tasks=all_tasks,
                cache_overrides_dir=args.cache_overrides,
                cache_folder=cache_folder,
            )
            # Note: Reporting state might need updating here if an override fixed a silent clip,
            # but recheck_audio_files later should handle consistency.

        # 3. Check for Silence
        if args.check_silence:
            logger.info("\n--- Checking for Silent Audio Files ---")
            silence_reporting_state = check_for_silence(
                tasks=all_tasks,
                silence_threshold=args.check_silence,
            )
            # Merge silence report state
            combined_reporting_state.silent_clips.update(
                silence_reporting_state.silent_clips
            )

        # 4. Fetch/Generate Audio (Not for dry-run)
        if not args.dry_run:
            logger.info("\n--- Fetching any Non-Cached Aduio Files ---")
            # Fetch and cache the audio files
            fetch_reporting_state = fetch_and_cache_audio(
                tasks=all_tasks,
                tts_provider_manager=tts_manager,
                silence_threshold=args.check_silence,
            )

            # Merge fetch report state (only adds newly generated silent clips)
            combined_reporting_state.silent_clips.update(
                fetch_reporting_state.silent_clips
            )

            # Recheck file status after potential generation/overrides
            logger.info("\n--- Rechecking Cache Status ---")
            recheck_audio_files(
                combined_reporting_state, cache_folder, args.check_silence, logger
            )
            logger.info("Recheck complete")

        # 5. Concatenate Audio (Only for full run mode)
        if not args.dry_run and not args.populate_cache:
            logger.info("\n--- Concatenating Audio ---")

            # Use task-based concatenation function
            concatenate_tasks_batched(
                tasks=all_tasks,
                output_file=output_file,
                batch_size=args.concat_batch_size,
                gap_duration_ms=args.gap,
            )

            logger.info(f"\nFinal audio file generated: {output_file}")

            # Set ID3 tags
            optional_config_path = find_optional_config(
                args.optional_config, args.input_file
            )
            if optional_config_path:
                logger.info(f"Setting ID3 tags from config: {optional_config_path}")
                if set_id3_tags_from_config(output_file, optional_config_path):
                    logger.info("  ID3 tags set successfully.")
                else:
                    logger.warning(
                        "  Failed to set ID3 tags or no tags specified in config."
                    )
            else:
                logger.info("No optional config file found or specified for ID3 tags.")

    except Exception as e:
        logger.error(f"An error occurred during processing: {e}", exc_info=True)
        # Attempt to print report even if processing failed
        print_unified_report(
            reporting_state=combined_reporting_state,
            logger=logger,
            tts_provider_manager=tts_manager,
            silence_checking_enabled=args.check_silence is not None,
            max_misses_to_report=args.max_report_misses,
            max_text_length=args.max_report_text,
        )
        sys.exit(1)

    # --- Final Reporting ---
    logger.info("\n--- Final Report ---")
    print_unified_report(
        reporting_state=combined_reporting_state,
        logger=logger,
        tts_provider_manager=tts_manager,
        silence_checking_enabled=args.check_silence is not None,
        max_misses_to_report=args.max_report_misses,
        max_text_length=args.max_report_text,
    )

    # Save modified JSON regardless of run mode (useful for debugging)
    save_modified_json(modified_dialogues, output_folder, args.input_file)

    # --- Completion Summary ---
    logger.info(f"\n--- {run_mode.upper()} Mode Completed ---")
    logger.info(f"Log file: {log_file}")
    logger.info(f"Cache folder: {cache_folder}")
    if not args.dry_run and not args.populate_cache:
        logger.info(f"Output file: {output_file}")

    logger.info("Script finished.\n")


if __name__ == "__main__":
    main()
