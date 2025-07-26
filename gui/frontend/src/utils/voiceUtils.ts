import type { VoiceEntry } from '@/types';

/**
 * Get the display name for a voice
 * @param voice - The voice entry
 * @returns The provider name if available, otherwise the sts_id
 */
export function getVoiceDisplayName(voice: VoiceEntry): string {
  return voice.description?.provider_name || voice.sts_id;
}

/**
 * Get the subtext for a voice (gender, accent, age)
 * @param voice - The voice entry
 * @returns Bullet-separated string of voice properties, or custom description as fallback
 */
export function getVoiceSubtext(voice: VoiceEntry): string {
  const parts = [];
  if (voice.voice_properties?.gender) {
    parts.push(voice.voice_properties.gender);
  }
  if (voice.voice_properties?.accent) {
    parts.push(voice.voice_properties.accent);
  }
  if (voice.description?.perceived_age) {
    parts.push(voice.description.perceived_age);
  }
  return parts.length > 0
    ? parts.join(' • ')
    : voice.description?.custom_description || '';
}

/**
 * Play a voice preview using the central audio player
 * @param voice - The voice entry to preview
 * @param setAudioData - Function to set audio data in the central player
 * @param providerName - Name of the provider
 * @param characterName - Optional character name for context
 */
export function playVoicePreview(
  voice: VoiceEntry,
  setAudioData: (
    audioUrl: string,
    primaryText: string,
    secondaryText?: string,
    downloadFilename?: string,
    autoplay?: boolean
  ) => void,
  providerName: string,
  characterName?: string
): void {
  if (!voice?.preview_url) return;

  const voiceName = getVoiceDisplayName(voice);
  const primaryText = characterName
    ? `${characterName} • Voice preview: ${voiceName}`
    : `Voice preview: ${voiceName}`;
  const secondaryText = `${providerName} • ${voiceName}`;

  // Load the preview into the central audio player with autoplay
  setAudioData(
    voice.preview_url,
    primaryText,
    secondaryText,
    undefined, // no custom filename for previews
    true // autoplay
  );
}