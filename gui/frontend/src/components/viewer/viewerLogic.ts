/**
 * Pure logic for the Screenplay Viewer: sequential-playback timing that
 * mirrors the audiobook concatenator, per-chunk-type reading styles, and
 * virtualizer size estimates. No React in this module.
 */

import type { AudioMetadata } from '@/services/AudioService';
import type { ChunkInventoryEntry } from '@/types/chunks';

/**
 * Gap inserted between chunks during sequential playback. Mirrors the
 * audiobook concatenator's default gap (`gap_duration_ms` in
 * audio_generation/utils.py and `AudiobookGenerationRequest.gap_ms`) so
 * listening in the viewer matches the generated audiobook.
 */
export const SEQUENTIAL_GAP_MS = 500;

/**
 * Duration of the silent clip the pipeline generates for expected-silence
 * chunks (download_manager writes a 10 ms silent MP3). The concatenator also
 * suppresses the gap that would follow an expected-silence chunk.
 */
export const EXPECTED_SILENCE_MS = 10;

/** Only cached chunks have audio the viewer can play. */
export function isPlayable(entry: ChunkInventoryEntry): boolean {
  return entry.status === 'cached';
}

/**
 * Index of the first playable entry at or after `fromIndex`, or null when no
 * playable entry remains. Skips missing and expected-silence chunks.
 */
export function findNextPlayableIndex(
  entries: ChunkInventoryEntry[],
  fromIndex: number
): number | null {
  for (let i = Math.max(0, fromIndex); i < entries.length; i++) {
    const entry = entries[i];
    if (entry && isPlayable(entry)) {
      return i;
    }
  }
  return null;
}

/**
 * Delay between the end of entries[fromIndex] and the start of
 * entries[toIndex] during sequential playback, emulating the concatenator:
 * every chunk is followed by the 500 ms gap except expected-silence chunks
 * (which suppress their following gap and themselves contribute 10 ms);
 * missing chunks contribute nothing (they don't exist in a generated
 * audiobook).
 *
 * Adjacent cached chunks: 500. Across a missing chunk: 500. Across one
 * expected-silence chunk: 510. Across two: 520.
 */
export function computeAdvanceDelayMs(
  entries: ChunkInventoryEntry[],
  fromIndex: number,
  toIndex: number
): number {
  let delay = 0;
  let previous = entries[fromIndex];

  for (let i = fromIndex + 1; i < toIndex; i++) {
    const entry = entries[i];
    if (!entry || entry.status === 'missing') {
      continue;
    }
    delay +=
      (previous?.status === 'expected_silence' ? 0 : SEQUENTIAL_GAP_MS) +
      EXPECTED_SILENCE_MS;
    previous = entry;
  }

  delay += previous?.status === 'expected_silence' ? 0 : SEQUENTIAL_GAP_MS;
  return delay;
}

/**
 * Tailwind classes for a chunk's text in the reading view, keyed by chunk
 * type. Unknown/custom types fall back to action (full-width paragraph)
 * styling. The list container applies the shared reading font.
 */
export function getRowTextClasses(chunkType: string): string {
  switch (chunkType) {
    case 'title':
      return 'text-center text-2xl font-bold';
    case 'scene_heading':
      return 'font-semibold uppercase tracking-wide';
    case 'speaker_attribution':
      return 'mx-auto w-full max-w-xl text-center font-semibold uppercase';
    case 'dialogue':
      return 'mx-auto w-full max-w-xl leading-relaxed';
    case 'dialogue_modifier':
      return 'text-muted-foreground mx-auto w-full max-w-xl text-center italic';
    case 'action':
    default:
      return 'leading-relaxed';
  }
}

/** Approximate characters per line in the narrow (max-w-xl) reading column
 * used by dialogue, speaker attributions, and parentheticals. */
const ESTIMATE_CHARS_PER_LINE_NARROW = 65;
/** Approximate characters per line for full-width text (action, headings). */
const ESTIMATE_CHARS_PER_LINE_WIDE = 95;
/** Chunk types rendered in the narrow reading column (getRowTextClasses). */
const NARROW_COLUMN_TYPES = new Set([
  'speaker_attribution',
  'dialogue',
  'dialogue_modifier',
]);
/** Approximate rendered line height in px (16 px serif, relaxed leading). */
const ESTIMATE_LINE_HEIGHT_PX = 28;
/** Vertical padding + margins around a row's text, in px. */
const ESTIMATE_ROW_PADDING_PX = 24;
/** Extra height for scene headings/titles (divider + breathing room). */
const ESTIMATE_HEADING_EXTRA_PX = 32;

/**
 * Height estimate for the virtualizer. Rows self-measure after mount
 * (measureElement), so this only needs to be in the right ballpark to keep
 * scrollbar math stable — but the ballpark must respect the column width per
 * type, or dialogue-heavy screenplays get a jumpy scrollbar.
 */
export function estimateRowSize(entry: ChunkInventoryEntry): number {
  const charsPerLine = NARROW_COLUMN_TYPES.has(entry.chunkType)
    ? ESTIMATE_CHARS_PER_LINE_NARROW
    : ESTIMATE_CHARS_PER_LINE_WIDE;
  const lines = Math.max(
    1,
    Math.ceil(entry.originalText.length / charsPerLine)
  );
  const headingExtra =
    entry.chunkType === 'scene_heading' || entry.chunkType === 'title'
      ? ESTIMATE_HEADING_EXTRA_PX
      : 0;
  return (
    ESTIMATE_ROW_PADDING_PX + lines * ESTIMATE_LINE_HEIGHT_PX + headingExtra
  );
}

/**
 * Metadata for the app-wide audio player (footer transport) when playing a
 * chunk from the viewer.
 */
export function buildViewerMetadata(entry: ChunkInventoryEntry): AudioMetadata {
  return {
    primaryText: entry.originalText,
    secondaryText: `${entry.speakerDisplay} · chunk #${entry.idx}`,
    downloadFilename: entry.cacheFilename,
  };
}

/**
 * Position of each entry in the rendered list, keyed by task idx. The two
 * coincide for the full inventory (entries arrive in task order), but
 * anything addressing entries by task idx (occurrence chips, PDF anchors)
 * must resolve through this map so alternate/filtered lenses stay correct.
 */
export function buildPositionByIdx(
  entries: ChunkInventoryEntry[]
): Map<number, number> {
  const map = new Map<number, number>();
  entries.forEach((entry, position) => {
    map.set(entry.idx, position);
  });
  return map;
}
