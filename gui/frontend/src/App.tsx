import { useEffect } from 'react';
import { AppHeader } from './components/AppHeader';
import { ConfigurationPanel } from './components/ConfigurationPanel';
import { ResultsPanel } from './components/ResultsPanel';
import { useBackendStatus } from './hooks/queries/useBackendStatus';
import { useProviders } from './hooks/queries/useProviders';
import { useVoiceLibrary } from './hooks/queries/useVoiceLibrary';
import { useAllTasks } from './hooks/queries/useTaskStatus';
import { useCreateTask } from './hooks/mutations/useTasks';
import { useConfiguration, useUserInput, useUIState } from './stores/appStore';
import type { VoiceEntry, GenerationRequest } from './types';

function App() {
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

  useEffect(() => {
    if (providersError) {
      setError(providersError.message);
    }
  }, [providersError, setError]);

  const handleProviderChange = (provider: string) => {
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

  const handleGenerate = async () => {
    if (!selectedProvider || !text.trim()) return;

    clearError();

    const request: GenerationRequest = {
      provider: selectedProvider,
      config: currentConfig,
      text: text,
      sts_id: selectedVoice?.sts_id,
      variants: 1,
    };

    createTaskMutation.mutate(request, {
      onError: (error) => {
        setError(error.message);
      },
    });
  };

  if (!backendStatus) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Connecting to backend...</p>
        </div>
      </div>
    );
  }

  if (!backendStatus.connected) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="text-red-600 text-6xl mb-4">⚠️</div>
          <h1 className="text-2xl font-bold text-gray-900 mb-4">Backend Disconnected</h1>
          <p className="text-gray-600 mb-4">
            Cannot connect to the TTS backend server at http://127.0.0.1:8000
          </p>
          <p className="text-sm text-gray-500">
            Make sure the backend server is running: <code>cd gui/backend && uv run sts-gui-server</code>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <AppHeader onStatusChange={() => {}} />

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          <ConfigurationPanel
            providers={providers || []}
            voiceLibrary={voiceLibrary}
            loading={createTaskMutation.isPending || providersLoading}
            onProviderChange={handleProviderChange}
            onVoiceSelect={handleVoiceSelect}
            onConfigChange={handleConfigChange}
            onGenerate={handleGenerate}
          />

          <ResultsPanel
            generationTasks={generationTasks}
          />
        </div>
      </div>
    </div>
  );
}

export default App;
