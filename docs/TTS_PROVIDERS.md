# TTS Provider Guide

Script to Speech supports multiple Text-to-Speech providers. This guide covers configuration, capabilities, and provider-specific considerations.

## Supported TTS Providers

### [OpenAI](https://openai.com/api/)
- **Requirements**: API key required
- **Voice Options**: Preview available at [openai.fm](https://www.openai.fm/)
- **Concurrent Downloads**: 7 threads
- **Rate Limits**: Standard API rate limits apply
- **Best For**: 
- **Considerations**
  - **Pros**
    - Cheap (up to 10x cheaper compared to ElevenLabs)
    - High-quality, realistic-sounding voices
    - Fast generation
  - **Cons**
    - Limited number of voices
    - Has issues where short clips are sometimes output as silent
  - **Best For**
    - Characters with lots of lines (due to affordability)
    - Characters that don't have special accent / age / etc. considerations
    - "default" narrator character (given above considerations)
### [ElevenLabs](https://elevenlabs.io/app/home)
- **Requirements**: 
  - API key required
  - "Creator" plan or higher required (other plans to be supported in future releases)
- **Voice Library**: Uses "public" [library voices](https://elevenlabs.io/app/voice-library) for configuration
- **Voice Limit**: 30 voice limit in ["my voices" library](https://elevenlabs.io/app/voice-lab)
- **Voice Management**: Automatic voice addition/removal within 30 voice limit
- **Monthly Limits**: Voice adds/removes have monthly quotas imposed by ElevenLabs
- **Concurrent Downloads**: 5 threads
- **Considerations**
  - **Pros**
    - Reliable generation: no issues with silent or otherwise mis-generated audio
    - Wide variety of voices, across ages / accents / ethnicities / style
    - High-quality, realistic-sounding voices
    - Fast generation
  - **Cons**
    - Expensive
    - Some voices in public library low quality
  - **Best For**
    - Characters where accent / age / style is important
    - Filling out the wider world of side characters

### [Cartesia](https://play.cartesia.ai/)
- **Concurrent Downloads**: 2 threads
- **Customization**: Language options and speaking rate (experimental)
- **Considerations**
  - **Pros**
    - Free plan gives 25 minutes of generations a month
    - Voice audio quality fairly high
    - Fast generation
    - Features a few dozen voices
    - $5 / month plan gets 125 minutes of audio
  - **Cons**
    - Voice cadence / delivery at times inconsistent
    - Voice less life-like than OpenAI or ElevenLabs providers
    - Inconsistent delivery of ALL UPPERCASE text
  - **Best For**
    - Side characters
    - Testing


### [Zyphra Zonos](https://playground.zyphra.com/sign-in) (API version)
- **Requirements**: API key required; free plan okay
- **Voice Options**: Configurable voice from 9 options
- **Concurrent Downloads**: 5 threads
- **Customization**: Speaking rate and language options
- **Considerations**
  - **Pros**
    - Free plan gives 100 minutes of generations a month
  - **Cons**
    - Few voices offered
    - Generation comparatively slow
    - Reliability: coherence struggles with longer dialogues
    - Voice less life-like than other providers
  - **Best For**
    - One-off side characters
    - Testing

### Dummy (Testing Only)
- **Purpose**: Testing without API calls
- **Types**: dummy_stateful and dummy_stateless
- **Use Case**: Development and testing


## Environment Variables

Required environment variables by provider:

```bash
# OpenAI
export OPENAI_API_KEY="your-api-key"

# ElevenLabs
export ELEVEN_API_KEY="your-api-key"

# Zonos
export ZONOS_API_KEY="your-api-key"
```

## Configuration Structure

### Provider Assignment

Each speaker in your configuration must have a provider assigned, and must supply all required fields for that provider. By default, when a TTS provider configuration is generated, required fields will be generated; optional fields can be manually added. Multiple providers can be combined in a single TTS provider configuration.

```yaml
default:
  provider: openai
  voice: onyx

HARRY:
  provider: elevenlabs
  voice_id: ErXwobaYiN019PkySvjV

LUNA:
  provider: zonos
  default_voice_name: american_male
```

### Generated Configuration (Single Provider Workflow)

The `sts-tts-provider-yaml generate [screenplay].json --tts-provider [provider]` command creates a template with:
1. An entry for each speaker
2. Pre-populated `provider` field
2. Empty entries for each required provider field
3. Speaker statistics to aid in casting each character
4. (optional) Use `--include-optional-fields` flag to also create empty entries for each optional field

```yaml
# default: 1556 lines - Used for all non-dialogue pieces
# Total characters: 104244, Longest dialogue: 2082 characters
default:
  provider: openai
  voice:

# HARRY: 283 lines
# Total characters: 12181, Longest dialogue: 365 characters
HARRY:
  provider: openai
  voice:
```

## Multi-Provider Workflow

### Step 1: Generate Base Configuration
```bash
uv run sts-tts-provider-yaml generate input/[screenplay]/[screenplay].json
```

### Step 2: Assign TTS Providers
Edit the generated YAML to assign providers to each speaker:
```yaml
default:
  provider: openai
HARRY:
  provider: elevenlabs
LUNA:
  provider: openai
```

### Step 3: Populate Provider Fields
```bash
uv run sts-tts-provider-yaml populate input/[screenplay]/[screenplay].json \
  input/[screenplay]/[screenplay]_voice_config.yaml
```

This creates `[screenplay]_voice_config_populated.yaml` with provider-specific fields grouped:

```yaml
# OpenAI Configuration
default:
  provider: openai
  voice:

LUNA:
  provider: openai
  voice:

# ElevenLabs Configuration
HARRY:
  provider: elevenlabs
  voice_id:
```

### Step 4: Fill in Provider Details
Complete the populated configuration with specific values:
```yaml
# OpenAI Configuration
default:
  provider: openai
  voice: onyx

LUNA:
  provider: openai
  voice: alloy

# ElevenLabs Configuration
HARRY:
  provider: elevenlabs
  voice_id: ErXwobaYiN019PkySvjV
```

## Provider-Specific Configuration

### OpenAI Configuration

Required fields:
- `voice`: Voice identifier

Available voices:
- alloy
- ash
- coral
- echo
- fable
- onyx
- nova
- sage
- shimmer

Example:
```yaml
default:
  provider: openai
  voice: onyx

NARRATOR:
  provider: openai
  voice: alloy
```

### ElevenLabs Configuration

Required fields:
- `voice_id`: Public library voice ID

Important notes:
- Voice IDs must be from the [public voice library](https://elevenlabs.io/app/voice-library), not the [my voices library](https://elevenlabs.io/app/voice-lab)
- Provider manages the 30 voice limit automatically by removing voices from "my voices" library when limit is reached
- Monthly add/remove operations are limited

Example:
```yaml
MARY:
  provider: elevenlabs
  voice_id: IKne3meq5aSn9XLyUdCD  # Public library ID

JOHN:
  provider: elevenlabs
  voice_id: ErXwobaYiN019PkySvjV  # Public library ID
```

### Cartesia Configuration

Required fields:
- `voice_id`: one of 9 available voices
Voices and theird IDs can be found at the [Cartesia Playground](https://play.cartesia.ai/)

Optional fields
- `language`: One of [en,fr,de,es,pt,zh,ja,hi,it,ko,nl,pl,ru,sv,tr]
- `speed`: One of ["slow", "normal", "fast"] 
  - *note: this is an experimental feature that doesn't work for all voices*

Example:
```yaml
BECCA:
  provider: cartesia
  voice_id: bf0a246a-8642-498a-9950-80c35e9276b5
  speed: fast
  language: fr

TOM:
  provider: cartesia
  voice_id: 4df027cb-2920-4a1f-8c34-f21529d5c3fe
```


### Zonos Configuration

Required fields:
- `default_voice_name`: one of 9 available voices

Available voices:
- american_female
- american_male	
- anime_girl
- british_female
- british_male
- energetic_boy
- energetic_girl
- japanese_female
- japanese_male

Optional fields:
- `speaking_rate`: Float between 5 and 35
- `language_iso_code`: One of [en-us, fr-fr, de, ja, ko, cmn]

Example:
```yaml
ROBOT:
  provider: zonos
  default_voice_name: american_female
  speaking_rate: 20
  language_iso_code: en-us

ALIEN:
  provider: zonos
  default_voice_name: american_male
```

## Rate Limiting

### Automatic Handling
The system automatically handles rate limits with:
- Exponential backoff
- Provider-specific retry logic
- Queue management

When rate limited, the system will:
1. Pause requests for that provider
2. Continue with other TTS providers
3. Retry after backoff period

## Provider Architecture

The Script to Speech system supports two types of TTS providers: stateless and stateful. Understanding the difference is important for creating custom providers.

### Stateless vs. Stateful TTS Providers

#### Stateless TTS Providers
- **Definition**: Providers that don't maintain state between API calls
- **Implementation**: Use class methods to generate audio
- **Examples**: OpenAI, Zonos
- **Advantages**:
  - Simpler to implement
  - Thread-safe without additional code
  - More predictable behavior
  - Easier to debug
- **When to use**: Default choice for most providers

#### Stateful TTS Providers
- **Definition**: Providers that maintain state between API calls
- **Implementation**: Same class methods as Stateless provider, except for instance-based `__init__` and `generate_audio` methods
- **Examples**: ElevenLabs (for voice registry management)
- **Advantages**:
  - Can cache / configure information between calls
  - Can implement complex state machines
- **When to use**: Only when required by the API or when managing complex resources

### Provider Management

The `TTSProviderManager` handles:
- **Lazy Initialization**: TTS providers are only initialized when needed
- **Thread Safety**: Thread locks protect provider initialization and state
- **Client Caching**: API clients are reused across calls
- **Multi-threading**: Each provider has its own download concurrency settings

## Creating Custom TTS Providers

### Base Classes

All TTS providers implement one of two base classes:

1. `StatelessTTSProviderBase`
   - For TTS providers without state
   - Uses class methods

2. `StatefulTTSProviderBase`
   - For TTS providers with state
   - Uses instance methods and `__init__`

Both inherit from `TTSProviderCommonMixin` which defines common requirements.

### Adding a New Provider
1. Create a directory in `src/script_to_speech/tts_providers/` with your provider name
2. Create a `tts_provider.py` file in that directory
3. Implement the appropriate base class
4. Return the correct provider identifier via `get_provider_identifier()`

The provider will be automatically discovered and available in configurations.

### Examples
- For an example of a stateless provider, see the [OpenAI TTS Provider](../src/script_to_speech/tts_providers/openai/tts_provider.py)
- For an example of a stateful provider, see the [ElevenLabs TTS Provider](../src/script_to_speech/tts_providers/elevenlabs/tts_provider.py) and accompanying [ElevenLabs Voice Registry Manager](src/script_to_speech/tts_providers/elevenlabs/voice_registry_manager.py)

### Provider Requirements

Required methods:
- `get_provider_identifier()`: Unique identifier for this provider; will be used in YAML configuration and whenever this provider is being called on the command line
- `get_speaker_identifier()`: Unique identifier for a given speaker, given a speaker configuration. This is used in caching, so **changing any configuration option for a speaker (e.g. optional fields) should also change the returned `speaker_identifier`**
- `instantiate_client()`: Create the API client that will be passed to `generate_audio` method by the `TTSProviderManager`
- `generate_audio()`: Request the audio from the TTS Provider API; return bytes representing the audio
- `get_required_fields()`: Required configuration fields
- `validate_speaker_config()`: Logic to validate configuration (checking for required fields, that they're the right type, etc.)
- `get_yaml_instructions()`: Configuration help text outlining required / optional fields, best practices, etc.

Optional methods:
- `get_optional_fields()`: Optional configuration fields
- `get_max_download_threads()`: Concurrent thread limit; defaults to 1

## Best Practices

### Configuration Management
1. Use the generate → assign → populate workflow
2. Keep backup configurations for different voice setups
3. Consider character type when assigning TTS providers

### Multi-Provider Benefits
1. **Speed**: Parallel processing across TTS providers
2. **Cost**: Optimize per-provider pricing
3. **Quality**: Match voice types to character needs

## Troubleshooting

### Common Issues

1. **API Key Errors**
   ```bash
   # Check environment variables
   echo $OPENAI_API_KEY
   echo $ELEVEN_API_KEY
   echo $ZONOS_API_KEY
   ```

2. **Voice Not Found**
   - ElevenLabs: Ensure voice ID is from public library
   - OpenAI: Verify voice name matches available options
   - Zonos: Check default_voice_name is a valid voice

3. **Rate Limiting**
   - Check provider-specific rate limits
   - Limit global concurrent downloads with `--max-workers` run mode modifier
   - Distribute voices across TTS providers
   - Monitor monthly quotas for voice adds / removes (ElevenLabs)

4. **Quality Issues**
   - OpenAI: Try different voices for different character types
   - ElevenLabs: Use "narrative"/"conversational" tagged voices
   - Zonos: Adjust speaking rate parameter

### Debugging
```bash
# Test single line of dialogue
uv run sts-generate-standalone-speech openai --voice echo "Test text"

```