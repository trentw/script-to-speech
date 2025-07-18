import React, { useState } from 'react';
import { AnimatedTabs } from './ui/animated-tabs';
import {
  VoiceSelector,
  ConfigForm,
} from '.';
import { VoiceSelectionPanel } from './VoiceSelectionPanel';
import { ProviderSelectionSelector } from './app/ProviderSelectionSelector';
import { ProviderSelectionPanel } from './ProviderSelectionPanel';
import { HistoryTab } from './HistoryTab';
import { HistoryDetailsPanel } from './HistoryDetailsPanel';
import { useConfiguration } from '../stores/appStore';
import { appButtonVariants } from './ui/button-variants';
import type { ProviderInfo, VoiceEntry, TaskStatusResponse } from '../types';

interface ConfigurationPanelProps {
  providers: ProviderInfo[];
  voiceLibrary: Record<string, VoiceEntry[]>;
  voiceCounts: Record<string, number>;
  providerErrors: Record<string, boolean>;
  loading: boolean;
  onProviderChange: (provider: string) => void;
  onVoiceSelect: (voice: VoiceEntry) => void;
  onConfigChange: (config: Record<string, any>) => void;
}

export const ConfigurationPanel: React.FC<ConfigurationPanelProps> = ({
  providers,
  voiceLibrary,
  voiceCounts,
  providerErrors,
  loading: _loading,
  onProviderChange,
  onVoiceSelect,
  onConfigChange,
}) => {
  // Use store for client state
  const { selectedProvider, selectedVoice, currentConfig } = useConfiguration();
  const [showVoicePanel, setShowVoicePanel] = useState(false);
  const [showProviderPanel, setShowProviderPanel] = useState(false);
  const [selectedHistoryTask, setSelectedHistoryTask] = useState<TaskStatusResponse | null>(null);
  const [isTransitioning, setIsTransitioning] = useState(false);
  
  const handleVoiceSelect = (voice: VoiceEntry) => {
    onVoiceSelect(voice);
    handleBackToSettings();
  };

  const handleProviderSelect = (provider: string) => {
    onProviderChange(provider);
    handleBackToSettings();
  };

  const handleShowVoicePanel = () => {
    setIsTransitioning(true);
    setTimeout(() => {
      setShowVoicePanel(true);
      setIsTransitioning(false);
    }, 150);
  };

  const handleShowProviderPanel = () => {
    setIsTransitioning(true);
    setTimeout(() => {
      setShowProviderPanel(true);
      setIsTransitioning(false);
    }, 150);
  };

  const handleBackToSettings = () => {
    setIsTransitioning(true);
    setTimeout(() => {
      setShowVoicePanel(false);
      setShowProviderPanel(false);
      setIsTransitioning(false);
    }, 150);
  };

  const handleShowHistoryDetails = (task: TaskStatusResponse) => {
    setIsTransitioning(true);
    setTimeout(() => {
      setSelectedHistoryTask(task);
      setIsTransitioning(false);
    }, 150);
  };

  const handleBackToHistory = () => {
    setIsTransitioning(true);
    setTimeout(() => {
      setSelectedHistoryTask(null);
      setIsTransitioning(false);
    }, 150);
  };

  return (
    <div className="h-full flex flex-col relative">
      <AnimatedTabs defaultValue="settings" className="h-full flex flex-col">
        <div className="px-4 pt-4 pb-0 shrink-0">
          <AnimatedTabs.List className="w-full">
            <AnimatedTabs.Trigger value="settings">Settings</AnimatedTabs.Trigger>
            <AnimatedTabs.Trigger value="history">History</AnimatedTabs.Trigger>
          </AnimatedTabs.List>
        </div>
        
        <AnimatedTabs.Content value="settings" className="flex-1 overflow-hidden min-h-0 relative">
              <div className={`absolute inset-0 transition-all duration-300 ease-in-out ${isTransitioning ? 'opacity-50' : 'opacity-100'}`}>
                <div className={`h-full overflow-y-auto transform transition-transform duration-300 ease-in-out ${
                  showVoicePanel || showProviderPanel ? '-translate-x-full' : 'translate-x-0'
                }`}>
              {/* Normal Settings Content */}
              <div className="px-4 py-4 space-y-6">
                {/* Provider Selection */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <label className="text-sm font-medium text-foreground">Text to Speech Provider</label>
                  </div>
                  <ProviderSelectionSelector
                    providers={providers}
                    selectedProvider={selectedProvider}
                    voiceLibrary={voiceLibrary}
                    voiceCounts={voiceCounts}
                    providerErrors={providerErrors}
                    onProviderSelect={onProviderChange}
                    onOpenProviderPanel={handleShowProviderPanel}
                  />
                </div>

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
                      onOpenVoicePanel={handleShowVoicePanel}
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
                      className={`w-full ${appButtonVariants({ variant: "reset", size: "default" })}`}
                      onClick={() => onConfigChange({})}
                    >
                      Reset to defaults
                    </button>
                  </div>
                )}
              </div>
            </div>
            
            {/* Selection Panels - slide in from the right */}
            <div className={`absolute inset-0 h-full overflow-y-auto transform transition-transform duration-300 ease-in-out ${
              showVoicePanel || showProviderPanel ? 'translate-x-0' : 'translate-x-full'
            }`}>
              {showProviderPanel && (
                <ProviderSelectionPanel
                  providers={providers}
                  selectedProvider={selectedProvider}
                  voiceLibrary={voiceLibrary}
                  voiceCounts={voiceCounts}
                  providerErrors={providerErrors}
                  onProviderSelect={handleProviderSelect}
                  onBack={handleBackToSettings}
                />
              )}
              {showVoicePanel && selectedProvider && (
                <VoiceSelectionPanel
                  provider={selectedProvider}
                  voices={voiceLibrary[selectedProvider] || []}
                  selectedVoice={selectedVoice}
                  onVoiceSelect={handleVoiceSelect}
                  onBack={handleBackToSettings}
                />
              )}
            </div>
          </div>
        </AnimatedTabs.Content>

        <AnimatedTabs.Content value="history" className="flex-1 overflow-hidden min-h-0 relative">
          <div className={`absolute inset-0 transition-all duration-300 ease-in-out ${isTransitioning ? 'opacity-50' : 'opacity-100'}`}>
            <div className={`h-full overflow-y-auto transform transition-transform duration-300 ease-in-out ${
              selectedHistoryTask ? '-translate-x-full' : 'translate-x-0'
            }`}>
              <HistoryTab onTaskSelect={handleShowHistoryDetails} />
            </div>
            
            {/* History Details Panel - slides in from the right */}
            <div className={`absolute inset-0 h-full overflow-y-auto transform transition-transform duration-300 ease-in-out ${
              selectedHistoryTask ? 'translate-x-0' : 'translate-x-full'
            }`}>
              {selectedHistoryTask && (
                <HistoryDetailsPanel
                  task={selectedHistoryTask}
                  onBack={handleBackToHistory}
                />
              )}
            </div>
          </div>
        </AnimatedTabs.Content>
      </AnimatedTabs>
    </div>
  );
};