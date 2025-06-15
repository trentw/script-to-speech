"""Command-line interface for generating voice casting prompts."""

import argparse
from pathlib import Path

from .character_notes_utils import generate_voice_casting_prompt_file
from .voice_casting_common import handle_cli_errors


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


@handle_cli_errors
def main() -> None:
    """Main execution function for the CLI."""
    args = parse_arguments()

    output_file_path = generate_voice_casting_prompt_file(
        source_screenplay_path=args.source_screenplay_path,
        tts_provider_config_path=args.tts_provider_config_path,
        prompt_file_path=args.prompt_file_path,
    )

    screenplay_name = args.source_screenplay_path.stem
    output_file_name = output_file_path.name

    print(f"\nSuccessfully generated voice casting prompt file:")
    print(f"  {output_file_path}")
    print(f"\n⚠️  PRIVACY NOTICE:")
    print(
        f"   This optional feature includes the COMPLETE TEXT of '{args.source_screenplay_path.name}'"
    )
    print(f"   Before uploading to any LLM service:")
    print(f"   • Review the service's privacy policy and data usage practices")
    print(f"   • Ensure you're comfortable sharing your screenplay content")
    print(f"   • Consider whether the service uses your content for AI training")
    print(f"   • Alternative: Skip LLM assistance and configure voices manually")
    print(f"   • For sensitive content, consider local LLM solutions")
    print(f"   See PRIVACY.md for detailed guidance on privacy-conscious usage.")
    print(f"\nTo use this file with an LLM for voice casting:")
    print(f"1. Upload the file '{output_file_name}' to your preferred LLM interface.")
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
    print(
        f"6. (optional) Check that the LLM output a valid voice configuration file (no missing / duplicate / extra speakers)."
    )
    print(f"   Example command using `uv run sts-tts-provider-yaml validate`:")
    print(
        f"     uv run sts-tts-provider-yaml validate 'input/{screenplay_name}/{screenplay_name}.json' \\"
    )
    print(f"       'input/{screenplay_name}/{screenplay_name}_voice_config.yaml'")


if __name__ == "__main__":
    main()
