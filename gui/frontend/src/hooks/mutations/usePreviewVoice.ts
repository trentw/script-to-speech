import { useMutation } from '@tanstack/react-query';

import { apiService } from '@/services/api';
import { useCentralAudio } from '@/stores/appStore';
import type { PreviewVoiceResponse } from '@/types/voice-casting';

interface PreviewVoiceOptions {
  provider: string;
  voiceId: string;
  text?: string;
  characterName?: string;
  config?: Record<string, any>;
}

/**
 * Hook to generate a voice preview for character casting
 */
export function usePreviewVoice() {
  const { setAudioData, setLoading } = useCentralAudio();

  return useMutation({
    mutationFn: async ({
      provider,
      voiceId,
      text,
      characterName,
      config = {},
    }: PreviewVoiceOptions): Promise<PreviewVoiceResponse> => {
      // Default preview text if none provided
      const previewText = text || 
        `Hello, my name is ${characterName || 'Character'}. This is a preview of my voice for the screenplay.`;

      // Set loading state
      setLoading(true);

      // Use voice casting preview endpoint
      const response = await apiService.previewVoice({
        provider,
        voice_id: voiceId,
        text: previewText,
        provider_config: config,
      });
      
      if (response.error) {
        throw new Error(response.error);
      }
      
      return response.data!;
    },
    onSuccess: (data, variables) => {
      // Update central audio player with preview
      setAudioData(
        data.audio_url,
        `${variables.characterName || 'Character'} Preview`,
        `Voice: ${data.voice_id}`,
        `preview_${variables.characterName}_${data.voice_id}.mp3`,
        true // autoplay
      );
    },
    onError: (error) => {
      setLoading(false);
      console.error('Failed to generate voice preview:', error);
      throw error;
    },
    onSettled: () => {
      setLoading(false);
    },
  });
}