"""Command-line interface for generating voice casting prompts."""

import argparse
import sys
import traceback
from pathlib import Path

import yaml  # For YAMLError

from .casting_utils import generate_voice_casting_prompt_file


def parse_arguments() -> argparse.Namespace:
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate a text file prompt for LLM-assisted voice casting.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "source_screenplay_path",
        type=Path,
        help="Path to the source screenplay file (.txt or .pdf).",
    )
    parser.add_argument(
        "tts_provider_config_path",
        type=Path,
        help="Path to the TTS provider configuration YAML file.",
    )
    parser.add_argument(
        "--prompt-file",
        dest="prompt_file_path",
        type=Path,
        default=None,
        help="Optional path to a custom prompt text file. If not provided, a default prompt is used.",
    )
    return parser.parse_args()


def main() -> None:
    """Main execution function for the CLI."""
    args = parse_arguments()

    try:
        output_file_path = generate_voice_casting_prompt_file(
            source_screenplay_path=args.source_screenplay_path,
            tts_provider_config_path=args.tts_provider_config_path,
            prompt_file_path=args.prompt_file_path,
        )

        screenplay_name = args.source_screenplay_path.stem
        output_file_name = output_file_path.name

        print(f"\nSuccessfully generated voice casting prompt file:")
        print(f"  {output_file_path}")
        print(
            f"\nWARNING: The full text content of '{args.source_screenplay_path.name}' is included in this prompt."
        )
        print(
            f"Make sure to understand the data collection policies of any non-local LLM to which you may be supplying this prompt"
        )
        print(f"\nTo use this file with an LLM for voice casting:")
        print(
            f"1. Upload the file '{output_file_name}' to your preferred LLM interface."
        )
        print(f"     --OR--")
        print(
            f"   Run the following command to copy the prompt to your clipboard, for easy pasting:"
        )
        print(f"     uv run sts-copy-to-clipboard '{output_file_path}'")
        print(
            f"2. After the LLM processes the content and provides updated YAML for character notes:"
        )
        print(f"3. Carefully copy the LLM's YAML output.")
        print(
            f"4. Open your original TTS voice configuration file (e.g., input/{screenplay_name}/{screenplay_name}_voice_config.yaml)."
        )
        print(
            f"5. Replace the existing content of the TTS voice configuration file with the YAML output from the LLM."
        )
        print(
            f"   (Ensure you are replacing the character definitions and their provider details,"
        )
        print(
            f"    incorporating the new casting notes and role descriptions as comments)."
        )

    except FileNotFoundError as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"\nError processing TTS provider config YAML: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nAn unexpected error occurred:", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
