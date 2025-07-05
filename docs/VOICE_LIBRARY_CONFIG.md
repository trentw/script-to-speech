# Voice Library Configuration Guide

Voice Library Configuration allows you to customize voice selection and casting prompts for your screenplay projects. This system provides fine-grained control over which voices are available for each TTS provider and enables you to add custom instructions for voice casting.

**File Discovery**: All `.yaml` and `.yml` files in configuration directories (including subdirectories) are automatically discovered and merged. File names are purely organizational - you can use any naming convention that works for your project.

## Purpose

The voice library configuration system serves several key purposes:

- **Voice Filtering**: Control which voices from each provider are included in voice casting prompts
- **Custom Instructions**: Add provider-specific or overall guidance for voice casting
- **Project Customization**: Override system-wide voice library settings on a per-project basis
- **Prompt Enhancement**: Inject additional context into overall voice casting prompts

## Configuration Options

### included_sts_ids

Whitelist specific voices for providers. When specified, only the listed voices will be available for that provider in voice casting prompts.

```yaml
included_sts_ids:
  openai:
    - alloy
    - nova
    - shimmer
  elevenlabs:
    - carl
    - shiv
    - kary
```

**Use Cases**:
- Limit voice selection to a curated set
- Focus on specific voice characteristics for your project

### excluded_sts_ids

Blacklist specific voices from providers. These voices will be removed from voice casting prompts.

```yaml
excluded_sts_ids:
  openai:
    - echo  # Too robotic for this project
  elevenlabs:
    - sully
    - daniel
```

**Use Cases**:
- Remove voices that don't fit your project's tone
- Exclude low-quality or problematic voices
- Filter out voices with inappropriate accents or characteristics

### additional_voice_casting_instructions

Add custom instructions that appear in voice casting prompts. Supports both provider-specific instructions and overall guidance.

#### Provider-Specific Instructions

```yaml
additional_voice_casting_instructions:
  openai:
    - "Use dramatic voices for action scenes"
    - "Prefer younger sounding voices for teenage characters"
  elevenlabs:
    - "Use British accents when available"
    - "Focus on emotional range for main characters"
  cartesia:
    - "Experiment with speaking rate for comedic characters"
```

#### Overall Instructions

```yaml
additional_voice_casting_instructions:
  overall_voice_casting_prompt:
    - "Focus on character emotional state throughout the story"
    - "Maintain consistency across scenes"
    - "Consider the target audience when selecting voices"
```

**Use Cases**:
- Provide project-specific casting guidance
- Emphasize particular voice characteristics
- Add context about character development or story tone

## Configuration Validation

The system validates configurations to prevent conflicts and ensure proper setup.

### Conflict Detection

The system automatically detects when the same voice ID appears in both `included_sts_ids` and `excluded_sts_ids` for a provider:

```yaml
# ❌ This will cause a validation error
included_sts_ids:
  openai:
    - alloy
    - nova
excluded_sts_ids:
  openai:
    - nova  # Conflict: nova is both included and excluded
```

**Error Message**:
```
Validation FAILED. Found conflicting IDs in include and exclude lists:
Provider 'openai': Conflicting ID(s) nova
```

### Validation Commands

Use the CLI to validate your voice library configuration:

```bash
# Validate all voice library data and configurations
uv run sts-validate-voice-library-data
```

This command checks:
- Voice library YAML file syntax
- Configuration conflicts (include/exclude overlaps)
- Voice ID validity against provider schemas

## Configuration File Merging

The voice library configuration system supports a two-tier structure with automatic merging of all configuration files:

### Directory Structure

```
# System-wide configurations example (part of the codebase)
src/script_to_speech/voice_library/voice_library_config/
├── system_defaults.yaml
├── provider_exclusions.yaml
└── openai/
    ├── filtering.yaml
    └── instructions.yaml

# User/project-specific configurations example
voice_library/voice_library_config/
├── project_voice_filtering.yaml
├── custom_instructions.yaml
├── character_specific.yaml
└── providers/
    ├── openai/
    │   ├── project_filtering.yaml
    │   └── character_instructions.yaml
    └── elevenlabs/
        └── accent_preferences.yaml
```

**Subdirectory Support**: You can organize configurations into subdirectories by provider, feature, or any structure that makes sense for your project. All `.yaml` and `.yml` files in all subdirectories are automatically discovered and merged.

### Merge Process

1. **Discovery**: All `.yaml` and `.yml` files are recursively found in both directories and all subdirectories
2. **System First**: Repository configs are loaded first (regardless of subdirectory structure)
3. **User Override**: User configs are merged on top, with user values taking precedence
4. **List Merging**: Lists are combined and deduplicated (preserves order, removes duplicates)

**Organization Freedom**: Since all files are merged regardless of location, you can organize by provider (`openai/`, `elevenlabs/`), by feature (`filtering/`, `instructions/`), or any structure that works for your project.

### Example Merge

**System Config** (`src/.../voice_library_config/defaults.yaml`):
```yaml
excluded_sts_ids:
  openai:
    - echo
  elevenlabs:
    - low_quality_voice
additional_voice_casting_instructions:
  overall_voice_casting_prompt:
    - "Prioritize voice quality"
```

**User Config** (`voice_library/voice_library_config/project.yaml`):
```yaml
excluded_sts_ids:
  openai:
    - nova  # Added to system exclusions
  cartesia:
    - robotic_voice  # New provider
additional_voice_casting_instructions:
  overall_voice_casting_prompt:
    - "Focus on character age appropriateness"  # Added to system instructions
  openai:
    - "Use dramatic voices for action scenes"  # New provider-specific instruction
```

**Merged Result**:
```yaml
excluded_sts_ids:
  openai:
    - echo
    - nova  # Merged from user config
  elevenlabs:
    - low_quality_voice
  cartesia:
    - robotic_voice  # From user config
additional_voice_casting_instructions:
  overall_voice_casting_prompt:
    - "Prioritize voice quality"
    - "Focus on character age appropriateness"  # Merged list
  openai:
    - "Use dramatic voices for action scenes"
```

## Configuration Examples

### Basic Voice Filtering

**Scenario**: Limit OpenAI to specific voices, exclude problematic ElevenLabs voices

```yaml
# voice_library/voice_library_config/basic_filtering.yaml
included_sts_ids:
  openai:
    - alloy
    - nova
    - shimmer

excluded_sts_ids:
  elevenlabs:
    - poor_quality_voice
    - inappropriate_accent
```

### Project-Specific Instructions

**Scenario**: Fantasy audiobook with specific voice requirements

```yaml
# voice_library/voice_library_config/fantasy_project.yaml
additional_voice_casting_instructions:
  overall_voice_casting_prompt:
    - "This is a fantasy audiobook - consider magical and medieval themes"
    - "Main characters should have distinct, memorable voices"
    - "Background characters can share similar voice types"
  
  openai:
    - "Use deeper voices for warrior characters"
    - "Prefer lighter voices for magical characters"
  
  elevenlabs:
    - "Use British or Celtic accents when appropriate"
    - "Experiment with voice age for different character types"
```

### Multi-File Organization

**Scenario**: Separate concerns across multiple configuration files

**Base Filtering** (`voice_library/voice_library_config/voice_filtering.yaml`):
```yaml
excluded_sts_ids:
  openai:
    - echo  # Too robotic
  elevenlabs:
    - voice_with_background_noise
    - heavily_accented_unclear
```

**Casting Instructions** (`voice_library/voice_library_config/casting_guidance.yaml`):
```yaml
additional_voice_casting_instructions:
  overall_voice_casting_prompt:
    - "Prioritize emotional range and clarity"
    - "Consider character relationships when casting"
  
  openai:
    - "Best for narrator and main characters due to cost efficiency"
  
  elevenlabs:
    - "Reserve for characters requiring specific accents or ages"
```

### Provider-Organized Structure

**Scenario**: Organize by TTS provider using subdirectories

**OpenAI Configuration** (`voice_library/voice_library_config/openai/filtering.yaml`):
```yaml
included_sts_ids:
  openai:
    - alloy
    - nova
    - shimmer
```

**OpenAI Instructions** (`voice_library/voice_library_config/openai/instructions.yaml`):
```yaml
additional_voice_casting_instructions:
  openai:
    - "Use for cost-effective main characters"
    - "Avoid for characters requiring specific accents"
```

**ElevenLabs Configuration** (`voice_library/voice_library_config/elevenlabs/setup.yaml`):
```yaml
excluded_sts_ids:
  elevenlabs:
    - low_quality_voice
    - background_noise_voice

additional_voice_casting_instructions:
  elevenlabs:
    - "Use for characters requiring specific accents or ages"
    - "Prioritize emotional range over cost"
```

### Character-Specific Configuration

**Scenario**: Detailed character requirements

```yaml
# voice_library/voice_library_config/character_requirements.yaml
additional_voice_casting_instructions:
  overall_voice_casting_prompt:
    - "Main protagonist: Young adult, determined, slightly raspy voice"
    - "Antagonist: Older, smooth, slightly menacing tone"
    - "Sidekick: Energetic, higher pitch, friendly"
    - "Narrator: Neutral, clear, engaging storytelling voice"
  
  elevenlabs:
    - "Use accent variety to distinguish between regions/cultures"
    - "Age-appropriate voices are critical for believability"
```

## Integration with Voice Casting

### Generating Casting Prompts

Use the CLI to generate voice casting prompts that incorporate your configurations:

```bash
# Generate casting prompt for specific providers
uv run sts-generate-voice-library-casting-prompt \
  path/to/voice_config.yaml \
  openai elevenlabs

# Output: voice_config_voice_library_casting_prompt.txt
```

### Generated Output Structure

The generated prompt file includes:

1. **Base Prompt**: Standard voice casting instructions
2. **Overall Instructions**: From `overall_voice_casting_prompt` (if configured)
3. **Voice Library Schema**: Technical specification
4. **Voice Configuration**: Your project's voice configuration
5. **Provider Data Sections**: For each requested provider:
   - Voice library data (filtered by your include/exclude rules)
   - Provider-specific instructions (if configured)

### Example Output Structure

```
[Base voice casting prompt content]

Additionally, please abide by the following instructions when casting voices:

- Focus on character emotional state throughout the story
- Maintain consistency across scenes

--- VOICE LIBRARY SCHEMA ---

[Schema content]

--- VOICE CONFIGURATION ---

[Your voice configuration]

--- VOICE LIBRARY DATA (OPENAI) ---

When casting for this provider (openai), please abide by the following instructions. These instructions are only for this provider:

- Use dramatic voices for action scenes
- Prefer younger sounding voices for teenage characters

[Filtered OpenAI voice data]

--- VOICE LIBRARY DATA (ELEVENLABS) ---

When casting for this provider (elevenlabs), please abide by the following instructions. These instructions are only for this provider:

- Use British accents when available
- Focus on emotional range for main characters

[Filtered ElevenLabs voice data]
```

## File Structure and Best Practices

### Recommended Organization Options

**Option 1: Flat Structure with Prefixes**
```
voice_library/voice_library_config/
├── base_filtering.yaml        # Basic include/exclude rules
├── project_instructions.yaml  # Overall casting guidance
├── provider_specific.yaml     # Provider-specific instructions
└── character_notes.yaml       # Detailed character requirements
```

**Option 2: Provider-Based Subdirectories**
```
voice_library/voice_library_config/
├── overall_instructions.yaml     # Project-wide guidance
├── openai/
│   ├── filtering.yaml           # OpenAI voice filtering
│   └── instructions.yaml        # OpenAI-specific guidance
├── elevenlabs/
│   ├── filtering.yaml           # ElevenLabs voice filtering
│   └── instructions.yaml        # ElevenLabs-specific guidance
└── cartesia/
    └── setup.yaml               # All Cartesia configuration
```

**Option 3: Feature-Based Subdirectories**
```
voice_library/voice_library_config/
├── filtering/
│   ├── openai_voices.yaml       # OpenAI include/exclude
│   └── elevenlabs_voices.yaml   # ElevenLabs include/exclude
├── instructions/
│   ├── overall.yaml             # Project-wide instructions
│   ├── openai.yaml              # OpenAI-specific instructions
│   └── elevenlabs.yaml          # ElevenLabs-specific instructions
└── characters/
    └── main_characters.yaml     # Character-specific guidance
```

### Best Practices

1. **Choose Consistent Organization**: Pick one organizational structure and stick with it
2. **Use Descriptive Filenames**: Make file purposes clear from their names  
3. **Document Decisions**: Use YAML comments to explain choices
4. **Test Configurations**: Use validation commands before generating prompts
5. **Consider Subdirectories**: Use subdirectories to organize complex configurations by provider or feature

### Suggested Naming Conventions

- `*_filtering.yaml`: Voice include/exclude configurations
- `*_instructions.yaml`: Casting guidance and instructions
- `*_character.yaml`: Character-specific requirements
- `*_project.yaml`: Project-wide settings

## Troubleshooting

### Common Validation Errors

**Conflicting Voice IDs**:
```yaml
# Problem: Same voice in include and exclude
included_sts_ids:
  openai: [alloy, nova]
excluded_sts_ids:
  openai: [nova]  # ❌ Conflict

# Solution: Remove from one list
excluded_sts_ids:
  openai: [echo]  # ✅ Different voice
```

**Invalid YAML Syntax**:
```yaml
# Problem: Incorrect indentation
additional_voice_casting_instructions:
openai:  # ❌ Missing indentation
  - "instruction"

# Solution: Proper indentation
additional_voice_casting_instructions:
  openai:  # ✅ Properly indented
    - "instruction"
```

### Debugging Tips

1. **Check File Discovery**: Ensure files are in correct directories
2. **Validate YAML**: Use online YAML validators for syntax checking
3. **Test Incrementally**: Add configurations gradually to isolate issues
4. **Check Merge Results**: Generate prompts to see final merged configuration
5. **Use Validation Command**: Run `sts-validate-voice-library-data` regularly

### Getting Help

- Run validation commands for immediate feedback
- Check generated prompt files to see applied configurations
- Review error messages for specific conflict details
- Consult voice library schema files for valid voice IDs