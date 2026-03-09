# LLM Voice Labeling Guide

When adding a new TTS provider to the voice library, each voice needs to be labeled with properties like age, pitch, energy, accent, and more. Hand-labeling dozens of voices is tedious. The LLM voice labeling pipeline automates this by using multimodal LLMs to listen to audio samples and produce structured ratings.

The pipeline consists of two voice library scripts:

- **`llm_voice_calibrate`**: Validates the LLM prompt against known hand-labeled voices (OpenAI, ElevenLabs). Run once, or whenever you change models or prompts.
- **`llm_voice_labeler`**: Labels new provider voices and outputs a valid `voices.yaml`.

## Prerequisites

You need an [OpenRouter](https://openrouter.ai) API key. Set it as an environment variable:

```bash
export OPENROUTER_API_KEY="sk-or-..."
```

You also need valid API credentials for the TTS provider whose voices you're labeling (e.g., `MINIMAX_API_KEY` and `MINIMAX_GROUP_ID` for Minimax).

## Quick Start

### 1. Generate an input template

```bash
uv run sts-voice-library-run-script llm_voice_labeler minimax --generate-input-template
```

This creates `minimax_voice_input.yaml` with all of the provider's voices pre-populated:

```yaml
voices:
  wise_scholar:
    config:
      voice_id: English_WiseScholar
  confident_woman:
    config:
      voice_id: English_ConfidentWoman
  # ... all provider voices
```

### 2. Add provider metadata (optional but recommended)

Edit the generated file to add `provider_info` blocks. These hints help the LLM produce better descriptions and tags:

```yaml
voices:
  wise_scholar:
    config:
      voice_id: English_WiseScholar
      speed: 1.0                        # Optional provider parameters
      language_boost: English
    provider_info:
      provider_name: "Wise Scholar"
      provider_description: "A scholarly, thoughtful male voice"
      provider_use_cases: "Educational Narration"

  confident_woman:
    config:
      voice_id: English_ConfidentWoman
    provider_info:
      provider_name: "Confident Woman"

  sad_teen:
    config:
      voice_id: English_SadTeen
    # Minimal entry - LLM infers everything from audio alone
```

The `config` block is passed directly to the TTS provider for audio generation. Any required or optional provider fields (like `speed`, `emotion`, `language_boost`) can be included here.

### 3. Preview with dry run

```bash
uv run sts-voice-library-run-script llm_voice_labeler minimax \
  --input-config minimax_voice_input.yaml \
  --dry-run
```

This shows which voices will be processed and the total number of LLM calls without spending any money.

### 4. Run the labeler

```bash
uv run sts-voice-library-run-script llm_voice_labeler minimax \
  --input-config minimax_voice_input.yaml \
  --dual-clips
```

This will:
1. Generate two audio samples per voice: a **neutral clip** (weather/news text) and an **expressive clip** (dramatic dialogue)
2. Send both clips to the LLM for analysis (3 iterations by default)
3. Build consensus across runs
4. Output a valid `voices.yaml`

### 5. Review and validate

The output `voices.yaml` is written to both the run output directory and your user voice library path. Validate it:

```bash
uv run sts-validate-voice-library-data
```

## Dual Clips

The `--dual-clips` flag (recommended) generates two audio samples per voice:

- **Neutral clip**: Calm, conversational content (weather report, news). Used to ground baseline properties like pitch, pace, and energy.
- **Expressive clip**: Dramatic dialogue with whispers, shouts, and varied emotions. Used to assess the voice's range, performative ability, and character.

This gives the LLM two data points to triangulate, preventing the bias that occurs with a single clip (expressive-only makes everything seem theatrical; neutral-only makes everything seem flat).

## Per-Property Reasoning

Every LLM response includes a `reasoning` field with 1-2 sentence acoustic justifications for key properties (energy, performative, quality, range, authority). This reasoning is:

- **Stored in raw results**: Each `raw_results/<model>/<voice>_runN.json` file includes the full reasoning
- **Preserved in consensus**: The reasoning from the most representative run is included in the consensus output
- **Useful for debugging**: When a rating seems wrong, check the reasoning to understand what the model heard

Example reasoning output:
```json
{
  "reasoning": {
    "energy": "Moderate pitch movement and amplitude variance; attempts higher energy on shouts but remains acoustically restrained.",
    "quality": "Audio is clean with no artifacts, though some extreme emotional shifts reveal slight synthetic qualities.",
    "performative": "Animated delivery with dramatic pauses and timbre shifts between whispers and shouts."
  }
}
```

## Calibration

Before labeling a new provider, run calibration to verify the LLM prompt produces accurate results. Calibration runs the same analysis on voices with known hand-labeled properties and compares the results.

```bash
uv run sts-voice-library-run-script llm_voice_calibrate --dual-clips
```

### Calibration options

```bash
# Calibrate against both OpenAI and ElevenLabs
uv run sts-voice-library-run-script llm_voice_calibrate \
  --providers openai,elevenlabs --dual-clips

# Test specific voices only
uv run sts-voice-library-run-script llm_voice_calibrate \
  --sts-ids onyx,sage,fable --dual-clips

# Reuse audio from a previous run (prompt-only iteration)
uv run sts-voice-library-run-script llm_voice_calibrate \
  --providers openai,elevenlabs --dual-clips \
  --reuse-audio-from llm_calibrate_previous --output-dir llm_calibrate_new

# Use a different model
uv run sts-voice-library-run-script llm_voice_calibrate \
  --models google/gemini-3.1-pro-preview --dual-clips
```

### Reading the calibration report

The report shows:
- **Overall Range MAE**: Mean absolute error across all numeric properties (lower is better, aim for < 0.1)
- **Per-property MAE**: How accurately each property (age, pitch, energy, etc.) is predicted
- **Enum accuracy**: How often accent and gender are correctly identified
- **Worst voices**: Voices with the highest total error, worth investigating

If systematic biases appear (e.g., the model consistently rates energy too high), you can tune the prompt in `prompt_builder.py` and re-run calibration with `--reuse-audio-from` to iterate on the prompt without regenerating audio.

### Calibration results

The current prompt (with acoustic guidance and dual clips) achieves:
- **Overall MAE ~0.088** on well-characterized voices (OpenAI batch 2, ElevenLabs premade)
- **100% accuracy** on gender across all tested voices
- **~95% accuracy** on accent (Canadian/American distinction is ambiguous)
- Quality, performative, and energy are the hardest properties; reasoning output helps identify when GT labels may be wrong

## Labeler Options

```
uv run sts-voice-library-run-script llm_voice_labeler <provider> [options]

Required:
  provider              TTS provider name (e.g., minimax)

Options:
  --input-config FILE   Provider input config YAML (required unless --generate-input-template)
  --generate-input-template  Auto-generate starter config from provider's voice IDs
  --iterations N        LLM iterations per voice per model (default: 3)
  --models MODEL,...    Comma-separated OpenRouter model IDs (default: google/gemini-3.1-pro-preview)
  --dual-clips          Generate neutral + expressive audio clips per voice (recommended)
  --skip-audio-gen      Reuse existing audio samples
  --audio-dir DIR       Directory with pre-generated audio
  --output-dir DIR      Output directory (default: output/llm_labeler_<provider>_<timestamp>)
  --sts-ids ID,...    Process only specific sts_ids
  --dry-run             Preview without calling LLMs
  --from-raw-results DIR  Rebuild consensus + voices.yaml from a previous run's raw_results/ directory
```

### Processing a subset of voices

To label just a few voices (useful for testing):

```bash
uv run sts-voice-library-run-script llm_voice_labeler minimax \
  --input-config minimax_voice_input.yaml \
  --sts-ids wise_scholar,confident_woman,sad_teen \
  --dual-clips
```

### Reusing audio samples

If you've already generated audio and want to re-run just the LLM analysis (e.g., after prompt changes):

```bash
uv run sts-voice-library-run-script llm_voice_labeler minimax \
  --input-config minimax_voice_input.yaml \
  --skip-audio-gen \
  --audio-dir output/llm_labeler_minimax_20260307/audio \
  --dual-clips
```

### Crash recovery

Raw results are written to disk incrementally as each LLM call completes, so a crash mid-run won't lose completed work. To rebuild consensus and `voices.yaml` from a partial (or complete) run's raw results:

```bash
uv run sts-voice-library-run-script llm_voice_labeler minimax \
  --input-config minimax_voice_input.yaml \
  --from-raw-results output/llm_labeler_minimax_20260307_120000/raw_results
```

This skips audio generation and LLM analysis entirely, reading the existing JSON files from disk. You can also combine with `--sts-ids` to rebuild consensus for a subset of voices.

## Output Structure

Each run creates a directory under `output/` (which is gitignored) with full audit trail:

```
output/llm_labeler_minimax_20260307_120000/
  audio/                              # Generated audio samples
    minimax_wise_scholar_neutral.mp3  # Neutral clip (with --dual-clips)
    minimax_wise_scholar_expressive.mp3  # Expressive clip
  raw_results/
    google_gemini-3.1-pro-preview/    # Per-model raw LLM responses
      wise_scholar_run1.json          # Includes reasoning field
      wise_scholar_run2.json
      wise_scholar_run3.json
  consensus/
    per_model/                        # Within-model consensus
      google_gemini-3.1-pro-preview.json
    final/                            # Cross-model merged consensus
      wise_scholar.json               # Includes reasoning from representative run
      confident_woman.json
  voices.yaml                         # Final output
```

### Raw result JSON structure

Each `raw_results` file contains the full LLM response:

```json
{
  "voice_properties": {
    "accent": "american_general",
    "gender": "masculine",
    "age": 0.55,
    "authority": 0.65,
    "energy": 0.5,
    "pace": 0.45,
    "performative": 0.5,
    "pitch": 0.35,
    "quality": 0.95,
    "range": 0.6,
    "special_vocal_characteristics": null
  },
  "reasoning": {
    "energy": "Moderate pitch movement with slight amplitude spikes on stressed words...",
    "performative": "Maintains consistent narrator-like timbre without dramatic shifts...",
    "quality": "Audio is clean and clear with no noticeable artifacts...",
    "range": "Shows conversational pitch variance expanding into wider swings...",
    "authority": "Strong chest resonance with precise consonant articulation..."
  },
  "description": {
    "custom_description": "A warm, resonant baritone with measured delivery...",
    "perceived_age": "35-50 years"
  },
  "tags": {
    "character_types": ["narrator", "father", "detective"],
    "custom_tags": ["warm", "resonant", "measured", "deep"]
  }
}
```

## Provider Input Config

The input config YAML has three sections per voice:

### `config` (required)

The full provider configuration passed to the TTS API for audio generation. Must include all required fields for the provider:

```yaml
config:
  voice_id: English_WiseScholar     # Required for minimax
  speed: 1.0                        # Optional
  emotion: neutral                  # Optional
  language_boost: English           # Optional
```

For voice mixes (provider-specific feature):

```yaml
config:
  voice_mix:
    - voice_id: English_WiseScholar
      weight: 70
    - voice_id: English_GentleTeacher
      weight: 30
  speed: 0.9
```

### `provider_info` (optional)

Metadata included in the LLM prompt to improve description quality:

```yaml
provider_info:
  provider_name: "Wise Scholar"
  provider_description: "A scholarly, thoughtful male voice"
  provider_use_cases: "Educational Narration"
```

### `sts_id` (the YAML key)

The voice's key in the YAML becomes its `sts_id` in the output `voices.yaml`. The `--generate-input-template` command auto-generates these by slugifying the provider's voice IDs (e.g., `English_WiseScholar` becomes `wise_scholar`).

## How Consensus Works

The pipeline runs each voice through multiple LLM iterations and (optionally) multiple models, then aggregates:

- **Numeric properties** (age, pitch, energy, etc.): Median across runs, rounded to nearest 0.05
- **Enum properties** (accent, gender): Mode (most common value); ties are flagged for review
- **Text fields** (description, perceived_age): Taken from the run closest to the consensus medians ("representative run")
- **Reasoning**: Preserved from the representative run for debugging and review
- **List fields** (character_types, custom_tags): Items appearing in >= 50% of runs are included

The summary report flags:
- **High variance**: Properties where runs disagreed significantly (stdev > 0.15)
- **Enum ties**: When no clear majority for accent or gender
- **Failed voices**: Voices where all LLM calls failed

## Cost Estimate

Costs depend on the models used and the number of voices/iterations.

**Calibration** (one-time):
- 6 voices x 3 iterations x 1 model = 18 LLM calls, ~$0.50-1

**Per provider** (e.g., Minimax with 64 voices):
- Audio generation: ~$1 (128 TTS API calls with dual clips)
- LLM analysis: 64 voices x 3 iterations x 1 model = 192 calls, ~$4-8
- Total: ~$5-9 per provider

To reduce costs, use fewer iterations (`--iterations 1`).

## Troubleshooting

### "OPENROUTER_API_KEY environment variable is not set"
Export your OpenRouter API key: `export OPENROUTER_API_KEY="sk-or-..."`

### Rate limiting
The pipeline automatically retries with exponential backoff on rate limit errors. If you hit persistent limits, reduce the number of voices per batch.

### Poor accuracy on calibration
- Check the per-property reasoning in `raw_results/` to understand what the model is hearing
- Use `--reuse-audio-from` to iterate on the prompt without regenerating audio
- Listen to the generated audio samples — some TTS voices don't match their descriptions
- Consider adjusting the evaluation text or acoustic guidance in `prompt_builder.py`

### Schema validation fails on output
Run `uv run sts-validate-voice-library-data` to see specific errors. Common issues:
- Enum values not in the allowed list (e.g., accent misspelled)
- Range values outside 0.0-1.0

These indicate the LLM produced out-of-schema values and may require prompt tuning.

## Hand-Tuning Workflow

The LLM labeler produces a good starting point, but you may want to hand-tune specific values. The recommended workflow:

1. Run the labeler with `--dual-clips` to get initial ratings
2. Review the `voices.yaml` output and the reasoning in `raw_results/`
3. For voices where ratings seem off, listen to the audio clips and check the reasoning
4. Edit the `voices.yaml` values directly — the LLM ratings are a starting point, not gospel
5. Run `uv run sts-validate-voice-library-data` to ensure your edits are schema-valid

The reasoning field is especially useful here: if the model says "flat delivery with no pitch variance" but you hear an energetic voice, the audio sample may not have captured the voice's full range. Consider regenerating with different evaluation text.
