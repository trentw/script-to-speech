import { createFileRoute } from '@tanstack/react-router';
import { Mic } from 'lucide-react';
import { useCallback, useEffect } from 'react';

import { RouteError } from '@/components/errors';

import { MainContent } from '../components/app/MainContent';
import { useAudioGeneration } from '../hooks/audio/useAudioGeneration';
import {
  useConfiguration,
  useUIState,
  useUserInput,
} from '../stores/appStore';
import type { GenerationRequest } from '../types';
import type { RouteStaticData } from '../types/route-metadata';

export const Route = createFileRoute('/tts')({
  component: TTSView,
  errorComponent: RouteError,
  staticData: {
    title: 'Text to Speech',
    icon: Mic,
    description:
      'Generate speech from text using multiple TTS providers and voices',
    navigation: {
      order: 1,
      showInNav: true,
    },
    ui: {
      showPanel: true,
      showFooter: true,
      mobileDrawers: ['settings', 'history'],
    },
    helpText:
      'Enter text and select a voice to generate natural-sounding speech. Supports multiple providers including OpenAI, ElevenLabs, and more.',
  } satisfies RouteStaticData,
});

function TTSView() {
  // Use Zustand store hooks for client state
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
  }, [
    selectedProvider,
    text,
    currentConfig,
    selectedVoice?.sts_id,
    handleGenerate,
    clearError,
  ]);

  // Keyboard shortcuts
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
        event.preventDefault();
        if (selectedProvider && text.trim() && !isGenerating) {
          handleGenerateRequest();
        }
      }
    },
    [selectedProvider, text, isGenerating, handleGenerateRequest]
  );

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [handleKeyDown]);

  // Cancel any pending audio generation when navigating away from TTS
  useEffect(() => {
    return () => {
      cancelGeneration();
    };
  }, [cancelGeneration]);

  return (
    <MainContent
      handleGenerate={handleGenerateRequest}
      isGenerating={isGenerating}
    />
  );
}
