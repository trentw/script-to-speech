# Troubleshooting Guide

This guide helps resolve common issues when using Script to Speech.

## Common Issues

### 1. Silent Audio Detection

**Problem**: Generated audio clips are silent or nearly silent. This seems to occur most frequently with short / single-word clips in TTS providers other than ElevenLabs

**Symptoms**:
- Warnings about silent clips in logs
- Audio files with low dBFS readings
- Partially silent audiobooks

**Solutions**:

1. **Identify Silent Clips**
   ```bash
   uv run sts-generate-audio script.json --tts-config config.yaml \
     --populate-cache --check-silence
   ```

2. **Generate Replacements**
Running `sts-generate-audio` with the `--check-silence` flag will generate pre-populated `sts-generate-standalone-speech` commands which just need to be copy and pasted
   ```bash
   # Copy reported text exactly
   # -v flag controls how many generations versions of each clip to generate
   uv run sts-generate-standalone-speech openai --voice echo \
     "silent text 1" "silent text 2" -v 3
   ```

3. **Manual Rename**
   ```bash
   # Match exact cache filename from report
   mv standalone_speech/generated_file.mp3 \
     standalone_speech/[original_cache_filename].mp3
   ```

4. **Apply Overrides**
This will move any cache-matching files from standalone_speech to the screenplay's cache directory
   ```bash
   uv run sts-generate-audio script.json --tts-config config.yaml \
     --populate-cache --cache-overrides
   ```

**Prevention**:
- Use `--check-silence` during initial generation
- Consider alternative TTS providers for troublesome text (ElevenLabs rarely seems to have issues with silent clips)

### 2. Rate Limiting

**Problem**: API requests are being rate limited.

**Symptoms**:
- Rate limit error messages
- Delayed audio generation
- Automatic retries and backoff

**Solutions**:

1. **Automatic Handling**
   - The system automatically retries with exponential backoff
   - Each provider has separate rate limit handling
   - Future versions of Script to Speech will allow for more manual control of thread limits and backoff behavior

2. **Reduce Global Concurrent Downloads
Note that this will limit the overall (cross-provider) maximum concurrent downloads
   ```bash
   uv run sts-generate-audio --max-workers 5
   ```

2. **Distribute Across TTS Providers**
   ```yaml
   # Split voices across multiple TTS providers
   NARRATOR:
     provider: openai
   MAIN_CHARACTER:
     provider: elevenlabs
   SIDE_CHARACTER:
     provider: zonos
   ```

**Prevention**:
- Use multiple TTS providers
- Monitor provider-specific limits

### 3. API Key Issues

**Problem**: API authentication failures.

**Symptoms**:
- "API key not set" errors
- Authentication failed messages
- 401 Unauthorized errors

**Solutions**:

1. **Check Environment Variables**
   ```bash
   # Verify keys are set
   echo $OPENAI_API_KEY
   echo $ELEVEN_API_KEY
   echo $CARTESIA_API_KEY
   echo $MINIMAX_API_KEY
   echo $MINIMAX_GROUP_ID
   echo $ZONOS_API_KEY
   ```

2. **Set Keys Properly**
   ```bash
   # In terminal session
   export OPENAI_API_KEY="your-key-here"
   
   # Or in .env file
   OPENAI_API_KEY=your-key-here
   ELEVEN_API_KEY=your-key-here
   ```

3. **Validate Key Format**
    - OpenAI: Starts with `sk-`
    - ElevenLabs: 32-character string
    - Cartesia: Starts with `sk_car_`
    - Minimax (API key): Bearer token format, long string
    - Minimax (Group ID): String of digits
    - Zonos: Starts with `zsk-`

**Prevention**:
- Use `.env` file for persistent keys
- Check API dashboard for key validity

### 4. Voice Configuration Errors

**Problem**: Voice not found or invalid configuration.

**Symptoms**:
- Voice ID errors
- Missing provider configuration
- Invalid voice parameters
- Required fields missing

**Solutions**:

1. **OpenAI**
- Ensure a valid voice option is being used
   ```bash
   # Valid voice options
   voices: [alloy, ash, coral, echo, fable, onyx, nova, sage, shimmer]
   ```

2. **ElevenLabs**
- Check voice ID is from public voice library (https://elevenlabs.io/app/voice-library) and not the "My voices" library (https://elevenlabs.io/app/voice-lab)
- Search for voice ID in the [public voice library](https://elevenlabs.io/app/voice-library) to make sure it still exists.  Voices are some times removed from ElevenLabs
   ```bash
   # Voice ID format: 21-character string
   voice_id: ErXwobaYiN019PkySvjV  # ID must be from public library
   ```

3. **Minimax**
    ```bash
    # Validate voice_id is one of the valid voice IDs
    voice_id: Casual_Guy  # Must be one of system voices
    
    # If using voice_mix, ensure proper structure
    voice_mix:
      - voice_id: Casual_Guy  # Must be valid voice ID
        weight: 70  # Must be 1-100
      - voice_id: Deep_Voice_Man
        weight: 30
    ```

4. **Zonos**
    ```bash
    # Validate voice is one of the default_voice_name from zonos documentation
    default_voice_name: american_male  # Must be one of 9 default voices
    ```

**Prevention**:
- Use `sts-tts-provider-yaml generate` for templates
- Validate configuration with `--dry-run` run mode
- Keep backup of working configurations

### 5. Memory and Disk Space Issues

**Problem**: System running out of memory or disk space.

**Symptoms**:
- Generation stops unexpectedly
- System slowdown
- "No space left on device" errors

**Solutions**:

1. **Reduce Batch Size**
For memory constrained systems, reducing the concatenation batch size can help performance when combining audio segments
   ```bash
   uv run sts-generate-audio --concat-batch-size 150
   ```

2. **Reduce Maximum Concurrent Downloads**
Reducing the amount of concurrent downloads can help reduce memory usage
   ```bash
   uv run sts-generate-audio --max-workers 5
   ```

3. **Process in Segments**
   ```bash
   # Process chapters separately
   uv run sts-generate-audio chapter1.json --populate-cache
   uv run sts-generate-audio chapter2.json --populate-cache
   # Manually combine later
   ```

4. **Clean Unnecessary Files**
   ```bash
   # Remove temporary files
   rm -rf output/*/logs/old_logs_*.txt
   rm -rf standalone_speech/unused_*.mp3
   ```

**Prevention**:
- Monitor disk space before large projects
- Use `--populate-cache` for gradual processing
- Consider processing on systems with adequate resources

### 6. Text Processor Configuration Issues

**Problem**: Text processors not working as expected.

**Symptoms**:
- Text not being transformed
- Wrong text processor precedence
- Validation errors

**Solutions**:

1. **Check Text Processor Order**
- All preprocessors from all configs, will be run before processors
- Multiple will be processed in order
- Within a config, (pre)processors will be run top to bottom
- Pay attention to "chain" mode (pre)processors (output of one (pre)processor becomes input of next) vs. "override" mode (last instance takes precedence) 

   ```yaml
   # config 1
   preprocessors:
     - name: extract_dialogue_parentheticals
   processors:
     - name: text_substitution
     - name: capitalization_transform_processor
   ```

   ```yaml
   # config 2
   preprocessors:
     - name: speaker_merge_preprocessor
   processors:
     - name: pattern_replace_processor
   ```

   ```yaml
   # Resultant processing pipeline ordering:
   # extract_dialogue_parentheticals -> speaker_merge_preprocessor -> text_substitution ->
   #  capitalization_transform_processor -> pattern_replace_processor
   ```



2. **Validate Configuration**
   ```bash
   # Test text processor configuration
   uv run sts-apply-text-processors-json script.json \
     --text-processor-configs test_config.yaml
   ```

3. **Fix Syntax Errors**
   - Check YAML indentation
   - Verify field names match exactly
   - Ensure required fields are present (check log output)

**Prevention**:
- Start with default configuration
- Add custom processors incrementally
- Test with small examples first

### 7. Cache-Related Issues

**Problem**: Unexpected cache behavior.

**Symptoms**:
- Audio not being reused
- Cache files overwriting each other
- Missing cache files

**Solutions**:

1. **Verify Cache Naming**
   ```bash
   # Cache filename structure:
   # [original_hash]~~[processed_hash]~~[provider_id]~~[speaker_id].mp3
   ```

2. **Check File Paths**
   ```bash
   # Ensure cache directory exists
   ls -la output/[script]/cache/
   ```

3. **Clear Problematic Cache**
   ```bash
   # Remove specific cache files
   rm output/[script]/cache/problematic_*.mp3
   # Or clear all cache
   rm -rf output/[script]/cache/
   ```

**Prevention**:
- Avoid modifying text processors / parser between runs of a screenplay
- Maintain separate cache directories for different versions

### 8. ElevenLabs-Specific Issues

**Problem**: ElevenLabs voice management errors.

**Symptoms**:
- "Voice not found in registry" errors
- 30 voice limit exceeded
- Monthly add/remove quota reached

**Solutions**:

1. **Use Public Library Voices**
   ```yaml
   # Only use public library voice IDs
   SPEAKER:
     provider: elevenlabs
     voice_id: ErXwobaYiN019PkySvjV  # Public library ID
   ```

2. **Monitor Voice Usage**
   - Provider automatically manages 30 voice limit
   - Check if monthly quota is exceeded (check log file)

3. **Alternative Approach**
   ```bash
   # If ElevenLabs issues persist, switch provider temporarily
   uv run sts-generate-audio --tts-config backup_config.yaml
   ```

**Prevention**:
- Minimize voice changes during development
- Use recommended voice tags (narrative & story, conversational)
- Plan voice allocation before large projects; try to reuse same 30 voices, as going above this will result in voice swapping from the library

### 9. Parser Issues

*Note: Screenplay parsing is currently fragile. It works best with movie screenplays with "standard" formatting. Support of scanned in / OCR'd scripts is currently poor. Additional configuration, and better handling of edge-cases, is planned for a future release*

**Problem**: Screenplay parsing errors.

**Symptoms**:
- Incorrect speaker attribution
- Merged dialogues
- Missing text chunks

**Solutions**:

1. **Manual Text Extraction**
   ```bash
   # Extract to text first for manual editing
   uv run sts-parse-screenplay script.pdf --text-only
   # Edit text file to remove headers/footers
   # Then parse cleaned text
   uv run sts-parse-screenplay cleaned_script.txt
   ```

2. **Check Parser Output**
   ```bash
   # Analyze parsed structure
   uv run sts-analyze-json script.json
   ```

3. **Validate any Custom Parser Changes**
   ```bash
   # When making changes to the parser, show differences in output between
   # parser version used to originally generate script.json and current parser logic
   uv run sts-parse-regression-check-json script.json
   ```

**Prevention**:
- Clean PDF before parsing
- Verify screenplay formatting
- Review parsed output before audio generation

### 10. Network Connectivity Issues

**Problem**: Network errors during API calls.

**Symptoms**:
- Connection timeout errors
- Intermittent failures
- SSL/TLS errors

**Solutions**:

1. **Retry with Backoff**
   - System automatically retries failed requests
   - Check network stability

2. **Test Connectivity**
   ```bash
   # Test basic connectivity to each provider
   curl https://api.openai.com/v1/models
   curl https://api.elevenlabs.io/v1/voices
   ```

3. **Configure Timeouts**
   - Network issues are handled automatically
   - Consider VPN if regional restrictions apply

**Prevention**:
- Stable internet connection
- Use `--populate-cache` run mode to ensure all files downloaded before generation
- Use local cache when possible

## Debugging Tools

### Command Line Tools

1. **Standalone Speech Testing**
   ```bash
   # Test individual voice configurations
   uv run sts-generate-standalone-speech openai --voice echo "Test text"
   ```

2. **Dry Run Validation**
   ```bash
   # Validate configuration without generation
   uv run sts-generate-audio script.json --tts-config config.yaml --dry-run
   ```

3. **Processor Testing**
   ```bash
   # Test text processors independently
   uv run sts-apply-text-processors-json script.json \
     --text-processor-configs test_config.yaml \
     --output-path debug_output.json
   ```

4. **Parser Regression Testing**
   ```bash
   # When making changes to the parser, show differences in output between
   # parser version used to originally generate script.json and current parser logic
   uv run sts-parse-regression-check-json script.json
   ```

### Log Analysis

1. **Check Detailed Logs**
   ```bash
   # View recent logs
   tail -f output/[script]/logs/[run mode]_log_YYYYMMDD_HHMMSS.txt
   ```

2. **Filter Errors**
   ```bash
   # Find errors in logs
   grep -i error output/[script]/logs/[run mode]_log_*.txt
   grep -i warning output/[script]/logs/[run mode]_log_*.txt
   ```

## Getting Help

### Information to Include

When reporting issues, include:
1. Full error message
2. Command used
3. Log file from output/[script]/logs
4. Configuration files (tts config, any additional processor configs, dialogue chunk .json)
5. System information (OS, Python version)
6. UV version: `uv --version`


## Best Practices for Avoiding Issues

1. **Incremental Development**
   - Test with small scripts first
   - Build up to full-length projects
   - Use `--dry-run` frequently

2. **Configuration Management**
   - Keep backup configurations
   - Version control YAML files
   - Document custom changes

3. **Resource Management**
   - Monitor disk space
   - Use appropriate batch sizes
   - Clean up old files regularly

4. **Quality Assurance**
   - Validate dialogue .json with `sts-analyze-json`
   - Use `--populate-cache` during audio generation to ensure all files downloaded without issue
   - Use `--check-silence` during audio generation
   - Use `sts-generate-standalone-speech` to test new voices and TTS providers

5. **Error Prevention**
   - Set up API keys properly
   - Follow naming conventions
   - Use provided templates