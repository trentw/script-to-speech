import argparse
import logging
import os
import sys
from pathlib import Path
from typing import List, Optional

import yaml
from pydub import AudioSegment
from tqdm import tqdm

from .audio_generation.log_messages import PipelinePhase, log_completion, log_phase
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
from .audio_generation.utils import concatenate_tasks_batched, load_json_chunks
from .text_processors.processor_manager import TextProcessorManager
from .text_processors.utils import get_text_processor_configs
from .tts_providers.tts_provider_manager import TTSProviderManager
from .utils.audio_utils import configure_ffmpeg
from .utils.file_system_utils import create_output_folders, save_processed_dialogues
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
        "tts_provider_config", help="Path to YAML configuration file for TTS provider."
    )
    parser.add_argument(
        "--gap",
        type=int,
        default=500,
        help="Gap duration between dialogues in milliseconds.",
    )
    parser.add_argument(
        "--text-processor-configs",
        nargs="*",
        help="Path(s) to YAML configuration file(s) for text (pre)processors. "
        "Multiple paths can be provided.",
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
        "--max-workers",
        type=int,
        default=12,
        help="Maximum number of concurrent workers for audio generation/download.",
    )
    parser.add_argument(
        "--dummy-tts-provider-override",
        action="store_true",
        help="Override configured TTS providers with dummy TTS providers for testing purposes. "
        "This will replace configured TTS providers with dummy_stateful/dummy_stateless TTS providers.",
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
    tts_manager = None
    try:
        # Create output folders using the unified utility function
        main_output_folder, cache_folder, logs_folder, log_file = create_output_folders(
            args.input_file, run_mode, args.dummy_tts_provider_override
        )

        # Construct output file path for the final MP3
        input_path_obj = Path(args.input_file)
        base_name = input_path_obj.stem
        output_filename = f"{base_name}.mp3"
        if args.dummy_tts_provider_override:
            output_filename = f"dummy_{output_filename}"
        output_file = main_output_folder / output_filename

        # Setup logging (must happen after log_file path is determined)
        setup_screenplay_logging(str(log_file))
        logger.info(f"Logging initialized. Log file: {log_file}")
        logger.info(f"Run mode: {run_mode}")
        if args.check_silence is not None:
            logger.info(
                f"Silence checking enabled: Threshold = {args.check_silence} dBFS"
            )
        if args.cache_overrides:
            logger.info(f"Cache overrides enabled. Directory: {args.cache_overrides}")
        if args.dummy_tts_provider_override:
            logger.info("DUMMY TTS PROVIDER OVERRIDE MODE ENABLED")
            logger.info(
                "All configured TTS providers will be replaced with dummy TTS providers and produce dummy audio"
            )
            logger.info(f"Using dummy cache folder: {cache_folder}")
            if output_file:
                logger.info(f"Using dummy output file: {output_file}")
            logger.info("Note: This mode is intended for testing purposes only")

        # Configure ffmpeg using static-ffmpeg
        configure_ffmpeg()
        logger.info("FFMPEG configuration successful using static-ffmpeg.")

        # Verify input file exists
        if not os.path.exists(args.input_file):
            raise FileNotFoundError(f"Input file not found: {args.input_file}")

        # Initialize Managers
        tts_provider_config_data_loaded = {}
        tts_provider_config_path_obj = Path(args.tts_provider_config)
        if not tts_provider_config_path_obj.exists():
            raise FileNotFoundError(
                f"TTS provider configuration file not found: {tts_provider_config_path_obj}"
            )

        with open(tts_provider_config_path_obj, "r", encoding="utf-8") as f:
            tts_provider_config_data_loaded = yaml.safe_load(f)

        if not isinstance(tts_provider_config_data_loaded, dict):
            raise ValueError(
                f"Invalid YAML format in {tts_provider_config_path_obj}: "
                "root must be a mapping (dictionary)."
            )
        if not tts_provider_config_data_loaded:  # Check if the dictionary is empty
            raise ValueError(
                f"TTS provider configuration file '{tts_provider_config_path_obj}' "
                "is empty or provides no configuration data."
            )

        tts_manager = TTSProviderManager(
            config_data=tts_provider_config_data_loaded,
            overall_provider=None,
            dummy_tts_provider_override=args.dummy_tts_provider_override,
        )
        logger.info("TTS provider manager initialized.")

        # Convert input file and processor config paths to Path objects
        input_file_path = Path(args.input_file) if args.input_file else None
        cmd_configs_paths = (
            [Path(p) for p in args.text_processor_configs]
            if args.text_processor_configs
            else None
        )

        generated_text_processor_configs = get_text_processor_configs(
            input_file_path, cmd_configs_paths
        )
        processor = TextProcessorManager(generated_text_processor_configs)
        logger.info(
            f"Text processor manager initialized with configs: {[str(p) for p in generated_text_processor_configs]}"  # Log as strings
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
        log_phase(logger, PipelinePhase.PLANNING)
        all_tasks, plan_reporting_state = plan_audio_generation(
            dialogues=dialogues,
            tts_provider_manager=tts_manager,
            processor=processor,
            cache_folder=str(cache_folder),
            cache_overrides_dir=args.cache_overrides,
        )
        # Merge initial planning report state
        combined_reporting_state.cache_misses.update(plan_reporting_state.cache_misses)

        # Extract modified dialogues for saving later
        modified_dialogues = [task.processed_dialogue for task in all_tasks]

        # --- Mode-Specific Actions ---

        # 2. Apply Cache Overrides (not for dry-run, modifies tasks in-place)
        if not args.dry_run and args.cache_overrides:
            log_phase(logger, PipelinePhase.OVERRIDES)
            apply_cache_overrides(
                tasks=all_tasks,
                cache_overrides_dir=args.cache_overrides,
                cache_folder=str(cache_folder),
            )
            # Note: Reporting state might need updating here if an override fixed a silent clip,
            # but recheck_audio_files later should handle consistency.

        # 3. Check for Silence
        if args.check_silence:
            log_phase(logger, PipelinePhase.SILENCE)
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
            log_phase(logger, PipelinePhase.FETCH)
            # Fetch and cache the audio files
            fetch_reporting_state = fetch_and_cache_audio(
                tasks=all_tasks,
                tts_provider_manager=tts_manager,
                silence_threshold=args.check_silence,
                max_workers=args.max_workers,
            )

            # Merge fetch report state (only adds newly generated silent clips)
            combined_reporting_state.silent_clips.update(
                fetch_reporting_state.silent_clips
            )

            # Recheck file status after potential generation/overrides
            log_phase(logger, PipelinePhase.RECHECK)
            recheck_audio_files(
                combined_reporting_state, str(cache_folder), args.check_silence, logger
            )

        # 5. Concatenate Audio (Only for full run mode)
        if not args.dry_run and not args.populate_cache:
            log_phase(logger, PipelinePhase.CONCAT)

            # Use task-based concatenation function
            concatenate_tasks_batched(
                tasks=all_tasks,
                output_file=str(output_file),
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
                if set_id3_tags_from_config(str(output_file), optional_config_path):
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
        # Check if tts_manager is bound before using it
        if tts_manager is not None:
            print_unified_report(
                reporting_state=combined_reporting_state,
                logger=logger,
                tts_provider_manager=tts_manager,
                silence_checking_enabled=args.check_silence is not None,
                max_misses_to_report=args.max_report_misses,
                max_text_length=args.max_report_text,
            )
        else:
            logger.error(
                "TTS provider manager was not initialized due to a setup error. Cannot print detailed report."
            )
        sys.exit(1)

    # --- Final Reporting ---
    log_phase(logger, PipelinePhase.FINAL_REPORT)
    # Check if tts_manager is bound before using it
    if tts_manager is not None:
        print_unified_report(
            reporting_state=combined_reporting_state,
            logger=logger,
            tts_provider_manager=tts_manager,
            silence_checking_enabled=args.check_silence is not None,
            max_misses_to_report=args.max_report_misses,
            max_text_length=args.max_report_text,
        )
    else:
        logger.warning(
            "TTS provider manager was not initialized. Cannot print detailed final report."
        )

    # Save modified JSON regardless of run mode (useful for debugging)
    # Ensure modified_dialogues is defined even if processing failed
    if modified_dialogues:
        save_processed_dialogues(modified_dialogues, main_output_folder, base_name)
    else:
        logger.warning("Modified dialogues not available to save.")

    # --- Completion Summary ---
    log_completion(
        logger,
        run_mode,
        log_file,
        cache_folder,
        output_file if not args.dry_run and not args.populate_cache else None,
    )


if __name__ == "__main__":
    main()
