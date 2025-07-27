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
