import React from 'react';
import type { ProviderInfo } from '../types';

interface ProviderSelectorProps {
  providers: ProviderInfo[];
  selectedProvider?: string;
  onProviderChange: (provider: string) => void;
  loading?: boolean;
}

export const ProviderSelector: React.FC<ProviderSelectorProps> = ({
  providers,
  selectedProvider,
  onProviderChange,
  loading = false
}) => {
  if (loading && providers.length === 0) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
        <span className="ml-2 text-gray-600">Loading providers...</span>
      </div>
    );
  }

  if (providers.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <p>No TTS providers available</p>
        <p className="text-sm mt-1">Check your backend configuration</p>
      </div>
    );
  }

  return (
    <div className="form-group">
      <label className="form-label">Select TTS Provider</label>
      <select
        className="select-field"
        value={selectedProvider || ''}
        onChange={(e) => onProviderChange(e.target.value)}
      >
        <option value="">Choose a provider...</option>
        {providers.map((provider) => (
          <option key={provider.identifier} value={provider.identifier}>
            {provider.name}
            {provider.description && ` - ${provider.description}`}
          </option>
        ))}
      </select>
      
      {selectedProvider && (
        <div className="mt-3 p-3 bg-blue-50 rounded-md">
          {(() => {
            const provider = providers.find(p => p.identifier === selectedProvider);
            if (!provider) return null;
            
            return (
              <div className="text-sm">
                <div className="font-medium text-blue-900 mb-1">
                  {provider.name}
                </div>
                <div className="text-blue-700 mb-2">
                  {provider.description || 'No description available'}
                </div>
                <div className="grid grid-cols-2 gap-4 text-xs">
                  <div>
                    <span className="font-medium">Required fields:</span>
                    <span className="ml-1">{provider.required_fields.length}</span>
                  </div>
                  <div>
                    <span className="font-medium">Optional fields:</span>
                    <span className="ml-1">{provider.optional_fields.length}</span>
                  </div>
                  <div>
                    <span className="font-medium">Max threads:</span>
                    <span className="ml-1">{provider.max_threads}</span>
                  </div>
                </div>
              </div>
            );
          })()}
        </div>
      )}
    </div>
  );
};