import React from 'react';
import {
  ProviderSelector,
  VoiceSelector,
  ConfigForm,
  TextInput,
} from '.';
import { useConfiguration, useUserInput } from '../stores/appStore';
import type { ProviderInfo, VoiceEntry } from '../types';

interface ConfigurationPanelProps {
  providers: ProviderInfo[];
  voiceLibrary: Record<string, VoiceEntry[]>;
  loading: boolean;
  onProviderChange: (provider: string) => void;
  onVoiceSelect: (voice: VoiceEntry) => void;
  onConfigChange: (config: Record<string, any>) => void;
  onGenerate: () => void;
}

export const ConfigurationPanel: React.FC<ConfigurationPanelProps> = ({
  providers,
  voiceLibrary,
  loading,
  onProviderChange,
  onVoiceSelect,
  onConfigChange,
  onGenerate,
}) => {
  // Use store for client state
  const { selectedProvider, selectedVoice, currentConfig } = useConfiguration();
  const { text, setText } = useUserInput();
  return (
    <div className="lg:col-span-2 space-y-6">
      {/* Text Input */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Text to Speech
        </h2>
        <TextInput
          value={text}
          onChange={setText}
          placeholder="Enter the text you want to convert to speech..."
        />
      </div>

      {/* Provider Selection */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">TTS Provider</h2>
        <ProviderSelector
          providers={providers}
          selectedProvider={selectedProvider}
          onProviderChange={onProviderChange}
          loading={loading}
        />
      </div>

      {/* Voice Selection */}
      {selectedProvider && (
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Voice Selection
          </h2>
          <VoiceSelector
            provider={selectedProvider}
            voices={voiceLibrary[selectedProvider] || []}
            selectedVoice={selectedVoice}
            onVoiceSelect={onVoiceSelect}
          />
        </div>
      )}

      {/* Configuration Form */}
      {selectedProvider && (
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Configuration
          </h2>
          <ConfigForm
            provider={selectedProvider}
            providerInfo={providers.find((p) => p.identifier === selectedProvider)}
            config={currentConfig}
            onConfigChange={onConfigChange}
          />
        </div>
      )}

      {/* Generate Button */}
      <div className="flex justify-center">
        <button
          className="btn-primary px-8 py-3 text-lg"
          onClick={onGenerate}
          disabled={!selectedProvider || !text.trim() || loading}
        >
          {loading ? (
            <div className="flex items-center space-x-2">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
              <span>Generating...</span>
            </div>
          ) : (
            'Generate Speech'
          )}
        </button>
      </div>
    </div>
  );
};