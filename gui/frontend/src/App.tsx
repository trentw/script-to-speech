import { useEffect, useCallback, useMemo } from 'react';
import { AppShell, AdaptiveNavigation, ResponsivePanel, MobileDrawer } from './components/layout';
import { useViewportSize } from './hooks/useViewportSize';
import { useBackendStatus } from './hooks/queries/useBackendStatus';
import { useProviders } from './hooks/queries/useProviders';
import { useVoiceLibrary } from './hooks/queries/useVoiceLibrary';
import { useAllTasks } from './hooks/queries/useTaskStatus';
import { useCreateTask } from './hooks/mutations/useTasks';
import { useConfiguration, useUserInput, useUIState, useCentralAudio, useLayout } from './stores/appStore';
import { getAudioUrls, getAudioFilename } from './utils/audioUtils';
import type { VoiceEntry, GenerationRequest } from './types';
import { Mic } from 'lucide-react';

// Import the new components
import { MainContent } from './components/app/MainContent';
import { HeaderContent } from './components/app/HeaderContent';
import { PanelContent } from './components/app/PanelContent';
import { SettingsContent } from './components/app/SettingsContent';
import { HistoryContent } from './components/app/HistoryContent';
import { FooterContent } from './components/app/FooterContent';
import { ProviderSelector } from './components/app/ProviderSelector';
import { ErrorDisplay } from './components/app/ErrorDisplay';
import { AppStatus, AppLoading } from './components/app/AppStatus';

function App() {
  // Hooks
  const { isMobile, isTablet } = useViewportSize();
  
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
  const { text, setText } = useUserInput();
  const { error, setError, clearError } = useUIState();
  const { audioUrl, setAudioData, setLoading: setAudioLoading } = useCentralAudio();

  // Use TanStack Query hooks for server state
  const { data: backendStatus } = useBackendStatus();
  const { data: providers, isPending: providersLoading, error: providersError } = useProviders();
  const { data: voiceLibraryData } = useVoiceLibrary(selectedProvider || '');
  const { data: generationTasks = [] } = useAllTasks();
  const createTaskMutation = useCreateTask();

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

  // Update central audio player when new tasks complete
  useEffect(() => {
    if (!audioUrl) { // Only auto-update if no audio is currently loaded
      const completedTasks = generationTasks
        .filter(task => task.status === 'completed')
        .sort((a, b) => new Date(b.created_at || '').getTime() - new Date(a.created_at || '').getTime());
      
      const latestTask = completedTasks[0];
      if (!latestTask) return;

      const audioUrls = getAudioUrls(latestTask);
      if (audioUrls.length === 0) return;

      // Use first audio file for single player
      const taskAudioUrl = audioUrls[0];
      const displayText = latestTask.request?.text || latestTask.result?.text_preview || 'Generated audio';
      const provider = latestTask.request?.provider || latestTask.result?.provider;
      const voiceId = latestTask.request?.sts_id || latestTask.result?.voice_id;
      
      setAudioData(
        taskAudioUrl,
        displayText.length > 50 ? displayText.slice(0, 50) + '...' : displayText,
        [provider, voiceId].filter(Boolean).join(' • '),
        getAudioFilename(latestTask, 0)
      );
    }
  }, [generationTasks, audioUrl, setAudioData]);

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

  const handleGenerate = useCallback(async () => {
    if (!selectedProvider || !text.trim()) return;

    clearError();
    setAudioLoading(true);

    const request: GenerationRequest = {
      provider: selectedProvider,
      config: currentConfig,
      text: text,
      sts_id: selectedVoice?.sts_id,
      variants: 1,
    };

    createTaskMutation.mutate(request, {
      onSuccess: () => {
        setAudioData('', 'Generating audio...', 'Please wait', '', true);
      },
      onError: (error) => {
        setError(error.message);
        setAudioLoading(false);
      },
    });
  }, [selectedProvider, text, currentConfig, selectedVoice?.sts_id, createTaskMutation, clearError, setError, setAudioLoading, setAudioData]);

  // Keyboard shortcuts
  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
      event.preventDefault();
      if (selectedProvider && text.trim() && !createTaskMutation.isPending) {
        handleGenerate();
      }
    }
  }, [selectedProvider, text, createTaskMutation.isPending, handleGenerate]);

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [handleKeyDown]);

  const memoizedProviderSelector = useCallback(() => (
    <ProviderSelector
      providers={providers || []}
      handleProviderChange={handleProviderChange}
    />
  ), [providers, handleProviderChange]);

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
            onMobileMenuToggle={toggleSidebar}
          />
        }
        header={<HeaderContent ProviderSelector={memoizedProviderSelector} />}
        main={<MainContent handleGenerate={handleGenerate} isGenerating={createTaskMutation.isPending} />}
        panel={
          !isMobile ? (
            <ResponsivePanel>
              <PanelContent
                providers={providers || []}
                voiceLibrary={voiceLibrary}
                loading={createTaskMutation.isPending || providersLoading}
                onProviderChange={handleProviderChange}
                onVoiceSelect={handleVoiceSelect}
                onConfigChange={handleConfigChange}
              />
            </ResponsivePanel>
          ) : undefined
        }
        footer={<FooterContent isGenerating={createTaskMutation.isPending} />}
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
              loading={createTaskMutation.isPending || providersLoading}
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