import { Settings } from 'lucide-react';
import React from 'react';

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

export const ProviderSelectionSelector: React.FC<
  ProviderSelectionSelectorProps
> = ({
  providers,
  selectedProvider,
  voiceLibrary,
  voiceCounts,
  providerErrors,
  onProviderSelect,
  onOpenProviderPanel,
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
    const voiceCount =
      voiceLibrary[provider.identifier]?.length ||
      voiceCounts[provider.identifier] ||
      0;
    if (voiceCount === 0) {
      return 'No preconfigured voices available';
    }
    return `${voiceCount} preconfigured voice${voiceCount !== 1 ? 's' : ''} available`;
  };

  const getProviderAvatar = (provider: ProviderInfo) => {
    return provider.name.charAt(0).toUpperCase();
  };

  const selectedProviderInfo = providers.find(
    (p) => p.identifier === selectedProvider
  );

  if (!providers || providers.length === 0) {
    return (
      <div className="space-y-3">
        <div className="text-muted-foreground py-8 text-center">
          <div className="bg-muted/30 mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full">
            <Settings className="h-6 w-6 opacity-50" />
          </div>
          <p className="text-sm font-medium">No providers available</p>
          <p className="mt-1 text-xs opacity-75">
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
