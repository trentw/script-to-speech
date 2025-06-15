"""Command-line interface for generating voice library casting prompts."""

import argparse
from pathlib import Path
from typing import List

from .voice_casting_common import handle_cli_errors
from .voice_library_casting_utils import generate_voice_library_casting_prompt_file


def parse_arguments() -> argparse.Namespace:
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate a text file prompt for LLM-assisted voice casting using voice library data.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "voice_config_path",
        type=Path,
        help="Path to the voice configuration YAML file.",
    )
    parser.add_argument(
        "providers",
        nargs="+",
        help="One or more TTS provider names (e.g., 'openai', 'elevenlabs').",
    )
    parser.add_argument(
        "--prompt-file",
        dest="prompt_file_path",
        type=Path,
        default=None,
        help="Optional path to a custom prompt text file. If not provided, a default prompt is used.",
    )
    parser.add_argument(
        "--output-file",
        dest="output_file_path",
        type=Path,
        default=None,
        help="Optional path for the output file. If not provided, will be generated based on the voice config file name.",
    )
    return parser.parse_args()


@handle_cli_errors
def main() -> None:
    """Main execution function for the CLI."""
    args = parse_arguments()

    output_file_path = generate_voice_library_casting_prompt_file(
        voice_config_path=args.voice_config_path,
        providers=args.providers,
        prompt_file_path=args.prompt_file_path,
        output_file_path=args.output_file_path,
    )

    config_name = args.voice_config_path.stem
    output_file_name = output_file_path.name
    providers_str = ", ".join(args.providers)

    print(f"\nSuccessfully generated voice library casting prompt file:")
    print(f"  {output_file_path}")
    print(f"  Including voice library data for providers: {providers_str}")
    print(f"\n⚠️  PRIVACY NOTICE:")
    print(
        f"   This optional feature includes voice configuration data from '{args.voice_config_path.name}'"
    )
    print(
        f"   which includes a list of character names, and potentially character casting notes,"
    )
    print(f"   and voice library data for the specified providers.")
    print(f"   Before uploading to any LLM service:")
    print(f"   • Review the service's privacy policy and data usage practices")
    print(f"   • Ensure you're comfortable sharing your voice configuration details")
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
        f"2. After the LLM processes the content and provides updated YAML with voice library selections:"
    )
    print(f"3. Carefully copy the LLM's YAML output.")
    print(
        f"4. Replace the existing content of your voice configuration file with the YAML output from the LLM."
    )
    print(
        f"   (Ensure the LLM has updated character voice assignments using the available voice library options)"
    )
    print(
        f"5. (optional) Validate that the LLM output is a valid voice configuration file."
    )
    print(f"   Example validation command:")
    print(
        f"     uv run sts-tts-provider-yaml validate '[screenplay].json' '{args.voice_config_path}'"
    )


if __name__ == "__main__":
    main()
