import type { CharacterInfo, VoiceAssignment } from '@/types/voice-casting';

export interface VoiceUsageInfo {
  character: string;
  lineCount: number;
}

/**
 * Calculate voice usage across all characters
 * @param assignments Map of character name to assignment info
 * @param characters Map of character name to character info
 * @param currentCharacter Optional current character to exclude from usage
 * @returns Map of sts_id to array of characters using that voice
 */
export function calculateVoiceUsage(
  assignments: Map<string, VoiceAssignment>,
  characters: Map<string, CharacterInfo> | undefined,
  currentCharacter?: string
): Map<string, VoiceUsageInfo[]> {
  const usage = new Map<string, VoiceUsageInfo[]>();

  assignments.forEach((assignment, character) => {
    // Skip if this is the current character or if there's no sts_id
    if (character === currentCharacter || !assignment.sts_id) return;

    // Get line count for this character
    const characterInfo = characters?.get(character);
    const lineCount = characterInfo?.lineCount || 0;

    // Add to usage map
    const existing = usage.get(assignment.sts_id) || [];
    existing.push({ character, lineCount });
    usage.set(assignment.sts_id, existing);
  });

  return usage;
}
