import { createFileRoute, Navigate } from '@tanstack/react-router';
import { useCallback, useEffect } from 'react';

import { MainContent } from '@/components/app/MainContent';
import { useAudioGeneration } from '@/hooks/audio/useAudioGeneration';
import {
  useConfiguration,
  useProject,
  useUIState,
  useUserInput,
} from '@/stores/appStore';
import type { GenerationRequest } from '@/types';
import type { RouteStaticData } from '@/types/route-metadata';

// Static metadata for this route
const staticData: RouteStaticData = {
  ui: {
    showPanel: true, // Show TTS panel for voice testing
    showFooter: true,
    mobileDrawers: ['settings', 'history'],
  },
};

export const Route = createFileRoute('/project/test')({
  component: ProjectVoiceTest,
  staticData,
});

function ProjectVoiceTest() {
  const projectState = useProject();

  // Call all hooks before any conditional logic
  const { selectedProvider, selectedVoice, currentConfig } = useConfiguration();
  const { text } = useUserInput();
  const { clearError } = useUIState();
  const { handleGenerate, isGenerating, cancelGeneration } =
    useAudioGeneration();

  const handleGenerateRequest = useCallback(async () => {
    if (!selectedProvider || !text.trim()) return;

    clearError();

    const request: GenerationRequest = {
      provider: selectedProvider,
      config: currentConfig,
      text,
      sts_id: selectedVoice?.sts_id,
      variants: 1,
    };

    try {
      await handleGenerate(request);
    } catch (generationError) {
      console.error('Project voice testing failed:', generationError);
    }
  }, [
    selectedProvider,
    text,
    currentConfig,
    selectedVoice?.sts_id,
    handleGenerate,
    clearError,
  ]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
        event.preventDefault();
        if (selectedProvider && text.trim() && !isGenerating) {
          void handleGenerateRequest();
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [selectedProvider, text, isGenerating, handleGenerateRequest]);

  useEffect(() => {
    return () => {
      cancelGeneration();
    };
  }, [cancelGeneration]);

  // Type guard and redirect if not in project mode (after all hooks)
  if (projectState.mode !== 'project') {
    return <Navigate to="/" replace />;
  }

  return (
    <MainContent
      handleGenerate={handleGenerateRequest}
      isGenerating={isGenerating}
    />
  );
}
