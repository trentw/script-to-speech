import React from 'react';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
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
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary"></div>
        <span className="ml-2 text-muted-foreground">Loading providers...</span>
      </div>
    );
  }

  if (!providers || providers.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <p>No TTS providers available</p>
        <p className="text-sm mt-1">Check your backend configuration</p>
      </div>
    );
  }

  const selectedProviderInfo = selectedProvider 
    ? providers.find(p => p.identifier === selectedProvider)
    : undefined;

  const handleProviderChange = (value: string) => {
    try {
      onProviderChange(value);
    } catch (error) {
      console.error('Error changing provider:', error);
    }
  };

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="provider-select">Select TTS Provider</Label>
        <Select
          value={selectedProvider || ''}
          onValueChange={handleProviderChange}
        >
          <SelectTrigger id="provider-select">
            <SelectValue placeholder="Choose a provider..." />
          </SelectTrigger>
          <SelectContent>
            {providers.map((provider) => (
              <SelectItem key={provider.identifier} value={provider.identifier}>
                <div className="flex flex-col">
                  <span className="font-medium">{provider.name}</span>
                  {provider.description && (
                    <span className="text-xs text-muted-foreground">
                      {provider.description}
                    </span>
                  )}
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      
      {selectedProviderInfo && (
        <div className="mt-3 p-4 bg-muted/50 rounded-lg border">
          <div className="space-y-2">
            <div className="font-medium text-foreground">
              {selectedProviderInfo.name}
            </div>
            <div className="text-sm text-muted-foreground">
              {selectedProviderInfo.description || 'No description available'}
            </div>
            <div className="grid grid-cols-3 gap-4 text-xs">
              <div className="text-center">
                <div className="font-medium text-foreground">Required</div>
                <div className="text-muted-foreground">{selectedProviderInfo.required_fields.length}</div>
              </div>
              <div className="text-center">
                <div className="font-medium text-foreground">Optional</div>
                <div className="text-muted-foreground">{selectedProviderInfo.optional_fields.length}</div>
              </div>
              <div className="text-center">
                <div className="font-medium text-foreground">Max Threads</div>
                <div className="text-muted-foreground">{selectedProviderInfo.max_threads}</div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};