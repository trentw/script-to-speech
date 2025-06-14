# Script to Speech

Convert screenplays into multi-voiced audiobooks using various Text-to-Speech (TTS) providers.

## Overview

Script to Speech is a command-line tool that transforms screenplay files (PDF or TXT) into audiobooks with multiple voices. It handles screenplay parsing, speaker attribution, text processing, and audio generation through a flexible pipeline that supports combining multiple TTS providers to produce an audiobook.

### Key Features

- **Multi-provider support**: Use OpenAI, ElevenLabs, Cartesia, Minimax, Zonos, or custom TTS providers. TTS providers can be set at a per-speaker level
- **Text processing pipeline**: Customize how text is processed before audio generation
- **Multi-threaded downloads**: With separate queues per provider for faster generation
- **Silence detection**: Identify and replace silent audio clips
- **Cache system**: Resume interrupted generations and reuse audio. Change text / speaker assignments and only regenerte that specific audio
- **Voice casting assistance**: Generate prompts for LLM-assisted voice casting and validation

## Privacy & Data Handling

**Script to Speech Privacy**: This tool operates entirely locally on your machine and collects no user data, has no telemetry, tracking, or analytics, and makes no network requests except to the services required for its core functionality.

**Audio Generation**: To convert your screenplay text into speech, Script to Speech sends individual dialogue chunks to TTS providers (OpenAI, ElevenLabs, etc.) you configure. Each provider receives only the specific text being converted to audio.

**Voice Casting (Optional)**: If you choose to use the LLM-assisted voice casting feature, your complete screenplay text and voice configuration are sent to the LLM service you select to generate casting recommendations.

**Important**: Before using any TTS provider or LLM service, review their privacy policies, data retention practices, and training data policies to ensure they align with your privacy requirements.

See our [Privacy Policy](PRIVACY.md) for detailed information about data flows, recommendations for privacy-conscious usage, and contact information.

## CLI Commands

| Command                           | Description                        |
| --------------------------------- | ---------------------------------- |
| `sts-parse-screenplay`            | Parse PDF/TXT to JSON chunks       |
| `sts-generate-audio`              | Generate audiobook from JSON       |
| `sts-generate-standalone-speech`  | Create individual audio clips      |
| `sts-tts-provider-yaml`           | Generate/populate provider configs |
| `sts-analyze-json`                | Analyze screenplay structure       |
| `sts-apply-text-processors-json`  | Apply text transformations         |
| `sts-parse-regression-check-json` | Validate parser output             |
| `sts-generate-character-notes-prompt` | Generate LLM casting prompts   |
| `sts-copy-to-clipboard`           | Copy file contents to clipboard    |

## Quick Start

### Installation

1. **Install UV** (package manager)

   ```bash
   pip install uv
   ```

   For alternate / more detailed UV installation instructions, see [UV's documentation](https://docs.astral.sh/uv/getting-started/installation/).

2. **Create a copy of the project**
   Either [download](https://github.com/trentw/script-to-speech/archive/refs/heads/master.zip) the project, or use git to clone it:
   ```bash
   git clone https://github.com/trentw/script-to-speech.git
   cd script-to-speech
   ```

### For Basic Usage

No additional installation needed! UV will automatically install dependencies on first use.

### For Development

Install the package in editable mode:

```bash
uv pip install -e ".[dev]"
```

## Basic Workflow

### Step 1: Setup Accounts with TTS Services and Configure
Get an API key from at least one of the supported providers listed in the [TTS Providers documentation](docs/TTS_PROVIDERS.md) and add it to the project

```bash
# OpenAI
export OPENAI_API_KEY="your-api-key"

# ElevenLabs
export ELEVEN_API_KEY="your-api-key"

# Cartesia
export CARTESIA_API_KEY="your-api-key"

# Minimax
export MINIMAX_API_KEY="your-api-key"
export MINIMAX_GROUP_ID="your-group-id"

# Zonos
export ZONOS_API_KEY="your-api-key"
```

### Step 2: Add Screenplay

Place your screenplay PDF in the `source_screenplays` directory.

### Step 3: Parse Screenplay

```bash
# Parse PDF to JSON dialogue chunks
uv run sts-parse-screenplay source_screenplays/your_script.pdf
```

This creates:

- `input/your_script/your_script.pdf` (copy of original)
- `input/your_script/your_script.json` (parsed dialogue chunks)
- `input/your_script/your_script_optional_config.yaml` (configuration file to set values like ID3 tags for .mp3 file)

### Step 4: Generate TTS Provider Configuration

```bash
# Generate YAML config for a single provider
uv run sts-tts-provider-yaml generate input/your_script/your_script.json --tts-provider openai
```

This creates `input/your_script/your_script_voice_config.yaml`

### Step 5: Configure Voices

Edit the generated YAML file to assign voices to speakers (note that "default" is used for any items without an explicit speaker defined, such as scene headers, action lines, etc.):

```yaml
default:
  provider: openai
  voice: onyx
ALICE:
  provider: openai
  voice: echo
```

### Step 6: Configure ID3 Tags (Optional)

Edit `input/your_script/your_script_optional_config.yaml`:

```yaml
id3_tag_config:
  title: "My Audiobook"
  screenplay_author: "Your Name"
  date: "2024"
```

These tags will be added to the output .mp3 file, and are displayed in audio / audio book player apps

### Step 7: Generate Audio

```bash
# Generate the audiobook
uv run sts-generate-audio input/your_script/your_script.json \
  --tts-config input/your_script/your_script_voice_config.yaml
```

Your audiobook will be output at: `output/your_script/your_script.mp3`

## Advanced Workflow

### Advanced Screenplay Parsing

1. **Modifying screenplay .pdf to remove elements (dates / headers / footers / etc.)**

   ```bash
   # Parse screenplay .pdf to text
   uv run sts-parse-screenplay source_screenplays/your_script.pdf --text-only
   ```

   Manually edit `input/your_script/your_script.txt` to remove headers / footers / etc., then:

   ```bash
   # Create JSON dialogue chunks from edited text
   uv run sts-parse-screenplay input/your_script/your_script.txt
   ```

2. **Analyze Screenplay**

   ```bash
   # Check speakers and dialogue types
   uv run sts-analyze-json input/your_script/your_script.json
   ```

   This can be a useful sanity test to make sure the screenplay parsing worked as expected:

   - Do the speakers look correct?
   - Is there the right number of scene headers?
   - Are there corresponding numbers of dual-dialogue headers and bodies?
   - etc.

### Advanced Text Processor / TTS-Provider Configuration

3. **Create Multi-Provider Configuration**

   ```bash
   # Generate multi-provider configuration
   uv run sts-tts-provider-yaml generate input/your_script/your_script.json
   ```

   This creates a config with speaker statistics, and a field for each speaker at `input/your_script/your_script_voice_config_populated.yaml` which is meant to be populated with the intended TTS provider for each speaker

   ```yaml
   # default: 1556 lines - Used for all non-dialogue pieces
   # Total characters: 104244, Longest dialogue: 2082 characters
   default:
     provider:

   # ALICE: 283 lines
   # Total characters: 12181, Longest dialogue: 365 characters
   ALICE:
     provider:

   # BOB: 120 lines
   # Total characters: 9123, Longest dialogue: 253 characters
   ALICE:
     provider:
   ```

   Edit to assign TTS providers to each speaker. Note that if provider-specific fields are manually added, they will be persisted in the "populate" step (as seen in ALICE's case below). It is required that a provider be added for each speaker:

   ```yaml
   # default: 1556 lines - Used for all non-dialogue pieces
   # Total characters: 104244, Longest dialogue: 2082 characters
   default:
     provider: openai

   # ALICE: 283 lines
   # Total characters: 12181, Longest dialogue: 365 characters
   ALICE:
     provider: openai
     voice: alloy

   # BOB: 120 lines
   # Total characters: 9123, Longest dialogue: 253 characters
   ALICE:
     provider: elevenlab
   ```

   Populate provider-specific fields for each speaker:

   ```bash
   uv run sts-tts-provider-yaml populate input/your_script/your_script.json \
     input/your_script/your_script_voice_config.yaml
   ```

   This creates `input/your_script/your_script_voice_config_populated.yaml` grouped by provider:

   ```yaml
   # default: 1556 lines - Used for all non-dialogue pieces
   # Total characters: 104244, Longest dialogue: 2082 characters
   default:
     provider: openai
     voice:

   # ALICE: 283 lines
   # Total characters: 12181, Longest dialogue: 365 characters
   ALICE:
     provider: openai
     voice: alloy

   # BOB: 120 lines
   # Total characters: 9123, Longest dialogue: 253 characters
   ALICE:
     provider: elevenlab
     voice_id:
   ```

   Fill in the provider-specific fields as in the single-provider case. For provider-specific instructions, including optional fields, see the instructions header at the top of each provider grouping. For more information, see the [detailed TTS Provider documentation](docs/TTS_PROVIDERS.md)

### (Optional) LLM-Assisted Voice Casting 

> **⚠️ PRIVACY WARNING**: The `sts-generate-character-notes-prompt` command creates a prompt containing the **full text** of your screenplay. Before using any cloud-based LLM service:
> - Review their privacy policy and data usage practices
> - Ensure you're comfortable sharing your screenplay content
> - Consider whether the LLM provider uses uploaded content for training
> - For sensitive content, consider using local LLM solutions instead
> 
> See our [Privacy Policy](PRIVACY.md) for detailed guidance on privacy-conscious usage.

4. **Generate Voice Casting Prompt**

   For complex scripts with many characters, you can use an LLM to generate casting notes (gender, vocal qualities, role summary, etc.) for each speaker in the screenplay:

   ```bash
   # Generate a prompt file for LLM-assisted voice casting
   uv run sts-generate-character-notes-prompt \
     source_screenplays/your_script.pdf \
     input/your_script/your_script_voice_config.yaml
   ```

   This creates `input/your_script/your_script_voice_casting_prompt.txt` containing:
   - Instructions for the LLM to provide casting notes for each character in the voice configuration
   - Your current voice configuration
   - The full screenplay text

5. **Copy Prompt to Clipboard**

   ```bash
   # Copy the generated prompt to your clipboard for easy pasting into an LLM
   uv run sts-copy-to-clipboard input/your_script/your_script_voice_casting_prompt.txt
   ```

6. **Validate LLM Output**

   After receiving updated voice configuration from the LLM, validate it:

   ```bash
   # Check for missing/extra/duplicate speakers and provider field issues
   uv run sts-tts-provider-yaml validate input/your_script/your_script.json \
     input/your_script/your_script_voice_config.yaml
   ```

   Use the `--strict` flag to also validate provider-specific configuration fields:

   ```bash
   # Strict validation including provider field validation
   uv run sts-tts-provider-yaml validate input/your_script/your_script.json \
     input/your_script/your_script_voice_config.yaml --strict
   ```

### Custom Text Processing

7. **Custom Text Processing**

   Custom text processor configurations can be created that will chain with the default configuration. By default, the program will look for an additional configuration file named the same as the .json dialogue chunk file, with `_text_processor_config.yaml` appended.

   So, to create a custom config, create `input/your_script/your_script_text_processor_config.yaml`:

   ```yaml
   processors:
     - name: text_substitution
       config:
         substitutions:
           - from: "CU"
             to: "close up"
             fields:
               - text
           - from: "P.O.V"
             to: "point of view"
             fields:
               - text
   ```

   For further information about text existing text processor transformations, or how to create your own, see [Text Processing Guide](docs/TEXT_PROCESSORS.md)

### Iterative Audio Generation with Various Run Modes
  Script to Speech supports a number of run modes to test and iteratively build dialogue clips before generating the final .mp3 output. For detailed information beyond what is listed below, see the [run modes documentation](docs/RUN_MODES.md)

   8. **Dry Run Testing**

   ```bash
   uv run sts-generate-audio input/your_script/your_script.json \
     --tts-config input/your_script/your_script_voice_config_populated.yaml \
     --dry-run
   ```

   Validates configuration and shows which files would be generated without actual audio creation
   
  **Use Cases:**

  - Validating configuration files are valid
  - Determining which audio files will be generated (useful when a speaker / dialogue chunk has been modified, and you want to see which files will be regenerated)
  - When used in combination with the `--check-silence` option described below to check for silent clips without attempting to regenerate them

   9. **Populate cache with Silence Detection**
   ```bash
   uv run sts-generate-audio input/your_script/your_script.json \
     --tts-config input/your_script/your_script_voice_config_populated.yaml \
     --populate-cache --check-silence
   ```

   Cache population will download clips without actually generating the .mp3 output file. Used in conjunction with the `--check-silence` flag, this can be a useful way to ensure that there aren't any problem files prior to generating the output .mp3
   **Use Cases**
   - Replacing silent clips prior to .mp3 output
   - Quality checking important pieces of dialogue, and replacing them with better "takes" 
   - Checkig price / quality / etc. before committing to full audio generation -- if the process is killed, it will resume downloading only new dialogues on next execution
   - Applying the `--cache-overrides` option described below

   10. **Replace Silent Clips / "Re-Audition" Specific Clips**
   Specific lines of dialogue can be generated with `sts-generate-standalone-speech`. Multiple lines can be supplied at once. The `-v` flag will determine how many "take" wil be generated for each line. These files will be output to the `standalone_speech` directory

   ```bash
   # Generate replacement audio
   uv run sts-generate-standalone-speech openai --voice echo \
     "Replace this silent text number 1" \
     "Replace this silent text number 2" \
     -v 3 # (optional) generate 3 variations of each line
   ```

  Rename generated file to match silent cache file name as reported in the console output, or in the log files at `output/your_script/logs`:

   ```bash
   mv standalone_speech/generated_file.mp3 \
     standalone_speech/[original_cache_filename].mp3
   ```

   11. **Apply Replacements**

   ```bash
   uv run sts-generate-audio input/your_script/your_script.json \
     --tts-config input/your_script/your_script_voice_config_populated.yaml \
     --populate-cache --cache-overrides --check-silence
   ```

   Replaces silent clips with generated audio and continues downloading any missing audio files

   12. **Repeat** until all audio is cached, then generate final output:

   ```bash
   uv run sts-generate-audio input/your_script/your_script.json \
     --tts-config input/your_script/your_script_voice_config_populated.yaml
   ```

   Combines all cached audio into the final audiobook

## Directory Structure
Script to Speech uses a number of default locations to simplify workflows. The following lists standard files you will likely encounter while running the program. Directories `input/[screenplay_name]` and `output/[screenplay_name]` will automatically be created when the screenplay is parsed. 

```
source_screenplays/                   # Original screenplay files
input/
└── [screenplay_name]/
    ├── [screenplay_name].pdf         # Copied screenplay
    ├── [screenplay_name].txt         # Extracted text (if parser run with --text-only)
    ├── [screenplay_name].json        # Parsed dialogue chunks
    ├── [screenplay_name]_optional_config.yaml          # ID3 tag configuration
    ├── [screenplay_name]_text_processor_config.yaml    # (optional) Custom text processors
    ├── [screenplay_name]_voice_config.yaml             # TTS provider config
    ├── [screenplay_name]_voice_config_populated.yaml   # TTS provider config populated with multi-provider options
    └── [screenplay_name]_voice_casting_prompt.txt      # (optional) LLM casting prompt

output/
└── [screenplay_name]/
    ├── [screenplay_name].mp3                  # Final audiobook
    ├── [screenplay_name]-text-processed.json  # Dialogue chunks with text processors applied
    ├── cache/                                 # Generated audio clips
    └── logs/                                  # Parsing and generation logs

standalone_speech/                             # Override audio files
```

## Run Modes

- **Default**: Generate complete audiobook
- **--dry-run**: Test configuration without generating audio
- **--populate-cache**: Generate and cache audio only (no final MP3)

See [RUN_MODES.md](doc/RUN_MODES.md) for detailed information.

## Text Processing

Script to Speech supports flexible text processing through preprocessors and processors:

- **Preprocessors**: Modify the dialogue structure
- **Processors**: Transform individual text lines

See [TEXT_PROCESSORS.md](docs/TEXT_PROCESSORS.md) for configuration details.

## TTS Providers

Supported TTS providers:

- **OpenAI**: Preview voices at [openai.fm](https://www.openai.fm/)
- **ElevenLabs**: Requires "Creator" plan, uses public library voices
- **Cartesia**: TTS with a free plan and a number of voices
- **Minimax**: TTS with voice mixing capabilities and emotion control
- **Zonos**: TTS service with a free plan and a few voices
- **Dummy**: Testing only

See [TTS_PROVIDERS.md](docs/TTS_PROVIDERS.md) for provider-specific configuration.

## Advanced Topics

### Sharing Cache for Re-casting

The `input` and `output` folders (including cache) can be shared between users to reuse audio when changing select voices:

1. Share `input/[screenplay_name]` and `output/[screenplay_name]` folders
2. Edit voice configuration for desired speakers
3. Run with existing cache to preserve unchanged audio

### Multi-threaded Downloads

Downloads are multi-threaded with separate queues per provider. Distributing voices across TTS providers speeds up generation.

### Cache Management

Generated audio is cached in `output/[screenplay_name]/cache/`. Cache files are uniquely named based on:

- Speaker configuration
- TTS provider
- Text content
- Processing parameters

Changes in any of the above will mark just the relevant clips for regeneration upon the next run 

## Troubleshooting

### Common Issues

1. **Silent Audio Detected**

   - Use `--check-silence` to identify silent clips
   - Generate replacements with `sts-generate-standalone-speech`
   - Apply with `--cache-overrides`

2. **Rate Limiting**
   - Each provider has different rate limits
   - The tool automatically handles backoff
   - Spread voices across TTS providers to avoid limits

3. **Voice Configuration Errors**
   - Use `sts-tts-provider-yaml validate` to check for missing/extra/duplicate speakers
   - Use `--strict` flag to validate provider-specific fields
   - Check voice IDs match provider requirements

4. **Screenplay is parsed incorrectly**
   - The parser is currently fairly fragile, and expects "standard" screenplay files with predictable margins and conventions. Additional configuration options, and automatic configuration, is planned for future releases

See [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for more solutions.

## Environment Variables

Required for TTS providers:

- `OPENAI_API_KEY`: OpenAI API access
- `ELEVEN_API_KEY`: ElevenLabs API access
- `CARTESIA_API_KEY`: Cartesia API access
- `MINIMAX_API_KEY`: Minimax API access
- `MINIMAX_GROUP_ID`: Minimax Group ID
- `ZONOS_API_KEY`: Zonos API access

### Using .env Files (Recommended)

For local development, you can use a `.env` file to store your API keys instead of setting them as environment variables in your shell. This approach is more convenient and for developers, helps prevent accidental exposure of your keys.

1. Copy the provided `.env.example` file to a new file named `.env` in the project root:
   ```bash
   cp .env.example .env
   ```

2. Edit the `.env` file and add your API keys:
   ```
   OPENAI_API_KEY="your-openai-key-here"
   ELEVEN_API_KEY="your-elevenlabs-key-here"
   # Add other keys as needed
   ```

3. The application will automatically load these variables when it starts.

**Note**: The `.env` file is excluded from version control via `.gitignore` to prevent accidentally committing your API keys. Never commit your actual API keys to version control.

## License

MIT licensed. See [LICENSE](LICENSE) for more information