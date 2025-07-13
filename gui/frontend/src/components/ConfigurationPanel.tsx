import React, { useState } from 'react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from './ui/tabs';
import {
  ProviderSelector,
  VoiceSelector,
  ConfigForm,
} from '.';
import { VoiceSelectionPanel } from './VoiceSelectionPanel';
import { HistoryTab } from './HistoryTab';
import { HistoryDetailsPanel } from './HistoryDetailsPanel';
import { useConfiguration } from '../stores/appStore';
import type { ProviderInfo, VoiceEntry, TaskStatusResponse } from '../types';

interface ConfigurationPanelProps {
  providers: ProviderInfo[];
  voiceLibrary: Record<string, VoiceEntry[]>;
  loading: boolean;
  onProviderChange: (provider: string) => void;
  onVoiceSelect: (voice: VoiceEntry) => void;
  onConfigChange: (config: Record<string, any>) => void;
}

export const ConfigurationPanel: React.FC<ConfigurationPanelProps> = ({
  providers,
  voiceLibrary,
  loading,
  onProviderChange,
  onVoiceSelect,
  onConfigChange,
}) => {
  // Use store for client state
  const { selectedProvider, selectedVoice, currentConfig } = useConfiguration();
  const [showVoicePanel, setShowVoicePanel] = useState(false);
  const [selectedHistoryTask, setSelectedHistoryTask] = useState<TaskStatusResponse | null>(null);
  
  const handleVoiceSelect = (voice: VoiceEntry) => {
    onVoiceSelect(voice);
    setShowVoicePanel(false);
  };

  return (
    <div className="h-full flex flex-col relative">
      <Tabs defaultValue="settings" className="h-full flex flex-col">
        <div className="p-4 border-b border-border shrink-0">
          <TabsList className="w-full">
            <TabsTrigger value="settings" className="flex-1">Settings</TabsTrigger>
            <TabsTrigger value="history" className="flex-1">History</TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="settings" className="flex-1 overflow-y-auto min-h-0">
          {showVoicePanel && selectedProvider ? (
            /* Voice Selection Panel - replaces entire Settings content */
            <VoiceSelectionPanel
              provider={selectedProvider}
              voices={voiceLibrary[selectedProvider] || []}
              selectedVoice={selectedVoice}
              onVoiceSelect={handleVoiceSelect}
              onBack={() => setShowVoicePanel(false)}
            />
          ) : (
            /* Normal Settings Content */
            <div className="p-4 space-y-6">
              {/* Voice Selection */}
              {selectedProvider && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <label className="text-sm font-medium text-foreground">Voice</label>
                  </div>
                  <VoiceSelector
                    provider={selectedProvider}
                    voices={voiceLibrary[selectedProvider] || []}
                    selectedVoice={selectedVoice}
                    onVoiceSelect={onVoiceSelect}
                    onOpenVoicePanel={() => setShowVoicePanel(true)}
                  />
                </div>
              )}

              {/* Configuration Form */}
              {selectedProvider && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <label className="text-sm font-medium text-foreground">Parameters</label>
                  </div>
                  <ConfigForm
                    provider={selectedProvider}
                    providerInfo={providers.find((p) => p.identifier === selectedProvider)}
                    config={currentConfig}
                    onConfigChange={onConfigChange}
                  />
                </div>
              )}

              {/* Reset Button */}
              {selectedProvider && (
                <div className="pt-4 border-t border-border">
                  <button
                    className="w-full px-3 py-2 text-sm border border-border rounded-md hover:bg-accent hover:text-accent-foreground transition-colors"
                    onClick={() => onConfigChange({})}
                  >
                    Reset to defaults
                  </button>
                </div>
              )}
            </div>
          )}
        </TabsContent>

        <TabsContent value="history" className="flex-1 overflow-y-auto min-h-0">
          {selectedHistoryTask ? (
            <HistoryDetailsPanel
              task={selectedHistoryTask}
              onBack={() => setSelectedHistoryTask(null)}
            />
          ) : (
            <HistoryTab onTaskSelect={setSelectedHistoryTask} />
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
};