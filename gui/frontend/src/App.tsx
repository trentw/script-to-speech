import { useEffect, useCallback, useState } from 'react';
import { ConfigurationPanel } from './components/ConfigurationPanel';
import { UniversalAudioPlayer } from './components/UniversalAudioPlayer';
import { useBackendStatus } from './hooks/queries/useBackendStatus';
import { useProviders } from './hooks/queries/useProviders';
import { useVoiceLibrary } from './hooks/queries/useVoiceLibrary';
import { useAllTasks } from './hooks/queries/useTaskStatus';
import { useCreateTask } from './hooks/mutations/useTasks';
import { useConfiguration, useUserInput, useUIState, useCentralAudio } from './stores/appStore';
import { getAudioUrls, getAudioFilename } from './utils/audioUtils';
import { appButtonVariants } from './components/ui/button-variants';
import type { VoiceEntry, GenerationRequest } from './types';
import { ChevronLeft, ChevronRight, Menu } from 'lucide-react';

function App() {
  // Local state for sidebar collapse
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

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
  const { audioUrl, primaryText, secondaryText, downloadFilename, loading: audioLoading, autoplay, setAudioData, setLoading: setAudioLoading } = useCentralAudio();

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
  }, [selectedProvider, text, currentConfig, selectedVoice?.sts_id, createTaskMutation, clearError, setError, setAudioLoading]);

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

  if (!backendStatus) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Connecting to backend...</p>
        </div>
      </div>
    );
  }

  if (!backendStatus.connected) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <div className="text-destructive text-6xl mb-4">⚠️</div>
          <h1 className="text-2xl font-bold text-foreground mb-4">Backend Disconnected</h1>
          <p className="text-muted-foreground mb-4">
            Cannot connect to the TTS backend server at http://127.0.0.1:8000
          </p>
          <p className="text-sm text-muted-foreground">
            Make sure the backend server is running: <code className="bg-muted px-1 py-0.5 rounded">cd gui/backend && uv run sts-gui-server</code>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen bg-background flex">
      {/* Left Sidebar - Navigation */}
      <div className={`border-r border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 flex flex-col transition-all duration-300 ease-in-out ${
        sidebarCollapsed ? 'w-16' : 'w-64'
      }`}>
        <div className="p-4 space-y-4">
          {/* Header */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              {!sidebarCollapsed && (
                <div>
                  <h1 className="text-xl font-bold tracking-tight">Script to Speech</h1>
                  <p className="text-xs text-muted-foreground">
                    Multi-provider TTS
                  </p>
                </div>
              )}
              <button
                className={appButtonVariants({ variant: "sidebar-toggle", size: "icon-sm" })}
                onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
                title={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
              >
                {sidebarCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
              </button>
            </div>
          </div>
          
          {/* Navigation items */}
          <div className="space-y-2">
            <div className={`px-3 py-2 rounded-md bg-accent text-accent-foreground text-sm flex items-center gap-2 ${
              sidebarCollapsed ? 'justify-center' : ''
            }`}>
              <Menu size={16} />
              {!sidebarCollapsed && <span>Text to Speech</span>}
            </div>
          </div>
        </div>
        
        {/* Backend Status at bottom */}
        <div className="p-4 border-t border-border mt-auto">
          <div className={`flex items-center gap-2 text-xs ${sidebarCollapsed ? 'justify-center' : ''}`}>
            <div className={`w-2 h-2 rounded-full ${backendStatus?.connected ? 'bg-green-500' : 'bg-red-500'}`} />
            {!sidebarCollapsed && (
              <span className="text-muted-foreground">
                Backend: {backendStatus?.connected ? 'Running' : 'Disconnected'}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex flex-col flex-1">
        {/* Enhanced Header Bar */}
        <div className="border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
          <div className="px-6 py-4 flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <h2 className="text-lg font-semibold text-foreground">Text to Speech</h2>
              <div className="flex items-center space-x-2">
                <label className="text-sm text-muted-foreground">Provider:</label>
                <select
                  className="px-3 py-2 border border-border rounded-lg bg-background text-foreground hover:border-accent transition-colors focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                  value={selectedProvider || ''}
                  onChange={(e) => handleProviderChange(e.target.value)}
                >
                  <option value="" key="select-provider-placeholder">Select Provider</option>
                  {providers?.map((provider) => (
                    <option key={provider.identifier} value={provider.identifier}>
                      {provider.name}
                    </option>
                  ))}
                </select>
                {selectedProvider && (
                  <div className="text-xs text-muted-foreground bg-muted/30 px-2 py-1 rounded-md">
                    {providers?.find(p => p.identifier === selectedProvider)?.description || 
                     `${selectedProvider.charAt(0).toUpperCase() + selectedProvider.slice(1)} TTS`}
                  </div>
                )}
              </div>
            </div>
            
            {/* Header Actions */}
            <div className="flex items-center space-x-2">
              <div className="flex items-center gap-2 text-xs">
                <div className={`w-2 h-2 rounded-full ${backendStatus?.connected ? 'bg-green-500' : 'bg-red-500'}`} />
                <span className="text-muted-foreground">
                  {backendStatus?.connected ? 'Backend Connected' : 'Backend Disconnected'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Content - Main area with right panel */}
        <div className="flex-1 flex">
          {/* Main Text Input Area */}
          <div className="flex-1 flex flex-col">
            {/* Text Input Area */}
            <div className="flex-1 p-6">
              <div className="h-full flex flex-col">
                <div className="flex-1 mb-4 relative">
                  <textarea
                    className="w-full h-full min-h-[400px] resize-none border border-border rounded-lg p-4 pr-24 bg-background text-lg placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all duration-200"
                    placeholder="Write something to say..."
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                  />
                  
                  {/* Character count overlay - positioned inside textarea */}
                  <div className={`absolute bottom-3 right-3 text-xs px-3 py-1.5 rounded-md font-medium border transition-colors ${
                    text.length > 4000 ? 'text-destructive bg-destructive/10 border-destructive/20' :
                    text.length > 2000 ? 'text-amber-600 bg-amber-50 border-amber-200 dark:text-amber-400 dark:bg-amber-950 dark:border-amber-800' :
                    'text-muted-foreground bg-background/90 border-border/50'
                  } backdrop-blur-sm shadow-sm`}>
                    {text.length.toLocaleString()} / 5,000
                  </div>
                </div>
                
                {/* Warning and Generate button */}
                <div className="flex items-center justify-between pt-2">
                  <div className="text-sm text-muted-foreground">
                    {text.length > 1000 && (
                      <span className="text-amber-600 flex items-center gap-1">
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                        </svg>
                        Long text may take more time to generate
                      </span>
                    )}
                  </div>
                  <button
                    className={appButtonVariants({ variant: "primary", size: "lg" })}
                    onClick={handleGenerate}
                    disabled={!selectedProvider || !text.trim() || createTaskMutation.isPending}
                    title={`Generate Speech (${navigator.userAgent.includes('Mac') ? '⌘' : 'Ctrl'}+Enter)`}
                  >
                    {createTaskMutation.isPending ? (
                      <div className="flex items-center space-x-2">
                        <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent"></div>
                        <span>Generating...</span>
                      </div>
                    ) : (
                      <div className="flex items-center space-x-2">
                        <span>Generate speech</span>
                        <span className="text-xs opacity-75">{navigator.userAgent.includes('Mac') ? '⌘' : 'Ctrl'}+Enter</span>
                      </div>
                    )}
                  </button>
                </div>
              </div>
            </div>

            {/* Persistent Audio Player - always visible */}
            <div className="border-t border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
              <div className="p-4">
                <UniversalAudioPlayer
                  audioUrl={audioUrl}
                  primaryText={primaryText}
                  secondaryText={secondaryText}
                  downloadFilename={downloadFilename}
                  loading={audioLoading || createTaskMutation.isPending}
                  autoplay={autoplay}
                />
              </div>
            </div>
          </div>

          {/* Right Panel - Configuration */}
          <div className="w-80 border-l border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
            <ConfigurationPanel
              providers={providers || []}
              voiceLibrary={voiceLibrary}
              loading={createTaskMutation.isPending || providersLoading}
              onProviderChange={handleProviderChange}
              onVoiceSelect={handleVoiceSelect}
              onConfigChange={handleConfigChange}
            />
          </div>
        </div>
      </div>

      {/* Error Display - Fixed positioning */}
      {error && (
        <div className="absolute bottom-4 left-4 right-4 z-50">
          <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-lg backdrop-blur supports-[backdrop-filter]:bg-destructive/5">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-medium text-destructive">Generation Error</h4>
                <p className="text-sm text-destructive/80 mt-1">{error}</p>
              </div>
              <button
                className={`${appButtonVariants({ variant: "list-action", size: "sm" })} text-destructive hover:text-destructive/80 border border-destructive/20 hover:bg-destructive/10`}
                onClick={clearError}
              >
                Dismiss
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
