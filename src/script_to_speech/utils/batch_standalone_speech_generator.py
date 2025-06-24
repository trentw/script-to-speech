import argparse
import os
from typing import Any, Dict, List, Optional, Union

import yaml

from ..tts_providers.tts_provider_manager import TTSProviderManager
from .generate_standalone_speech import generate_standalone_speech, get_provider_class
from .logging import get_screenplay_logger

logger = get_screenplay_logger("utils.batch_standalone_speech_generator")


def load_batch_config(yaml_path: str) -> Dict[str, Any]:
    """Load and validate batch configuration from YAML file."""
    try:
        with open(yaml_path, "r") as f:
            config = yaml.safe_load(f)

        if not isinstance(config, dict):
            raise ValueError("YAML file must contain a dictionary")

        if "text" not in config:
            raise ValueError("YAML file must contain a 'text' field")

        if not isinstance(config["text"], str):
            raise ValueError("'text' field must be a string")

        # Validate that at least one of sts_ids or configs is provided
        if "sts_ids" not in config and "configs" not in config:
            raise ValueError(
                "YAML file must contain either 'sts_ids' or 'configs' field"
            )

        return config

    except FileNotFoundError:
        raise ValueError(f"YAML file not found: {yaml_path}")
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing YAML file: {e}")


def process_sts_ids(
    sts_ids_config: Dict[str, List[str]], text: str, args: argparse.Namespace
) -> None:
    """Process sts_ids configuration and generate speech files."""
    # Count total sts_ids
    total_sts_ids = sum(len(sts_id_list) for sts_id_list in sts_ids_config.values())
    current_sts_id = 0

    for provider_name, sts_id_list in sts_ids_config.items():
        logger.info(
            f"--- Processing provider: {provider_name} ({len(sts_id_list)} sts_ids)"
        )

        for sts_id in sts_id_list:
            current_sts_id += 1
            logger.info(
                f"\n> Processing sts_id {current_sts_id}/{total_sts_ids}: {sts_id}"
            )

            try:
                # Build TTS config for this sts_id
                tts_provider_config_data = {
                    "default": {"provider": provider_name, "sts_id": sts_id}
                }

                # Create TTSProviderManager
                tts_manager = TTSProviderManager(
                    config_data=tts_provider_config_data,
                    overall_provider=None,
                    dummy_tts_provider_override=False,
                )

                # Generate speech with custom filename
                output_filename = f"{provider_name}_{sts_id}"
                if args.filename_addition:
                    output_filename += f"_{args.filename_addition}"

                for variant in range(1, args.variants + 1):
                    generate_standalone_speech(
                        tts_manager=tts_manager,
                        text=text,
                        variant_num=variant if args.variants > 1 else 1,
                        output_dir=args.output_dir,
                        split_audio=args.split_audio,
                        silence_threshold=args.silence_threshold,
                        min_silence_len=args.min_silence_len,
                        keep_silence=args.keep_silence,
                        output_filename=output_filename,
                    )

            except Exception as e:
                logger.error(
                    f"Error processing sts_id {sts_id} for provider {provider_name}: {e}"
                )
                continue

        logger.info("")  # Blank line after each provider


def process_configs(
    configs_list: List[Dict[str, Any]], text: str, args: argparse.Namespace
) -> None:
    """Process configs list and generate speech files."""
    for i, config in enumerate(configs_list):
        logger.info(f"\n> Processing config {i + 1}/{len(configs_list)}")

        if not isinstance(config, dict):
            logger.error(f"Config {i + 1} is not a dictionary, skipping")
            continue

        if "provider" not in config:
            logger.error(f"Config {i + 1} missing 'provider' field, skipping")
            continue

        provider_name = config["provider"]

        try:
            # Get provider class and validate config
            provider_class = get_provider_class(provider_name)

            # Build TTS config
            tts_provider_config_data = {"default": config.copy()}

            # Validate the config
            provider_class.validate_speaker_config(tts_provider_config_data["default"])

            # Create TTSProviderManager
            tts_manager = TTSProviderManager(
                config_data=tts_provider_config_data,
                overall_provider=None,
                dummy_tts_provider_override=False,
            )

            # Generate speech with default naming (no custom filename)
            for variant in range(1, args.variants + 1):
                generate_standalone_speech(
                    tts_manager=tts_manager,
                    text=text,
                    variant_num=variant if args.variants > 1 else 1,
                    output_dir=args.output_dir,
                    split_audio=args.split_audio,
                    silence_threshold=args.silence_threshold,
                    min_silence_len=args.min_silence_len,
                    keep_silence=args.keep_silence,
                )

        except Exception as e:
            logger.error(f"Error processing config {i + 1}: {e}")
            continue


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate batch speech files from YAML configuration."
    )
    parser.add_argument("yaml_file", help="Path to YAML configuration file")
    parser.add_argument(
        "--variants",
        "-v",
        type=int,
        default=1,
        help="Number of variants to generate for each configuration (default: 1)",
    )
    parser.add_argument(
        "--output-dir",
        default="standalone_speech",
        help="Directory for output files (default: standalone_speech)",
    )

    # Add split audio arguments
    parser.add_argument(
        "--split-audio",
        action="store_true",
        help="Enable split audio mode - splits after constant sentence",
    )
    parser.add_argument(
        "--silence-threshold",
        type=int,
        default=-40,
        help="Silence threshold in dBFS for splitting (default: -40)",
    )
    parser.add_argument(
        "--min-silence-len",
        type=int,
        default=500,
        help="Minimum silence length in ms for splitting (default: 500)",
    )
    parser.add_argument(
        "--keep-silence",
        type=int,
        default=100,
        help="Amount of silence to keep in ms after splitting (default: 100)",
    )
    parser.add_argument(
        "--filename-addition",
        type=str,
        default="",
        help="Additional text to append to output filename (only for sts_id cases)",
    )

    args = parser.parse_args()

    try:
        # Load batch configuration
        config = load_batch_config(args.yaml_file)
        text = config["text"]

        # Configure ffmpeg if using split audio method
        if args.split_audio:
            try:
                from .audio_utils import configure_ffmpeg

                configure_ffmpeg()
            except Exception as e:
                logger.error(f"Error configuring ffmpeg: {e}")
                return 1

        # Create output directory
        os.makedirs(args.output_dir, exist_ok=True)

        # Process sts_ids if provided
        if "sts_ids" in config:
            total_sts_ids = sum(
                len(sts_id_list) for sts_id_list in config["sts_ids"].values()
            )
            total_providers = len(config["sts_ids"])
            logger.info(
                f"### Processing sts_ids configuration ({total_providers} providers, {total_sts_ids} total sts_ids)"
            )
            process_sts_ids(config["sts_ids"], text, args)
            logger.info("")  # Blank line between sections

        # Process configs if provided
        if "configs" in config:
            total_configs = len(config["configs"])
            logger.info(
                f"### Processing configs configuration ({total_configs} configs)"
            )
            process_configs(config["configs"], text, args)

        logger.info("\nBatch speech generation completed")
        return 0

    except Exception as e:
        logger.error(f"Error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
