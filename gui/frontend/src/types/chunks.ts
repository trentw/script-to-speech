/**
 * Types for the chunk inventory ("Find Chunks") feature.
 *
 * These types correspond to the backend models in gui_backend/models.py
 * (ChunkInventoryEntry, ChunkSpeakerConfig, ChunkInventoryResponse) and
 * describe every post-preprocessed screenplay chunk with its audio-cache
 * state.
 */

/**
 * The kinds of user-initiated review-flow generations, matching the backend
 * enum validated by POST /api/generate:
 * - "retake": regenerating a chunk's exact processed text
 * - "edit": generating from modified text
 *
 * Adding a kind: extend this array (and the backend enum), then add its badge
 * labels to GENERATION_KIND_BADGES in components/review/generationKind.ts.
 */
export const GENERATION_KINDS = ['retake', 'edit'] as const;

export type GenerationKind = (typeof GENERATION_KINDS)[number];

/**
 * Per-speaker generation info, shared across chunk inventory entries.
 * Keyed by voice-config speaker key ("default" for unattributed chunks)
 * so the full config isn't repeated on every entry.
 * Corresponds to ChunkSpeakerConfig on the backend.
 */
export interface ChunkSpeakerConfig {
  /** TTS provider identifier (e.g., "openai", "elevenlabs") */
  provider: string;
  /** Cache filename component (for display only) */
  voiceId: string;
  /** Full speaker config for regeneration (contains provider, voice, speed, etc.) */
  speakerConfig: Record<string, unknown>;
  /**
   * Human-readable voice library identifier (e.g., "sarah").
   * Only available for voices defined in the voice library; null for custom voices.
   */
  stsId?: string | null;
}

/**
 * One post-preprocessed chunk with its audio-cache state.
 * Corresponds to ChunkInventoryEntry on the backend.
 */
export interface ChunkInventoryEntry {
  /** Position in the post-preprocessed chunk list */
  idx: number;
  /** Chunk type (e.g., "dialogue", "action", "scene_heading") */
  chunkType: string;
  /** Voice-config speaker key; null for the default speaker */
  speaker: string | null;
  /** Speaker display name (e.g., "JOHN" or "(default)") */
  speakerDisplay: string;
  /** Pre-text-processor text */
  originalText: string;
  /** Post-text-processor text (what is spoken) */
  processedText: string;
  /** Resolved on-disk cache name (expected plain name if missing) */
  cacheFilename: string;
  /** Audio-cache state of this chunk */
  status: 'cached' | 'missing' | 'expected_silence';
  /**
   * Set when the cached audio was user-committed from the review flow:
   * "edit" (modified text) or "retake" (regenerated original text);
   * null otherwise.
   */
  userModified: GenerationKind | null;
  /**
   * Idxs of all chunks sharing this audio file (including this one) --
   * identical text+speaker deduplicates to a single cached clip.
   */
  occurrences: number[];
}

/**
 * Full chunk inventory for a project.
 * Corresponds to ChunkInventoryResponse on the backend.
 */
export interface ChunkInventoryResponse {
  /** Project name */
  projectName: string;
  /** Every post-preprocessed chunk with its cache state */
  entries: ChunkInventoryEntry[];
  /** Per-speaker generation configs, keyed by speaker key ("default" included) */
  speakerConfigs: Record<string, ChunkSpeakerConfig>;
  /** Total number of chunks */
  totalChunks: number;
  /** Number of chunks with cached audio */
  cachedCount: number;
  /** Number of chunks with missing audio */
  missingCount: number;
  /** Number of chunks with user-modified (edit/retake) audio */
  userModifiedCount: number;
  /** Path to cache folder for audio serving */
  cacheFolder: string;
  /** ISO timestamp of when this inventory was computed */
  generatedAt: string;
}
