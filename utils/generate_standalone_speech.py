import argparse
from typing import Dict, Any, Type, List
import os
from datetime import datetime
import re
import importlib
from utils.logging import get_screenplay_logger
from tts_providers.base.tts_provider import TTSProvider

logger = get_screenplay_logger("utils.generate_standalone_speech")


def clean_filename(text: str) -> str:
    """Convert text to valid filename."""
    cleaned = re.sub(r'[^\w\s-]', '', text)
    return cleaned.replace(' ', '_')


def get_provider_class(provider_name: str) -> Type[TTSProvider]:
    """Get the provider class for a given provider name."""
    try:
        module = importlib.import_module(
            f"tts_providers.{provider_name}.tts_provider")

        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and
                issubclass(attr, TTSProvider) and
                attr != TTSProvider and
                    attr.get_provider_identifier() == provider_name):
                return attr

        raise ValueError(f"No valid provider class found for {provider_name}")
    except ImportError as e:
        raise ValueError(f"Provider '{provider_name}' not found: {e}")


def generate_standalone_speech(
    provider: TTSProvider,
    text: str,
    variant_num: int = 1,
    output_dir: str = "standalone_speech"
) -> None:
    """
    Generate speech using specified provider.

    Args:
        provider: Initialized TTS provider
        text: Text to convert to speech
        variant_num: Variant number when generating multiple versions
        output_dir: Directory for output files
    """
    try:
        # Generate speech using default speaker
        audio_data = provider.generate_audio(None, text)

        # Create timestamp for unique filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # Create filename
        text_preview = clean_filename(text[:30])
        variant_suffix = f"_variant{variant_num}" if variant_num > 1 else ""
        provider_id = provider.get_provider_identifier()
        voice_id = provider.get_speaker_identifier(
            None)  # Get default voice ID
        filename = f"{provider_id}--{voice_id}--{text_preview}{variant_suffix}--{timestamp}.mp3"
        output_path = os.path.join(output_dir, filename)

        # Save audio
        with open(output_path, "wb") as f:
            f.write(audio_data)

        logger.info(f"Generated speech file: {output_path}")

    except Exception as e:
        logger.error(f"Error generating speech: {e}")


def get_command_string(provider_name: str, voice_id: str, texts: List[str]) -> str:
    """Generate command line string for standalone speech generation.

    Args:
        provider_name: Name of the TTS provider
        voice_id: Voice identifier
        texts: List of text strings to convert

    Returns:
        Command line string that can be used to generate the audio
    """
    try:
        # Get provider class to determine required fields
        provider_class = get_provider_class(provider_name)
        required_fields = provider_class.get_required_fields()

        if not required_fields:
            logger.error(
                f"No required fields found for provider {provider_name}")
            return ""

        # Build command with first required field as voice parameter
        # TODO: Assumes only one required parameter to define voice
        # TODO: TTS providers could return "clean" voice id instead of having
        #       to depend on splitting by underscore
        trimmed_voice_id = voice_id.split(
            "_")[0] if "_" in voice_id else voice_id
        voice_param = f"--{required_fields[0]} {trimmed_voice_id}"
        texts_quoted = [f'"{t}"' for t in texts]

        return f"python -m utils.generate_standalone_speech {provider_name} {voice_param} {' '.join(texts_quoted)}"
    except Exception as e:
        logger.error(f"Error generating command string: {e}")
        return ""


def main():
    # Get available providers
    available_providers = []
    for item in os.listdir("tts_providers"):
        if os.path.isdir(os.path.join("tts_providers", item)) and item not in ['base', '__pycache__']:
            try:
                get_provider_class(item)
                available_providers.append(item)
            except ValueError:
                continue

    parser = argparse.ArgumentParser(
        description='Generate speech files using TTS providers.')
    parser.add_argument('provider', choices=available_providers,
                        help='TTS provider to use')

    # Get provider class to determine required fields
    provider_class = get_provider_class(parser.parse_known_args()[0].provider)
    required_fields = provider_class.get_required_fields()

    # Add arguments for each required field
    for field in required_fields:
        parser.add_argument(f'--{field}', required=True,
                            help=f'Required {field} parameter for {parser.parse_known_args()[0].provider}')

    parser.add_argument('texts', nargs='+',
                        help='Text strings to convert to speech')
    parser.add_argument('--variants', '-v', type=int, default=1,
                        help='Number of variants to generate for each text (default: 1)')
    parser.add_argument('--output-dir', default='standalone_speech',
                        help='Directory for output files (default: standalone_speech)')

    args = parser.parse_args()

    # Create provider configuration with just the required voice settings
    config = {
        'default': {field: getattr(args, field) for field in required_fields}
    }

    try:
        # Initialize provider
        provider = provider_class()
        provider.initialize(config)

        # Generate speech for each text string
        for text in args.texts:
            for variant in range(1, args.variants + 1):
                generate_standalone_speech(
                    provider=provider,
                    text=text,
                    variant_num=variant if args.variants > 1 else 1,
                    output_dir=args.output_dir
                )

    except Exception as e:
        logger.error(f"Error: {e}")
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
