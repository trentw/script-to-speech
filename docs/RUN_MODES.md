# Audio Generation Run Modes Guide

Script to Speech supports multiple execution modes to handle different stages of the audio generation process. This guide explains each mode and when to use them.

## Available Run Modes

### Default Mode (Full Generation)
**Command**: No special flag needed
```bash
uv run sts-generate-audio input/script.json --tts-config config.yaml
```

**Purpose**: Complete audio file generation

**What it does**:
1. Loads and processes dialogue chunks
2. Applies text processors
3. Generates missing audio files
4. Concatenates audio into final MP3
5. Applies ID3 tags if configured

**Use when**: Ready to create final audiobook output

### Dry Run Mode
**Command**: `--dry-run`
```bash
uv run sts-generate-audio input/script.json --tts-config config.yaml --dry-run
```

**Purpose**: Configuration validation and planning

**What it does**:
1. Validates configuration files
2. Shows which audio files would be generated
3. Reports cache status
4. No actual audio generation

**Use when**:
- Testing configuration changes
- Estimating generation time
- Checking speaker assignments
- Smoke testing before full run

### Populate Cache Mode
**Command**: `--populate-cache`
```bash
uv run sts-generate-audio input/script.json --tts-config config.yaml --populate-cache
```

**Purpose**: Audio generation without final combination into audio file

**What it does**:
1. Generates and caches all audio files
2. No final MP3 creation
3. Preserves individual audio clips

**Use when**:
- Building cache for later use
- Testing audio quality individually
- Handling silent audio issues
- Ensuring all audio files are generated before combining into audio file
- Preparing for re-casting voices

## Run Mode Combinations

### With Silence Detection
Audio generation runs can include optional **silence detection** to flag clips that may be too quiet or improperly generated.

Silence detection evaluates the **peak volume** (in dBFS) of each audio clip. If the **loudest point** in the clip is **below the configured threshold**, it's considered "silent" and flagged.

```bash
# Dry run with silence check
uv run sts-generate-audio --dry-run --check-silence

# Populate cache with silence detection
uv run sts-generate-audio --populate-cache --check-silence

# Full run with silence check and custom silence threshold
uv run sts-generate-audio --check-silence -30
```

**Silence threshold (in dBFS)**:
The `--check-silence` flag accepts a float threshold value (in decibels relative to full scale).
Lower values allow quieter audio; higher values are more strict.

**dBFS Quick Reference:**

- 0 dBFS = maximum possible digital volume
- Negative values = quieter
- -inf dBFS = absolute digital silence

**Common Thresholds and Use Cases**
| Threshold         | Effect                                | Use Case                                      |
| ----------------- | ------------------------------------- | --------------------------------------------- |
| `-40.0` (default) | Balanced – flags clearly silent clips | Good default for most use cases               |
| `-30.0`           | More sensitive – flags quieter clips  | Use if **some silent clips sneak through**    |
| `-50.0`           | Less sensitive – allows quiet clips   | Use if **non-silent clips are being flagged as silent** |

**Troubleshooting Guide**
- "Some silent clips snuck through"*
   - If you're hearing nearly inaudible clips in your final output:
      - Raise the threshold (e.g. `--check-silence -30`)
      - This makes the detection more sensitive, flagging quieter clips
- "Some clips are being wrongly flagged as silent"
   - If valid audio is being incorrectly flagged as silent:
      - Lower the threshold (e.g. --check-silence -50)
      - This allows quiet but valid audio to pass the check

**Tip:** When `--check-silence` is used, the dBFS level of each clip will be recorded in the debug logs at `output/[screenplay]/logs`

### With Cache Overrides
Replace silent or problematic audio with `--cache-overrides`. When this run mode is used:
1. The cache override directory will be checked for any files that match the filename of cache files. By default, the cache-overrides directory is `standalone_speech`, but a custom directory can be supplied
2.  If any matching files are found in the override directory, they will be moved to the cache directory for the current screenplay
3. The rest of the audio generation process will continue as normal

```bash
# Use standalone_speech directory for overrides
uv run sts-generate-audio --populate-cache --cache-overrides

# Specify custom override directory
uv run sts-generate-audio --populate-cache --cache-overrides custom_dir/
```

**Tip**: This is also a good way to replace a specific audio clip with a new "take" if it is important that a line is delivered in a certain way

## Typical Workflows

### Initial Generation
1. **Validate configuration**
   ```bash
   uv run sts-generate-audio --dry-run
   ```

2. **Generate audio**
   ```bash
   uv run sts-generate-audio
   ```

### Handling Silent Audio
1. **Identify silent clips**
   ```bash
   uv run sts-generate-audio --populate-cache --check-silence
   ```

2. **Generate replacements**
   ```bash
   uv run sts-generate-standalone-speech openai --voice echo "replacement text"
   ```

3. **Apply overrides**
   ```bash
   uv run sts-generate-audio --populate-cache --cache-overrides --check-silence
   ```

4. **Repeat until all audio is valid**
   
5. **Create final output**
   ```bash
   uv run sts-generate-audio
   ```


## Command Reference

### Global Options
```bash
uv run sts-generate-audio [input_json] \
  --tts-config [config.yaml] \
  [run_mode] \
  [additional_options]
```

### Run Mode Flags
- `--dry-run`: Configuration validation only; no files audio clips will be downloaded
- `--populate-cache`: Generate audio without combination into final audio file

### Additional Options
- `--check-silence [dBFS]`: Detect silent audio (default: -40.0)
- `--cache-overrides [dir]`: Replace audio from directory
- `--gap [ms]`: Gap inserted between audio clips (default: 500)
- `--max-report-misses [n]`: Maximum number of cache misses / silent clips for which to print generation commands (default: 20)
- `--max-report-text [n]`: Maximum text length for clips included in cache miss / silent clip generation commands (default: 30)
- `--concat-batch-size [n]`: Batch size for audio clip concatenation (default: 250)
- `--max-workers [n]`: Maximum number of concurrent workers for audio generation/download (default: 12)

## Advanced Usage

### Custom Gap Timing Between Clips
```bash
# Shorter gaps for faster narration
uv run sts-generate-audio --gap 300

# Longer gaps for slower pace
uv run sts-generate-audio --gap 800
```

### Reporting Control
```bash
# Generate clip generation commands for higher number of missing / silent clips
uv run sts-generate-audio --check-silence --max-report-misses 50

# Output generation commands for longer dialogue clips
uv run sts-generate-audio --check-silence --max-report-text 70
```

## Performance Considerations

### Mode Selection for Speed
1. **Development**: Use `--dry-run` for quick testing
2. **Quality Check**: Use `--populate-cache` with `--check-silence`
3. **Final Generation**: Use default mode after cache is built

### Memory Management
Large projects in memory constrained situations may benefit from:
- Smaller batch sizes (`--concat-batch-size 100`)
- Reducing concurrent download maximum (`--max-workers` 5)

## Output and Logging

### Output Locations
- **Dry Run**: `output/[script]/[script]-modified.json`
- **Populate Cache**: Additionally, `output/[script]/cache/` directory
- **Full Generation**: Additionally, `output/[script]/[script].mp3`

### Log Files
- **Run logs**: `output/[script]/logs/`
- **Named by timestamp**: `log_YYYYMMDD_HHMMSS.txt`
- **Named by mode**: `[dry-run]_log_...txt`

## Troubleshooting Run Modes

### Dry Run Issues
- Check configuration file paths
- Validate API keys are set
- Ensure JSON is properly formatted

### Populate Cache Issues
- Monitor disk space for large projects
- Check provider rate limiting
- Verify network connectivity

### Full Generation Issues
- Ensure sufficient disk space for final MP3
- Check for silent audio before final generation
- Validate all required files are present

## Best Practices

### Mode Selection
1. Always start with `--dry-run`
2. Use `--populate-cache` for large projects
3. Handle silent audio before final generation
4. Test configuration changes with `--dry-run`

### Incremental Development
1. Process sections individually by addition to the input `[script].json` once previous section is verified working 
2. Use `--populate-cache` to build cache gradually

### Quality Assurance
1. Use `--check-silence` regularly
2. Test audio quality from sample characters
3. Validate configuration with `--dry-run`
4. Keep backup of working configurations

## Examples

### Complete Quality Workflow
```bash
# 1. Initial validation
uv run sts-generate-audio script.json --tts-config config.yaml --dry-run

# 2. Generate with quality checks
uv run sts-generate-audio script.json --tts-config config.yaml \
  --populate-cache --check-silence -30

# 3. Fix silent audio
uv run sts-generate-standalone-speech openai --voice echo \
  "Previously silent text 1 " "Previously silent text 2 "

# 4. Apply fixes, after files in standalone_speech have been renamed to match cache
uv run sts-generate-audio script.json --tts-config config.yaml \
  --populate-cache --cache-overrides --check-silence

# 5. Final generation, once all clips are confirmed cast
uv run sts-generate-audio script.json --tts-config config.yaml
```