import React, { useState } from 'react';

import { useConfiguration } from '../stores/appStore';
import type { ProviderInfo, TaskStatusResponse, VoiceEntry } from '../types';
import { ConfigForm, VoiceSelector } from '.';
import { ProviderSelectionSelector } from './app/ProviderSelectionSelector';
import { HistoryDetailsPanel } from './HistoryDetailsPanel';
import { HistoryTab } from './HistoryTab';
import { ProviderSelectionPanel } from './ProviderSelectionPanel';
import { AnimatedTabs } from './ui/animated-tabs';
import { appButtonVariants } from './ui/button-variants';
import { VoiceSelectionPanel } from './VoiceSelectionPanel';

interface ConfigurationPanelProps {
  providers: ProviderInfo[];
  voiceLibrary: Record<string, VoiceEntry[]>;
  voiceCounts: Record<string, number>;
  providerErrors: Record<string, boolean>;
  loading: boolean;
  onProviderChange: (provider: string) => void;
  onVoiceSelect: (voice: VoiceEntry) => void;
  onConfigChange: (
    config: Record<string, string | number | boolean | string[]>
  ) => void;
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
  const [selectedHistoryTask, setSelectedHistoryTask] =
    useState<TaskStatusResponse | null>(null);
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
    <div className="relative flex h-full flex-col">
      <AnimatedTabs defaultValue="settings" className="flex h-full flex-col">
        <div className="shrink-0 px-4 pt-4 pb-0">
          <AnimatedTabs.List className="w-full">
            <AnimatedTabs.Trigger value="settings">
              Settings
            </AnimatedTabs.Trigger>
            <AnimatedTabs.Trigger value="history">History</AnimatedTabs.Trigger>
          </AnimatedTabs.List>
        </div>

        <AnimatedTabs.Content
          value="settings"
          className="relative min-h-0 flex-1 overflow-hidden"
        >
          <div
            className={`absolute inset-0 transition-all duration-300 ease-in-out ${isTransitioning ? 'opacity-50' : 'opacity-100'}`}
          >
            <div
              className={`h-full transform overflow-y-auto transition-transform duration-300 ease-in-out ${
                showVoicePanel || showProviderPanel
                  ? '-translate-x-full'
                  : 'translate-x-0'
              }`}
            >
              {/* Normal Settings Content */}
              <div className="space-y-6 px-4 py-4">
                {/* Provider Selection */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <label
                      htmlFor="provider-selector"
                      className="text-foreground text-sm font-medium"
                    >
                      Text to Speech Provider
                    </label>
                  </div>
                  <div id="provider-selector">
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
                </div>

                {/* Voice Selection */}
                {selectedProvider && (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <label
                        htmlFor="voice-selector"
                        className="text-foreground text-sm font-medium"
                      >
                        Voice
                      </label>
                    </div>
                    <div id="voice-selector">
                      <VoiceSelector
                        provider={selectedProvider}
                        voices={voiceLibrary[selectedProvider] || []}
                        selectedVoice={selectedVoice}
                        onVoiceSelect={onVoiceSelect}
                        onOpenVoicePanel={handleShowVoicePanel}
                      />
                    </div>
                  </div>
                )}

                {/* Configuration Form */}
                {selectedProvider && (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <label
                        htmlFor="config-form"
                        className="text-foreground text-sm font-medium"
                      >
                        Parameters
                      </label>
                    </div>
                    <div id="config-form">
                      <ConfigForm
                        provider={selectedProvider}
                        providerInfo={providers.find(
                          (p) => p.identifier === selectedProvider
                        )}
                        config={currentConfig}
                        onConfigChange={onConfigChange}
                      />
                    </div>
                  </div>
                )}

                {/* Reset Button */}
                {selectedProvider && (
                  <div className="border-border border-t pt-4">
                    <button
                      className={`w-full ${appButtonVariants({ variant: 'reset', size: 'default' })}`}
                      onClick={() => onConfigChange({})}
                    >
                      Reset to defaults
                    </button>
                  </div>
                )}
              </div>
            </div>

            {/* Selection Panels - slide in from the right */}
            <div
              className={`absolute inset-0 h-full transform overflow-y-auto transition-transform duration-300 ease-in-out ${
                showVoicePanel || showProviderPanel
                  ? 'translate-x-0'
                  : 'translate-x-full'
              }`}
            >
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
                  providerDisplayName={
                    providers.find((p) => p.identifier === selectedProvider)
                      ?.name
                  }
                  voices={voiceLibrary[selectedProvider] || []}
                  selectedVoice={selectedVoice}
                  onVoiceSelect={handleVoiceSelect}
                  onBack={handleBackToSettings}
                />
              )}
            </div>
          </div>
        </AnimatedTabs.Content>

        <AnimatedTabs.Content
          value="history"
          className="relative min-h-0 flex-1 overflow-hidden"
        >
          <div
            className={`absolute inset-0 transition-all duration-300 ease-in-out ${isTransitioning ? 'opacity-50' : 'opacity-100'}`}
          >
            <div
              className={`h-full transform overflow-y-auto transition-transform duration-300 ease-in-out ${
                selectedHistoryTask ? '-translate-x-full' : 'translate-x-0'
              }`}
            >
              <HistoryTab onTaskSelect={handleShowHistoryDetails} />
            </div>

            {/* History Details Panel - slides in from the right */}
            <div
              className={`absolute inset-0 h-full transform overflow-y-auto transition-transform duration-300 ease-in-out ${
                selectedHistoryTask ? 'translate-x-0' : 'translate-x-full'
              }`}
            >
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
