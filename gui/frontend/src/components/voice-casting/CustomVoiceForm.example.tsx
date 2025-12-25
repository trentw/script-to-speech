/**
 * Example usage of CustomVoiceForm component
 *
 * This example shows how to integrate the CustomVoiceForm component
 * into the VoiceAssignmentPanel for custom voice configuration.
 */

import { useState } from 'react';

import { CustomVoiceForm } from './CustomVoiceForm';

export function CustomVoiceFormExample() {
  const [selectedProvider] = useState('openai');
  const [customConfig, setCustomConfig] = useState<Record<string, unknown>>({});
  const [showForm, setShowForm] = useState(false);

  const handleConfigChange = (config: Record<string, unknown>) => {
    setCustomConfig(config);
    setShowForm(false);

    // Generate voice identifier for custom voice
    const primaryField = config.voice_id || config.voice || 'custom';
    const voiceIdentifier = `${selectedProvider}:custom:${primaryField}`;

    console.log('Custom voice configured:', {
      voiceIdentifier,
      provider: selectedProvider,
      provider_config: config,
    });
  };

  return (
    <div className="space-y-4">
      {!showForm ? (
        <div>
          <button onClick={() => setShowForm(true)}>
            Configure Custom Voice
          </button>

          {Object.keys(customConfig).length > 0 && (
            <div className="mt-4 rounded border p-4">
              <h4>Current Configuration:</h4>
              <pre>{JSON.stringify(customConfig, null, 2)}</pre>
            </div>
          )}
        </div>
      ) : (
        <CustomVoiceForm
          provider={selectedProvider}
          currentConfig={customConfig}
          onConfigChange={handleConfigChange}
          onCancel={() => setShowForm(false)}
        />
      )}
    </div>
  );
}

/**
 * Integration example for VoiceAssignmentPanel
 *
 * Replace the existing custom voice configuration section with:
 *
 * ```tsx
 * {isCustomVoice && (
 *   <Card className="border-primary/20">
 *     <CardContent className="p-0">
 *       <CustomVoiceForm
 *         provider={selectedProvider}
 *         currentConfig={customVoiceConfig}
 *         onConfigChange={(config) => {
 *           setCustomVoiceConfig(config);
 *           // Optionally auto-assign after configuration
 *           // handleAssign();
 *         }}
 *         onCancel={() => {
 *           setIsCustomVoice(false);
 *           setCustomVoiceConfig({});
 *         }}
 *       />
 *     </CardContent>
 *   </Card>
 * )}
 * ```
 */
