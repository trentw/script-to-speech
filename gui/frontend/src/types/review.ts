/**
 * Types for the Audio Review feature.
 *
 * These types correspond to the backend models in gui_backend/models.py
 * and are used for managing problem clips (silent clips and cache misses).
 */

/**
 * Information about a problem audio clip (silent or cache miss).
 * Corresponds to ProblemClipInfo on the backend.
 */
export interface ProblemClipInfo {
  /** Cache filename for reference (e.g., "abc123~~openai~~nova.mp3") */
  cacheFilename: string;
  /** Speaker display name (e.g., "NORMA" or "(default)") */
  speaker: string;
  /** Cache filename component (for display only) */
  voiceId: string;
  /** TTS provider identifier (e.g., "openai", "elevenlabs") */
  provider: string;
  /** Full dialogue text */
  text: string;
  /** For silent clips, the detected dBFS level */
  dbfsLevel: number | null;
  /** Full speaker config for regeneration (contains provider, voice, speed, etc.) */
  speakerConfig: Record<string, unknown>;
}

/**
 * Response containing cache misses for a project.
 * This is a fast operation (just checks file existence).
 */
export interface CacheMissesResponse {
  /** Audio clips that don't have cached files */
  cacheMisses: ProblemClipInfo[];
  /** True if cache misses were capped at the display limit */
  cacheMissesCapped: boolean;
  /** Total count of cache misses before capping */
  totalCacheMisses: number;
  /** Path to cache folder for audio serving */
  cacheFolder: string;
  /** ISO timestamp of when the scan was performed */
  scannedAt: string;
}

/**
 * Response containing silent clips for a project.
 * This is a slow operation (scans audio files for silence).
 */
export interface SilentClipsResponse {
  /** Audio clips detected as silent */
  silentClips: ProblemClipInfo[];
  /** Number of cached clips that were scanned */
  totalClipsScanned: number;
  /** Path to cache folder for audio serving */
  cacheFolder: string;
  /** ISO timestamp of when the scan was performed (null if never scanned) */
  scannedAt: string | null;
}

/**
 * Request to commit a variant to the project cache.
 * Corresponds to CommitVariantRequest on the backend.
 */
export interface CommitVariantRequest {
  /** Path to variant file in standalone_speech */
  sourcePath: string;
  /** Target filename in the cache folder */
  targetCacheFilename: string;
  /** Project name */
  projectName: string;
}

/**
 * Response from committing a variant.
 * Corresponds to CommitVariantResponse on the backend.
 */
export interface CommitVariantResponse {
  /** Whether the commit was successful */
  success: boolean;
  /** Path to the committed file */
  targetPath: string;
  /** Status message */
  message: string;
}

/**
 * Request to delete a variant file.
 * Corresponds to DeleteVariantRequest on the backend.
 */
export interface DeleteVariantRequest {
  /** Path to file in standalone_speech */
  filePath: string;
}

// ============================================================================
// Client-side state types (not sent to backend)
// ============================================================================

/**
 * Information about a generated variant audio file.
 * Used for tracking variants in the UI before committing.
 */
export interface VariantInfo {
  /** Unique ID for React key */
  id: string;
  /** HTTP URL for audio playback */
  audioUrl: string;
  /** Full filesystem path for commit/delete operations */
  filePath: string;
  /** Whether this variant has been committed to cache */
  committed: boolean;
}

/**
 * State for an edited dialogue line.
 * Used when user modifies text for pronunciation adjustments.
 */
export interface DialogueEditState {
  /** Original text from the clip */
  originalText: string;
  /** User-modified text */
  editedText: string;
  /** Variants generated from the edited text */
  variants: VariantInfo[];
}

/**
 * Clips grouped by speaker for display.
 */
export interface SpeakerGroup {
  /** Speaker display name (e.g., "NORMA") */
  speaker: string;
  /** Voice ID used for this speaker */
  voiceId: string;
  /** TTS provider for this speaker */
  provider: string;
  /** Clips belonging to this speaker */
  clips: ProblemClipInfo[];
}

/**
 * Represents an independent edit input instance for generating variants.
 * Allows multiple edit inputs per dialogue line, each with its own text,
 * task tracking, and generated variants.
 */
export interface EditInputInstance {
  /** Unique ID for React key and state management */
  id: string;
  /** User-modifiable text for this input */
  text: string;
  /** Number of variants to generate */
  variantCount: number;
  /** Current generation task ID (null when not generating) */
  currentTaskId: string | null;
  /** Whether we're waiting for variants after task creation */
  isAwaitingVariants: boolean;
  /** Timestamp when generation started (for timeout) */
  generationStartTime: number | null;
  /** Generated variants for this input */
  variants: VariantInfo[];
  /** Set of processed audio URLs (for streaming deduplication) */
  processedUrls: Set<string>;
}
