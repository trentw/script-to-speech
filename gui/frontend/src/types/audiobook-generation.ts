// Audiobook Generation Types

/**
 * Audio generation run modes matching CLI options.
 */
export type AudiobookGenerationMode = 'dry-run' | 'populate-cache' | 'full';

/**
 * Phases of the audio generation pipeline.
 */
export type AudiobookGenerationPhase =
  | 'pending'
  | 'planning'
  | 'applying_overrides'
  | 'checking_silence'
  | 'generating'
  | 'concatenating'
  | 'exporting'
  | 'finalizing'
  | 'completed'
  | 'failed';

/**
 * Statistics from the generation process.
 */
export interface AudiobookGenerationStats {
  totalClips: number;
  cachedClips: number;
  generatedClips: number;
  failedClips: number;
  skippedDuplicateClips: number;
  silentClips: number;
  rateLimitedClips: number;

  // Detailed status counts
  byStatus?: Record<string, number>;

  // Rate limit info
  rateLimitedProviders?: Array<{
    provider: string;
    backoffUntil?: string;
  }>;
}

/**
 * Request to start audiobook generation.
 */
export interface AudiobookGenerationRequest {
  projectName: string;
  inputJsonPath: string;
  voiceConfigPath: string;
  mode?: AudiobookGenerationMode;

  // Optional features
  silenceThreshold?: number | null; // dBFS, null to disable
  cacheOverridesDir?: string;
  textProcessorConfigs?: string[];

  // Generation settings
  gapMs?: number;
  maxWorkers?: number;
}

/**
 * Current progress of an audiobook generation task.
 */
export interface AudiobookGenerationProgress {
  taskId: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  phase: AudiobookGenerationPhase;
  phaseProgress: number; // 0.0-1.0 within current phase
  overallProgress: number; // 0.0-1.0 across all phases
  message: string;

  // Statistics (populated during/after GENERATING phase)
  stats?: AudiobookGenerationStats;

  // Timing
  createdAt?: string;
  startedAt?: string;
  completedAt?: string;

  // Error info
  error?: string;
}

/**
 * Final result of a completed audiobook generation.
 */
export interface AudiobookGenerationResult {
  outputFile?: string; // Path to final MP3 (if full mode)
  cacheFolder: string; // Path to cache folder
  logFile?: string; // Path to generation log

  // Final statistics
  stats: AudiobookGenerationStats;

  // Issues detected (for dry-run or review)
  cacheMisses: Array<{
    speaker: string;
    text: string;
  }>;
  silentClips: Array<{
    speaker: string;
    text: string;
  }>;
}

/**
 * Task creation response from the API.
 */
export interface AudiobookTaskResponse {
  taskId: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  message: string;
}

/**
 * Human-readable phase labels for UI display.
 */
export const PHASE_LABELS: Record<AudiobookGenerationPhase, string> = {
  pending: 'Waiting to start',
  planning: 'Planning generation',
  applying_overrides: 'Applying cache overrides',
  checking_silence: 'Checking for silence',
  generating: 'Generating audio',
  concatenating: 'Concatenating files',
  exporting: 'Exporting audiobook',
  finalizing: 'Finalizing audiobook',
  completed: 'Completed',
  failed: 'Failed',
};

/**
 * Mode descriptions for UI display.
 */
export const MODE_DESCRIPTIONS: Record<AudiobookGenerationMode, string> = {
  'dry-run':
    'Plan only - shows what would be generated without creating any files',
  'populate-cache':
    'Generate individual audio clips without creating final audiobook',
  full: 'Full generation - creates complete audiobook MP3 with ID3 tags',
};
