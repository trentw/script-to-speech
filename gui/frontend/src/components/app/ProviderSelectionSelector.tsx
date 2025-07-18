import React from 'react';
import { Settings } from 'lucide-react';
import { SelectorButton } from '@/components/ui/selector';
import type { ProviderInfo, VoiceEntry } from '../../types';

interface ProviderSelectionSelectorProps {
  providers: ProviderInfo[];
  selectedProvider?: string;
  voiceLibrary: Record<string, VoiceEntry[]>;
  voiceCounts: Record<string, number>;
  providerErrors: Record<string, boolean>;
  onProviderSelect: (provider: string) => void;
  onOpenProviderPanel: () => void;
}

export const ProviderSelectionSelector: React.FC<ProviderSelectionSelectorProps> = ({
  providers,
  selectedProvider,
  voiceLibrary,
  voiceCounts,
  providerErrors,
  onProviderSelect: _onProviderSelect, // Not used directly in this component
  onOpenProviderPanel
}) => {
  const getProviderDisplayName = (provider: ProviderInfo) => {
    return provider.name;
  };

  const getProviderSubtext = (provider: ProviderInfo) => {
    // Check if provider has an error
    if (providerErrors[provider.identifier]) {
      return 'Error loading voices';
    }
    
    // Use voice library if available (when provider is selected), otherwise use voice counts
    const voiceCount = voiceLibrary[provider.identifier]?.length || voiceCounts[provider.identifier] || 0;
    if (voiceCount === 0) {
      return 'No voices available';
    }
    return `${voiceCount} voice${voiceCount !== 1 ? 's' : ''} available`;
  };

  const getProviderAvatar = (provider: ProviderInfo) => {
    return provider.name.charAt(0).toUpperCase();
  };


  const selectedProviderInfo = providers.find(p => p.identifier === selectedProvider);

  if (!providers || providers.length === 0) {
    return (
      <div className="space-y-3">
        <div className="text-center py-8 text-muted-foreground">
          <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-muted/30 flex items-center justify-center">
            <Settings className="w-6 h-6 opacity-50" />
          </div>
          <p className="text-sm font-medium">No providers available</p>
          <p className="text-xs mt-1 opacity-75">
            Check your API configuration
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <SelectorButton
        selectedItem={selectedProviderInfo}
        placeholder="Select provider"
        onClick={onOpenProviderPanel}
        renderAvatar={getProviderAvatar}
        renderPrimary={getProviderDisplayName}
        renderSecondary={getProviderSubtext}
        availableCount={providers.length}
      />

    </div>
  );
};