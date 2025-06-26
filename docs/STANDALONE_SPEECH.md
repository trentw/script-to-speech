# Standalone Speech Generation Guide

Script to Speech provides powerful command-line tools for generating audio clips outside of the main screenplay processing workflow. These tools are essential for testing voices, replacing faulty audio, and generating sample clips in bulk.

This guide covers two key utilities:
- `sts-generate-standalone-speech`: For generating one or more individual audio clips, given a single voice.
- `sts-batch-generate-standalone-speech`: For bulk-generating audio from a list of voices, ideal for testing and voice library evaluation.

## Single Clip Generation: `sts-generate-standalone-speech`

This utility allows you to generate an audio file for a specific line of text using any supported TTS provider and voice.

### Purpose
- **Testing Voices**: Quickly hear how a specific voice sounds with a line of dialogue.
- **Fixing Audio**: Re-generate a line of dialogue that was silent, mispronounced, or had the wrong emotional tone. This is a core part of the [silent audio troubleshooting workflow](./TROUBLESHOOTING.md#1-silent-audio-detection).
- **Creating One-Offs**: Generate audio for any purpose without needing a full screenplay structure.

### Command Structure
The basic command follows this pattern:
```bash
uv run sts-generate-standalone-speech [provider] [provider_options] "text_to_generate"
```

- `[provider]`: The name of the TTS provider (e.g., `openai`, `elevenlabs`).
- `[provider_options]`: Provider-specific flags to select a voice. Any required or optional parameter for a TTS provider can be used as a command-line argument with a `--` prefix (e.g., `--voice_id`, `--speed`).
- `"text_to_generate"`: The text to be converted to speech. Can include multiple pieces of text.

### Common Usage

#### Basic Example
To generate a simple clip with OpenAI's `echo` voice:
```bash
uv run sts-generate-standalone-speech openai --voice echo "Hello, world!"
```

#### Generating with Optional Parameters
To generate a clip with Minimax, specifying the speed and emotion:
```bash
uv run sts-generate-standalone-speech minimax --voice_id English_WiseScholar --speed 1.2 --emotion happy "A happy, fast-talking character."
```

#### Generating Multiple Clips
You can pass multiple text strings to generate separate audio files for each.
```bash
uv run sts-generate-standalone-speech openai --voice alloy "First line." "Second line."
```

#### Generating Multiple Versions
To generate several variations of a clip (useful when a TTS provider gives inconsistent results), use the `-v` or `--versions` flag.
```bash
# Generates 3 different versions of the same text
uv run sts-generate-standalone-speech openai --voice fable "A critical line of dialogue." -v 3
```

### Generating from the Voice Library (`--sts_id`)

You can use the `--sts_id` argument to generate audio using a pre-defined voice from your voice library. This simplifies the command by removing the need to specify every provider parameter.

```bash
# Generate audio using an ElevenLabs voice from the library
uv run sts-generate-standalone-speech elevenlabs --sts_id eric "This is a test."
```

You can also override specific parameters when using `--sts_id`.

```bash
# Override the stability of an ElevenLabs voice from the library
uv run sts-generate-standalone-speech elevenlabs --sts_id eric --override_param 0.6 "This is a less stable test."
```

### Output Files
- **Location**: All generated clips are saved in the `standalone_speech/` directory.
- **Naming**: Files are named using a hash of their content and provider details to avoid collisions. For example: `openai--echo--Hello_world--20250625_120000.mp3`.
- **Custom Filename**: You can specify a custom filename using the `--output_filename` parameter. For example: `--output_filename my_custom_filename` will create `my_custom_filename.mp3`.

When replacing silent clips, you will need to rename the generated file to match the original cache filename reported in the logs. See the [Troubleshooting Guide](./TROUBLESHOOTING.md) for more details.

## Batch Generation: `sts-batch-generate-standalone-speech`

This utility is designed to generate the same line of text across a wide range of voices from one or more providers. It's perfect for creating a voice library showcase or for comparing different voices for casting.

### Command Structure
This tool takes a single YAML configuration file as an argument.
```bash
uv run sts-batch-generate-standalone-speech [path_to_config.yaml]
```

### Configuration File
The YAML file can have three main sections: `text`, `sts_ids`, and `configs`.

```yaml
# sample_batch_config.yaml
text: >
  Here is a line of text that can be used to test the quality and
  style of different voices. It should be long enough to capture
  the nuances of the speaker's delivery.

sts_ids:
  elevenlabs:
    - "antoni"
    - "laura"
    - "thomas"
  
  openai:
    - "nova"

configs:
  - provider: openai
    voice: alloy
  - provider: minimax
    voice_id: English_WiseScholar
    speed: 1.2
    emotion: happy
```

- `text`: A string containing the dialogue to be generated. Multi-line strings are supported.
- `sts_ids`: A dictionary where each key is a TTS provider name (e.g., `elevenlabs`). The value is a list of `sts_id`s from the voice library for that provider.
- `configs`: A list of dictionaries, where each dictionary represents a specific voice configuration. This is useful for testing voices that are not in the voice library, or for testing specific parameter combinations.

### Output Files
- **Location**: All generated clips are saved in the `standalone_speech/` directory.
- **Naming**: Files are named to be easily identifiable, including the provider, voice ID, a snippet of the text, and a timestamp.
- **Custom Filename**: For `sts_ids` based generation, you can add a suffix to the filename using the `--filename_addition` parameter. For example: `--filename_addition my_test` will create files like `elevenlabs_antoni_my_test.mp3`.