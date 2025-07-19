import React, { useState } from 'react';
import { Search } from 'lucide-react';
import { SelectorPanel, SelectorCard } from '@/components/ui/selector';
import type { ProviderInfo, VoiceEntry } from '../types';

interface ProviderSelectionPanelProps {
  providers: ProviderInfo[];
  selectedProvider?: string;
  voiceLibrary: Record<string, VoiceEntry[]>;
  voiceCounts: Record<string, number>;
  providerErrors: Record<string, boolean>;
  onProviderSelect: (provider: string) => void;
  onBack: () => void;
}

export const ProviderSelectionPanel: React.FC<ProviderSelectionPanelProps> = ({
  providers,
  selectedProvider,
  voiceLibrary,
  voiceCounts,
  providerErrors,
  onProviderSelect,
  onBack
}) => {
  const [searchQuery, setSearchQuery] = useState('');

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
      return 'No preconfigured voices available';
    }
    return `${voiceCount} preconfigured voice${voiceCount !== 1 ? 's' : ''} available`;
  };

  const getProviderDescription = (provider: ProviderInfo) => {
    const requiredFields = provider.required_fields || [];
    const optionalFields = provider.optional_fields || [];
    
    // Start with empty description to remove redundant "[name] TTS provider" text
    let description = '';
    
    // Add required configuration section
    if (requiredFields.length > 0) {
      const requiredFieldNames = requiredFields.map(field => `**${field.name}**`).join(', ');
      description += `Required configuration: ${requiredFieldNames}`;
    }
    
    // Add optional configuration section
    if (optionalFields.length > 0) {
      const optionalFieldNames = optionalFields.map(field => `**${field.name}**`).join(', ');
      description += (description ? '\n' : '') + `Optional configuration: ${optionalFieldNames}`;
    }
    
    return description;
  };

  const getProviderAvatar = (provider: ProviderInfo) => {
    return provider.name.charAt(0).toUpperCase();
  };

  const handleProviderSelect = (provider: ProviderInfo) => {
    onProviderSelect(provider.identifier);
  };

  const filteredProviders = providers
    .filter(provider => {
      if (!searchQuery) return true;
      const name = provider.name.toLowerCase();
      const description = (provider.description || '').toLowerCase();
      return name.includes(searchQuery.toLowerCase()) || 
             description.includes(searchQuery.toLowerCase());
    })
    .sort((a, b) => {
      // Get voice counts for comparison
      const voiceCountA = voiceLibrary[a.identifier]?.length || voiceCounts[a.identifier] || 0;
      const voiceCountB = voiceLibrary[b.identifier]?.length || voiceCounts[b.identifier] || 0;
      
      // Sort by voice count (highest to lowest)
      return voiceCountB - voiceCountA;
    });

  return (
    <SelectorPanel
      isOpen={true}
      title="Select TTS Provider"
      onBack={onBack}
    >
      {/* Search */}
      <div className="pb-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search providers..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-border rounded-md bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
          />
        </div>
      </div>

      {/* Provider List */}
      <div className="space-y-1">
        <h4 className="text-sm font-medium text-muted-foreground mb-3">
          Available Providers ({filteredProviders.length})
        </h4>
        
        {filteredProviders.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <p className="text-sm">No providers found</p>
            <p className="text-xs mt-1">Try adjusting your search</p>
          </div>
        ) : (
          <div className="space-y-2">
            {filteredProviders.map((provider) => (
              <SelectorCard
                key={provider.identifier}
                item={provider}
                isSelected={selectedProvider === provider.identifier}
                onSelect={handleProviderSelect}
                renderAvatar={getProviderAvatar}
                renderPrimary={getProviderDisplayName}
                renderSecondary={getProviderSubtext}
                renderDescription={getProviderDescription}
              />
            ))}
          </div>
        )}
      </div>
    </SelectorPanel>
  );
};