# Custom Voice Configuration Form

## Overview

The `CustomVoiceForm` component provides a dynamic form for configuring custom voices across different TTS providers. It fetches provider-specific field requirements from the backend API and generates appropriate form controls.

## Features

- **Dynamic Field Generation**: Automatically generates form fields based on provider metadata
- **Type-Safe Validation**: Validates field types, ranges, and required constraints
- **Multiple Field Types**: Supports string, integer, float, boolean fields with appropriate controls
- **Provider-Specific Options**: Renders select dropdowns for fields with predefined options
- **Real-time Validation**: Shows validation errors as users interact with the form

## Components

### CustomVoiceForm

Main form component that renders dynamic fields based on provider metadata.

**Props:**

- `provider: string` - The TTS provider identifier (e.g., 'openai', 'elevenlabs')
- `currentConfig?: Record<string, unknown>` - Existing configuration to populate the form
- `onConfigChange: (config: Record<string, unknown>) => void` - Callback when configuration is valid
- `onCancel: () => void` - Callback when user cancels the form

### useProviderMetadata Hook

React Query hook that fetches provider metadata including required and optional fields.

**Usage:**

```typescript
const { data: providerInfo, isLoading, error } = useProviderMetadata('openai');
```

## Field Types and Controls

The form automatically renders appropriate controls based on field types:

- **STRING**: Text input or select dropdown (if options are provided)
- **INTEGER**: Number input with step=1
- **FLOAT**: Number input with step=any
- **BOOLEAN**: Toggle switch
- **LIST**: (Future enhancement)
- **DICT**: (Future enhancement)

## Integration Example

```typescript
import { CustomVoiceForm } from '@/components/voice-casting/CustomVoiceForm';

function VoiceAssignmentPanel() {
  const [isCustomVoice, setIsCustomVoice] = useState(false);
  const [customVoiceConfig, setCustomVoiceConfig] = useState<Record<string, unknown>>({});
  const [selectedProvider, setSelectedProvider] = useState('openai');

  const handleCustomVoiceConfig = (config: Record<string, unknown>) => {
    setCustomVoiceConfig(config);

    // Generate voice identifier
    const primaryField = config.voice_id || config.voice || 'custom';
    const voiceIdentifier = `${selectedProvider}:custom:${primaryField}`;

    // Save assignment
    setCharacterAssignment(characterName, {
      voice_identifier: voiceIdentifier,
      provider: selectedProvider,
      provider_config: config,
    });
  };

  return (
    <>
      {isCustomVoice && (
        <CustomVoiceForm
          provider={selectedProvider}
          currentConfig={customVoiceConfig}
          onConfigChange={handleCustomVoiceConfig}
          onCancel={() => setIsCustomVoice(false)}
        />
      )}
    </>
  );
}
```

## Provider Field Examples

### OpenAI

- `voice` (required, select): Voice selection from predefined options

### ElevenLabs

- `voice_id` (required, string): ElevenLabs voice identifier
- `stability` (optional, float): Voice stability (0.0-1.0)
- `similarity_boost` (optional, float): Similarity boost (0.0-1.0)

### Cartesia

- `voice_id` (required, string): Cartesia voice identifier
- `language` (optional, string): Language code
- `speed` (optional, float): Speech speed multiplier (0.5-2.0)

## Future Enhancements

1. **Optional Fields Toggle**: Add a toggle to show/hide optional fields
2. **Field Grouping**: Group related fields together for better UX
3. **Advanced Validation**: Add regex patterns, custom validators
4. **Field Dependencies**: Show/hide fields based on other field values
5. **Voice Preview**: Integration with TTS preview for custom voices
6. **Template System**: Save and reuse custom voice configurations

## Testing

The component includes comprehensive tests covering:

- Dynamic field rendering based on provider metadata
- Form validation and error handling
- Value initialization and updates
- Submit and cancel callbacks

Run tests:

```bash
npm test CustomVoiceForm
```
