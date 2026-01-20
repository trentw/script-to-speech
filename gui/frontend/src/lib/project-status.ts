import type { ProjectStatus } from '@/types/project';

interface ProgressStatusInput {
  hasJson: boolean;
  hasVoiceConfig: boolean;
  speakerCount?: number;
  voicesAssigned?: number;
  hasOutputMp3?: boolean;
}

export interface ProgressStatus {
  label: string;
  badgeClassName: string;
  stage: 'not-started' | 'parsing' | 'casting' | 'generating' | 'complete';
}

/**
 * Check if voice casting is complete for a project
 */
export function isVoiceCastingComplete(
  status: ProjectStatus | null | undefined
): boolean {
  if (!status) return false;

  // Must have JSON (screenplay parsed) and voice config
  if (!status.hasJson || !status.hasVoiceConfig) return false;

  // All speakers must have voices assigned
  if (
    status.speakerCount !== undefined &&
    status.voicesAssigned !== undefined
  ) {
    return status.voicesAssigned >= status.speakerCount;
  }

  // Fallback to voicesCast flag
  return status.voicesCast;
}

/**
 * Get the progress status and badge styling for a project
 */
export function getProjectProgressStatus(
  input: ProgressStatusInput
): ProgressStatus {
  const { hasJson, hasVoiceConfig, speakerCount, voicesAssigned, hasOutputMp3 } =
    input;

  // Not started - no parsed screenplay
  if (!hasJson) {
    return {
      label: 'Not Started',
      badgeClassName: 'border-slate-300 bg-slate-100 text-slate-600',
      stage: 'not-started',
    };
  }

  // Screenplay parsed, checking voice casting
  if (!hasVoiceConfig) {
    return {
      label: 'Needs Voice Casting',
      badgeClassName: 'border-amber-300 bg-amber-100 text-amber-700',
      stage: 'casting',
    };
  }

  // Has voice config, check if all voices assigned
  if (speakerCount !== undefined && voicesAssigned !== undefined) {
    if (voicesAssigned < speakerCount) {
      return {
        label: `Casting (${voicesAssigned}/${speakerCount})`,
        badgeClassName: 'border-amber-300 bg-amber-100 text-amber-700',
        stage: 'casting',
      };
    }
  }

  // Check if audio generation is complete
  if (hasOutputMp3) {
    return {
      label: 'Generation Complete',
      badgeClassName: 'border-purple-300 bg-purple-100 text-purple-700',
      stage: 'complete',
    };
  }

  // All voices assigned, ready to generate
  return {
    label: 'Ready to Generate',
    badgeClassName: 'border-green-300 bg-green-100 text-green-700',
    stage: 'generating',
  };
}
