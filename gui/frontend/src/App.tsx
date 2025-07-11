import { useState, useEffect } from 'react';
import { AppHeader } from './components/AppHeader';
import { ConfigurationPanel } from './components/ConfigurationPanel';
import { ResultsPanel } from './components/ResultsPanel';
import { useBackendStatus } from './hooks/queries/useBackendStatus';
import { useProviders } from './hooks/queries/useProviders';
import { useVoiceLibrary } from './hooks/queries/useVoiceLibrary';
import { useAllTasks } from './hooks/queries/useTaskStatus';
import { useCreateTask } from './hooks/mutations/useTasks';
import type { VoiceEntry, GenerationRequest } from './types';

function App() {
  const [selectedProvider, setSelectedProvider] = useState<string | undefined>();
  const [selectedVoice, setSelectedVoice] = useState<VoiceEntry | undefined>();
  const [currentConfig, setCurrentConfig] = useState<Record<string, any>>({});
  const [text, setText] = useState<string>('');
  const [error, setError] = useState<string | undefined>();

  // Use TanStack Query hooks
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
  }, [providersError]);

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

  const handleTextChange = (text: string) => {
    setText(text);
  };

  const handleGenerate = async () => {
    if (!selectedProvider || !text.trim()) return;

    setError(undefined);

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
            selectedProvider={selectedProvider}
            voiceLibrary={voiceLibrary}
            selectedVoice={selectedVoice}
            currentConfig={currentConfig}
            text={text}
            loading={createTaskMutation.isPending || providersLoading}
            onProviderChange={handleProviderChange}
            onVoiceSelect={handleVoiceSelect}
            onConfigChange={handleConfigChange}
            onTextChange={handleTextChange}
            onGenerate={handleGenerate}
          />

          <ResultsPanel
            generationTasks={generationTasks}
            error={error}
            onDismissError={() => setError(undefined)}
          />
        </div>
      </div>
    </div>
  );
}

export default App;
