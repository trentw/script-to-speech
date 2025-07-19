import { useEffect, useCallback } from 'react';
import { AppShell, AdaptiveNavigation, ResponsivePanel, MobileDrawer } from './components/layout';
import { useViewportSize } from './hooks/useViewportSize';
import { useBackendStatus } from './hooks/queries/useBackendStatus';
import { useProviders } from './hooks/queries/useProviders';
import { useVoiceLibrary } from './hooks/queries/useVoiceLibrary';
import { useAllVoiceCounts } from './hooks/queries/useAllVoiceCounts';
import { useAudioGeneration } from './hooks/audio/useAudioGeneration';
import { useConfiguration, useUserInput, useUIState, useLayout } from './stores/appStore';
import type { VoiceEntry, GenerationRequest } from './types';
import { Mic } from 'lucide-react';

// Import the new components
import { MainContent } from './components/app/MainContent';
import { HeaderContent } from './components/app/HeaderContent';
import { PanelContent } from './components/app/PanelContent';
import { SettingsContent } from './components/app/SettingsContent';
import { HistoryContent } from './components/app/HistoryContent';
import { FooterContent } from './components/app/FooterContent';
import { ErrorDisplay } from './components/app/ErrorDisplay';
import { AppStatus, AppLoading } from './components/app/AppStatus';

function App() {
  // Hooks
  const { isMobile } = useViewportSize();
  
  // Use Layout state for responsive behavior
  const { 
    sidebarExpanded, 
    activeModal, 
    toggleSidebar, 
    closeModal 
  } = useLayout();

  // Use Zustand store hooks for client state
  const { 
    selectedProvider, 
    selectedVoice, 
    currentConfig, 
    setSelectedProvider, 
    setSelectedVoice, 
    setCurrentConfig 
  } = useConfiguration();
  const { text } = useUserInput();
  const { setError, clearError } = useUIState();
  const { handleGenerate, isGenerating } = useAudioGeneration();

  // Use TanStack Query hooks for server state
  const { data: backendStatus } = useBackendStatus();
  const { data: providers, isPending: providersLoading, error: providersError } = useProviders();
  const { data: voiceLibraryData } = useVoiceLibrary(selectedProvider || '');

  // Get voice counts for all providers dynamically
  const { voiceCounts, providerErrors } = useAllVoiceCounts(providers || []);

  // Adapt voice library data to expected format
  const voiceLibrary: Record<string, VoiceEntry[]> = selectedProvider && voiceLibraryData 
    ? { [selectedProvider]: voiceLibraryData }
    : {};


  // Navigation items (only core app navigation)
  const navigationItems = [
    {
      id: 'tts',
      label: 'Text to Speech',
      icon: Mic,
      isActive: true
    }
  ];



  useEffect(() => {
    if (providersError) {
      setError(providersError.message);
    }
  }, [providersError, setError]);

  const handleProviderChange = (provider: string) => {
    clearError(); // Clear any existing errors
    setSelectedProvider(provider);
    setCurrentConfig({});
    setSelectedVoice(undefined);
  };

  const handleVoiceSelect = (voice: VoiceEntry) => {
    setSelectedVoice(voice);
    setCurrentConfig({ ...voice.config, sts_id: voice.sts_id });
  };

  const handleConfigChange = (config: Record<string, unknown>) => {
    setCurrentConfig(config);
  };

  const handleGenerateRequest = useCallback(async () => {
    if (!selectedProvider || !text.trim()) return;

    clearError();

    const request: GenerationRequest = {
      provider: selectedProvider,
      config: currentConfig,
      text: text,
      sts_id: selectedVoice?.sts_id,
      variants: 1,
    };

    try {
      await handleGenerate(request);
    } catch (error) {
      // Error is already handled by useAudioGeneration hook
      console.error('Generation failed:', error);
    }
  }, [selectedProvider, text, currentConfig, selectedVoice?.sts_id, handleGenerate, clearError]);

  // Keyboard shortcuts
  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
      event.preventDefault();
      if (selectedProvider && text.trim() && !isGenerating) {
        handleGenerateRequest();
      }
    }
  }, [selectedProvider, text, isGenerating, handleGenerateRequest]);

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [handleKeyDown]);


  if (!backendStatus) {
    return <AppLoading />;
  }

  if (!backendStatus.connected) {
    return <AppStatus connected={false} />;
  }

  return (
    <>
      <AppShell
        navigation={
          <AdaptiveNavigation
            items={navigationItems}
            isExpanded={sidebarExpanded}
            onToggleExpanded={toggleSidebar}
          />
        }
        header={<HeaderContent />}
        main={<MainContent handleGenerate={handleGenerateRequest} isGenerating={isGenerating} />}
        panel={
          !isMobile ? (
            <ResponsivePanel>
              <PanelContent
                providers={providers || []}
                voiceLibrary={voiceLibrary}
                voiceCounts={voiceCounts}
                providerErrors={providerErrors}
                loading={isGenerating || providersLoading}
                onProviderChange={handleProviderChange}
                onVoiceSelect={handleVoiceSelect}
                onConfigChange={handleConfigChange}
              />
            </ResponsivePanel>
          ) : undefined
        }
        footer={<FooterContent isGenerating={isGenerating} />}
      />

      {/* Mobile Drawers */}
      {isMobile && (
        <>
          <MobileDrawer
            title="Settings"
            isOpen={activeModal === 'settings'}
            onClose={closeModal}
          >
            <SettingsContent
              providers={providers || []}
              voiceLibrary={voiceLibrary}
              voiceCounts={voiceCounts}
              providerErrors={providerErrors}
              loading={isGenerating || providersLoading}
              onProviderChange={handleProviderChange}
              onVoiceSelect={handleVoiceSelect}
              onConfigChange={handleConfigChange}
            />
          </MobileDrawer>

          <MobileDrawer
            title="History"
            isOpen={activeModal === 'history'}
            onClose={closeModal}
          >
            <HistoryContent />
          </MobileDrawer>
        </>
      )}

      <ErrorDisplay />
    </>
  );
}

export default App;