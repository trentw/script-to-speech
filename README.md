# Script to Speech

Convert screenplays into multi-voiced audiobooks using various Text-to-Speech (TTS) providers.

Script to Speech is available in two versions:

1.  **Desktop GUI (Experimental)**: A modern, easy-to-use desktop application. Recommended for new users.
2.  **Command Line Interface (CLI)**: The core, feature-complete tool. Recommended for advanced users and automation.

| Feature | Desktop GUI | CLI |
| :--- | :--- | :--- |
| **Ease of Use** | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| **Features** | Core Features | All Features |
| **Stability** | Experimental | Stable |
| **Documentation** | [GUI User Guide](docs/GUI_USER_GUIDE.md) | [CLI Documentation](#cli-usage) |

---

## Key Features

- **Multi-provider support**: Use OpenAI, ElevenLabs, Cartesia, Minimax, Zonos, or custom TTS providers. TTS providers can be set at a per-speaker level
- **Text processing pipeline**: Customize how text is processed before audio generation
- **Multi-threaded downloads**: With separate queues per provider for faster generation
- **Silence detection**: Identify and replace silent audio clips
- **Cache system**: Resume interrupted generations and reuse audio. Change text / speaker assignments and only regenerte that specific audio
- **Voice casting assistance**: Generate prompts for LLM-assisted character notes and voice library casting

## Privacy & Data Handling

**Script to Speech Privacy**: This tool operates entirely locally on your machine and collects no user data, has no telemetry, tracking, or analytics, and makes no network requests except to the services required for its core functionality.

**Audio Generation**: To convert your screenplay text into speech, Script to Speech sends individual dialogue chunks to TTS providers (OpenAI, ElevenLabs, etc.) you configure. Each provider receives only the specific text being converted to audio.

**Voice Casting (Optional)**: If you choose to use the LLM-assisted voice casting feature, your complete screenplay text and voice configuration are sent to the LLM service you select to generate casting recommendations.

**Important**: Before using any TTS provider or LLM service, review their privacy policies, data retention practices, and training data policies to ensure they align with your privacy requirements.

See our [Privacy Policy](PRIVACY.md) for detailed information about data flows, recommendations for privacy-conscious usage, and contact information.

---

## CLI Usage

The following documentation covers the **Command Line Interface**. For GUI instructions, please see the [GUI User Guide](docs/GUI_USER_GUIDE.md).

## CLI Commands

| Command                           | Description                        |
| --------------------------------- | ---------------------------------- |
| `sts-parse-screenplay`            | Parse PDF/TXT to JSON chunks       |
| `sts-generate-audio`              | Generate audiobook from JSON       |
| `sts-generate-standalone-speech`  | Create individual audio clips. See [Standalone Speech Generation](docs/STANDALONE_SPEECH.md) for more details. |
| `sts-tts-provider-yaml`           | Generate/populate provider configs |
| `sts-analyze-json`                | Analyze screenplay structure       |
| `sts-apply-text-processors-json`  | Apply text transformations         |
| `sts-parse-regression-check-json` | Validate parser output             |
| `sts-generate-character-notes-prompt` | Generate LLM casting prompts   |
| `sts-generate-voice-library-casting-prompt` | Generate voice library casting prompts |
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
  input/your_script/your_script_voice_config.yaml
```

Your audiobook will be output at: `output/your_script/your_script.mp3`

## Advanced Workflow

The basic workflow will handle most screenplay-to-audiobook conversions, but Script to Speech offers many advanced features for complex projects, quality optimization, and fine-tuned control. This section covers advanced techniques you can use as needed:

- **Advanced parsing** for non-standard screenplays
- **Multi-provider setups** to optimize cost and voice variety
- **LLM-assisted casting** for complex character rosters
- **Custom text processing** for screenplay-specific formatting
- **Iterative generation** to ensure quality before final output

Each technique can be used independently based on your project's needs.

### Advanced Screenplay Parsing

Sometimes you'll need more control over the parsing process, especially when dealing with non-standard screenplay formats or PDFs with headers/footers that interfere with parsing.

**Modifying screenplay PDFs to remove unwanted elements:**

```bash
# Parse screenplay .pdf to text
uv run sts-parse-screenplay source_screenplays/your_script.pdf --text-only
```

Manually edit `input/your_script/your_script.txt` to remove headers, footers, page numbers, or any other elements that shouldn't be part of the audio, then:

```bash
# Create JSON dialogue chunks from edited text
uv run sts-parse-screenplay input/your_script/your_script.txt
```

**Analyzing the parsed screenplay:**

After parsing, it's good practice to verify the results:

```bash
# Check speakers and dialogue types
uv run sts-analyze-json input/your_script/your_script.json
```

This helps ensure the screenplay parsing worked as expected:
- Do the speakers look correct?
- Is there the right number of scene headers?
- Are there corresponding numbers of dual-dialogue headers and bodies?
- Are any characters being split incorrectly (e.g., "BOB" vs "BOB (O.S.)")?

### Multi-Provider Voice Configuration

For larger projects, you may want to use different TTS providers for different characters to optimize cost, quality, or voice variety.

**Generate a multi-provider template:**

Start by generating a configuration file that shows statistics for each speaker:

```bash
# Generate multi-provider configuration
uv run sts-tts-provider-yaml generate input/your_script/your_script.json
```

This creates a config with speaker statistics at `input/your_script/your_script_voice_config.yaml`:

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
BOB:
  provider:
```

**Assign providers to speakers:**

Edit the file to assign TTS providers based on character importance, line count, and voice requirements. You can also add provider-specific fields at this stage:

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
BOB:
  provider: elevenlabs
```

**Populate provider-specific fields:**

Once providers are assigned, populate the remaining provider-specific fields:

```bash
uv run sts-tts-provider-yaml populate input/your_script/your_script.json \
  input/your_script/your_script_voice_config.yaml
```

This creates `input/your_script/your_script_voice_config_populated.yaml` with provider-specific fields grouped by provider. Fill in the required fields for each provider according to the instructions at the top of each section. For detailed provider information, see the [TTS Providers documentation](docs/TTS_PROVIDERS.md).

### (Optional) LLM-Assisted Voice Casting 

Script to Speech provides two LLM-assisted tools that work together to help cast voices for your screenplay characters:

1. **Character Notes Generation** - Analyzes your screenplay to create casting notes for each character
2. **Voice Library Casting** - Uses those notes to select specific voices from provider voice libraries

> **⚠️ PRIVACY WARNING**: 
> - `sts-generate-character-notes-prompt` creates a prompt containing the **full text** of your screenplay
> - `sts-generate-voice-library-casting-prompt` creates a prompt containing your character list and any casting notes (but not the screenplay text)
> 
> Before using any cloud-based LLM service:
> - Review their privacy policy and data usage practices
> - Ensure you're comfortable sharing your content
> - Consider whether the LLM provider uses uploaded content for training
> - For sensitive content, consider using local LLM solutions or manually configuring voices
> 
> See our [Privacy Policy](PRIVACY.md) for detailed guidance on privacy-conscious usage.

#### Step 1: Generate Character Notes (Optional)

For complex scripts with many characters, you can use an LLM to generate casting notes (gender, vocal qualities, role summary, etc.) for each speaker:

```bash
# Generate a prompt file for LLM-assisted character analysis
uv run sts-generate-character-notes-prompt \
  source_screenplays/your_script.pdf \
  input/your_script/your_script_voice_config.yaml
```

This creates `input/your_script/your_script_character_notes_prompt.txt` containing:
- Instructions for the LLM to provide casting notes for each character
- Your current voice configuration
- The full screenplay text

#### Step 2: Copy Prompt to Clipboard

```bash
# Copy the generated prompt to your clipboard for easy pasting into an LLM
uv run sts-copy-to-clipboard input/your_script/your_script_character_notes_prompt.txt
```

#### Step 3: Update Configuration with Character Notes

After receiving the LLM's output with character notes added as YAML comments, save the updated configuration back to your voice config file.

#### Step 4: Cast Voices from Library (Optional)

Once you have character notes (either from the LLM or manually added), you can use voice library casting to automatically select appropriate voices:

```bash
# Generate a prompt for voice library casting
uv run sts-generate-voice-library-casting-prompt \
  input/your_script/your_script_voice_config.yaml \
  openai elevenlabs
```

This creates `input/your_script/your_script_voice_config_voice_library_casting_prompt.txt` containing:
- Instructions for the LLM to select voices from the specified provider libraries
- Your voice configuration with character notes
- Voice library data for the specified providers

Note: You can specify multiple providers (e.g., `openai elevenlabs cartesia`) to cast from multiple voice libraries simultaneously.

#### Step 5: Apply Voice Selections

Copy the prompt to clipboard and paste into your LLM:

```bash
uv run sts-copy-to-clipboard input/your_script/your_script_voice_config_voice_library_casting_prompt.txt
```

The LLM will return your configuration with `sts_id` fields populated with specific voice selections from the libraries.

#### Step 6: Validate Configuration

After receiving updated voice configuration from the LLM, validate it:

```bash
# Check for missing/extra/duplicate speakers and provider field issues
uv run sts-tts-provider-yaml validate input/your_script/your_script.json \
  input/your_script/your_script_voice_config.yaml --strict
```

#### Privacy-Conscious Alternative Workflow

For sensitive screenplays, you can skip character notes generation and manually add casting notes:

1. Manually edit your voice configuration to add character descriptions as YAML comments
2. Use only `sts-generate-voice-library-casting-prompt` (which doesn't include screenplay text)
3. This way, only character names and your notes are shared with the LLM, not the screenplay content

### Custom Text Processing

Script to Speech allows you to customize how text is processed before being sent to TTS providers. This is useful for expanding abbreviations, handling special formatting, or adjusting capitalization.

Custom text processor configurations will chain with the default configuration. By default, the program looks for a file named after your dialogue chunk file with `_text_processor_config.yaml` appended.

To create a custom config, create `input/your_script/your_script_text_processor_config.yaml`:

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

For more information about text processor transformations and creating your own, see the [Text Processing Guide](docs/TEXT_PROCESSORS.md).

### Iterative Audio Generation with Run Modes

Script to Speech supports various run modes to test and iteratively refine your audiobook before generating the final output. This workflow is particularly useful for large projects where you want to ensure quality before committing to full generation.

**Dry Run Testing**

Start by validating your configuration without generating any audio:

```bash
uv run sts-generate-audio input/your_script/your_script.json \
  input/your_script/your_script_voice_config.yaml \
  --dry-run
```

Use cases:
- Validating configuration files
- Determining which audio files will be generated
- Checking for potential issues before spending on API calls

**Building the Audio Cache**

Generate all audio clips without creating the final MP3:

```bash
uv run sts-generate-audio input/your_script/your_script.json \
  input/your_script/your_script_voice_config.yaml \
  --populate-cache --check-silence
```

This approach allows you to:
- Check for silent or problematic clips before final generation
- Build your cache incrementally (process can be resumed if interrupted)
- Review individual clips for quality
- Replace specific clips with better "takes"

**Replacing Problem Audio**

If silent clips are detected or you want to re-record specific lines:

```bash
# Generate replacement audio
uv run sts-generate-standalone-speech openai --voice echo \
  "Replace this silent text number 1" \
  "Replace this silent text number 2" \
  -v 3  # Generate 3 variations of each line
```

Rename the generated file to match the cache filename (as reported in console output or logs):

```bash
mv standalone_speech/generated_file.mp3 \
  standalone_speech/[original_cache_filename].mp3
```

Apply the replacements:

```bash
uv run sts-generate-audio input/your_script/your_script.json \
  input/your_script/your_script_voice_config.yaml \
  --populate-cache --cache-overrides --check-silence
```

See [Standalone Speech Generation](docs/STANDALONE_SPEECH.md) for more details and usage options

**Final Generation**

Once all audio is cached and verified:

```bash
uv run sts-generate-audio input/your_script/your_script.json \
  input/your_script/your_script_voice_config.yaml
```

This combines all cached audio into the final audiobook with proper gaps and ID3 tags.

For detailed information about all available run modes and options, see the [Run Modes documentation](docs/RUN_MODES.md).

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
    ├── [screenplay_name]_character_notes_prompt.txt      # (optional) LLM character notes prompt
    └── [screenplay_name]_voice_config_voice_library_casting_prompt.txt  # (optional) LLM voice library casting prompt

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
