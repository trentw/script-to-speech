import { useState, useEffect } from 'react';
import { ProviderSelector } from './components/ProviderSelector';
import { VoiceSelector } from './components/VoiceSelector';
import { ConfigForm } from './components/ConfigForm';
import { TextInput } from './components/TextInput';
import { GenerationStatus } from './components/GenerationStatus';
import { AudioPlayer } from './components/AudioPlayer';
import { BackendStatus } from './components/BackendStatus';
import { apiService } from './services/api';
import type { AppState, VoiceEntry, GenerationRequest } from './types';

function App() {
  const [appState, setAppState] = useState<AppState>({
    providers: [],
    voiceLibrary: {},
    currentConfig: {},
    text: '',
    generationTasks: [],
    loading: false,
  });

  const [connectionStatus, setConnectionStatus] = useState<'checking' | 'connected' | 'disconnected'>('checking');

  // Check backend connection on mount
  useEffect(() => {
    const checkConnection = async () => {
      const isHealthy = await apiService.healthCheck();
      setConnectionStatus(isHealthy ? 'connected' : 'disconnected');
    };
    
    checkConnection();
    const interval = setInterval(checkConnection, 30000); // Check every 30 seconds
    return () => clearInterval(interval);
  }, []);

  // Load providers on mount
  useEffect(() => {
    const loadProviders = async () => {
      if (connectionStatus !== 'connected') return;
      
      setAppState(prev => ({ ...prev, loading: true }));
      
      const response = await apiService.getProvidersInfo();
      if (response.data) {
        setAppState(prev => ({
          ...prev,
          providers: response.data!,
          loading: false,
        }));
      } else {
        setAppState(prev => ({
          ...prev,
          error: response.error,
          loading: false,
        }));
      }
    };

    loadProviders();
  }, [connectionStatus]);

  // Load voice library when provider is selected
  useEffect(() => {
    const loadVoiceLibrary = async () => {
      if (!appState.selectedProvider || connectionStatus !== 'connected') return;

      const response = await apiService.getProviderVoices(appState.selectedProvider);
      if (response.data) {
        setAppState(prev => ({
          ...prev,
          voiceLibrary: {
            ...prev.voiceLibrary,
            [appState.selectedProvider!]: response.data!,
          },
        }));
      }
    };

    loadVoiceLibrary();
  }, [appState.selectedProvider, connectionStatus]);

  const handleProviderChange = (provider: string) => {
    setAppState(prev => ({
      ...prev,
      selectedProvider: provider,
      currentConfig: {},
      selectedVoice: undefined,
    }));
  };

  const handleVoiceSelect = (voice: VoiceEntry) => {
    setAppState(prev => ({
      ...prev,
      selectedVoice: voice,
      currentConfig: { ...voice.config, sts_id: voice.sts_id },
    }));
  };

  const handleConfigChange = (config: Record<string, any>) => {
    setAppState(prev => ({
      ...prev,
      currentConfig: config,
    }));
  };

  const handleTextChange = (text: string) => {
    setAppState(prev => ({
      ...prev,
      text,
    }));
  };

  const handleGenerate = async () => {
    if (!appState.selectedProvider || !appState.text.trim()) return;

    setAppState(prev => ({ ...prev, loading: true }));

    const request: GenerationRequest = {
      provider: appState.selectedProvider!,
      config: appState.currentConfig,
      text: appState.text,
      sts_id: appState.selectedVoice?.sts_id,
      variants: 1,
    };

    const response = await apiService.createGenerationTask(request);
    
    if (response.data) {
      // Start polling for task status
      pollTaskStatus(response.data.task_id);
    } else {
      setAppState(prev => ({
        ...prev,
        error: response.error,
        loading: false,
      }));
    }
  };

  const pollTaskStatus = async (taskId: string) => {
    const pollInterval = setInterval(async () => {
      const response = await apiService.getTaskStatus(taskId);
      
      if (response.data) {
        const task = response.data;
        
        setAppState(prev => ({
          ...prev,
          generationTasks: [
            ...prev.generationTasks.filter(t => t.task_id !== taskId),
            task,
          ],
        }));

        if (task.status === 'completed' || task.status === 'failed') {
          clearInterval(pollInterval);
          setAppState(prev => ({ ...prev, loading: false }));
        }
      } else {
        clearInterval(pollInterval);
        setAppState(prev => ({
          ...prev,
          error: response.error,
          loading: false,
        }));
      }
    }, 1000);
  };

  if (connectionStatus === 'checking') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Connecting to backend...</p>
        </div>
      </div>
    );
  }

  if (connectionStatus === 'disconnected') {
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
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Script to Speech</h1>
              <p className="text-sm text-gray-500">TTS Playground Desktop Application</p>
            </div>
            <div className="max-w-xs">
              <BackendStatus onStatusChange={(isRunning) => {
                setConnectionStatus(isRunning ? 'connected' : 'disconnected');
              }} />
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Left Panel - Configuration */}
          <div className="lg:col-span-2 space-y-6">
            
            {/* Text Input */}
            <div className="card p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Text to Speech</h2>
              <TextInput
                value={appState.text}
                onChange={handleTextChange}
                placeholder="Enter the text you want to convert to speech..."
              />
            </div>

            {/* Provider Selection */}
            <div className="card p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">TTS Provider</h2>
              <ProviderSelector
                providers={appState.providers}
                selectedProvider={appState.selectedProvider}
                onProviderChange={handleProviderChange}
                loading={appState.loading}
              />
            </div>

            {/* Voice Selection */}
            {appState.selectedProvider && (
              <div className="card p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Voice Selection</h2>
                <VoiceSelector
                  provider={appState.selectedProvider}
                  voices={appState.voiceLibrary[appState.selectedProvider] || []}
                  selectedVoice={appState.selectedVoice}
                  onVoiceSelect={handleVoiceSelect}
                />
              </div>
            )}

            {/* Configuration Form */}
            {appState.selectedProvider && (
              <div className="card p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Configuration</h2>
                <ConfigForm
                  provider={appState.selectedProvider}
                  providerInfo={appState.providers.find(p => p.identifier === appState.selectedProvider)}
                  config={appState.currentConfig}
                  onConfigChange={handleConfigChange}
                />
              </div>
            )}

            {/* Generate Button */}
            <div className="flex justify-center">
              <button
                className="btn-primary px-8 py-3 text-lg"
                onClick={handleGenerate}
                disabled={!appState.selectedProvider || !appState.text.trim() || appState.loading}
              >
                {appState.loading ? (
                  <div className="flex items-center space-x-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    <span>Generating...</span>
                  </div>
                ) : (
                  'Generate Speech'
                )}
              </button>
            </div>
          </div>

          {/* Right Panel - Status and Results */}
          <div className="space-y-6">
            
            {/* Generation Status */}
            <div className="card p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Generation Status</h2>
              <GenerationStatus tasks={appState.generationTasks} />
            </div>

            {/* Audio Player */}
            {appState.generationTasks.some(t => t.status === 'completed' && t.result) && (
              <div className="card p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Generated Audio</h2>
                <AudioPlayer
                  tasks={appState.generationTasks.filter(t => t.status === 'completed' && t.result)}
                />
              </div>
            )}

            {/* Error Display */}
            {appState.error && (
              <div className="card p-6 border-red-200 bg-red-50">
                <h2 className="text-lg font-semibold text-red-800 mb-2">Error</h2>
                <p className="text-red-600">{appState.error}</p>
                <button
                  className="btn-secondary mt-3"
                  onClick={() => setAppState(prev => ({ ...prev, error: undefined }))}
                >
                  Dismiss
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
