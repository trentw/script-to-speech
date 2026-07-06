/**
 * Pure search/filter logic for the "Find Chunks" section, plus the mapping
 * from a chunk inventory entry to the ProblemClipInfo shape consumed by the
 * existing DialogueItem card.
 */

import type { ChunkInventoryEntry, ChunkSpeakerConfig } from '@/types/chunks';
import type { ProblemClipInfo } from '@/types/review';

/** Sentinel value for "no filter" in the speaker/chunk-type dropdowns */
export const ALL_FILTER = 'all';

/** Status filter options for the search section */
export type ChunkStatusFilter = 'all' | 'cached' | 'missing' | 'user-modified';

export interface ChunkSearchFilters {
  /** Case-insensitive substring match over originalText/processedText/speakerDisplay */
  query: string;
  /** Speaker display name, or ALL_FILTER */
  speaker: string;
  /** Chunk type, or ALL_FILTER */
  chunkType: string;
  /** Cache-status filter */
  status: ChunkStatusFilter;
}

/**
 * Whether the user has an "active query": non-empty trimmed search text or
 * any non-default filter. With no active query the section shows a hint
 * instead of results - an empty search box must not match the whole
 * screenplay (a selected speaker showing all of that speaker's chunks is
 * fine).
 */
export function hasActiveSearch(filters: ChunkSearchFilters): boolean {
  return (
    filters.query.trim() !== '' ||
    filters.speaker !== ALL_FILTER ||
    filters.chunkType !== ALL_FILTER ||
    filters.status !== 'all'
  );
}

/**
 * Collapse entries that share the same cache audio file into one entry per
 * unique cacheFilename (identical text+speaker chunks resolve to the same
 * file). Keeps the first entry for each file, preserving input order. Each
 * kept entry's `occurrences` already lists every chunk idx sharing the file.
 */
export function dedupeEntriesByCacheFilename(
  entries: ChunkInventoryEntry[]
): ChunkInventoryEntry[] {
  const seen = new Set<string>();
  const result: ChunkInventoryEntry[] = [];

  for (const entry of entries) {
    if (!seen.has(entry.cacheFilename)) {
      seen.add(entry.cacheFilename);
      result.push(entry);
    }
  }

  return result;
}

/**
 * Filter chunk inventory entries by search text, speaker, chunk type, and
 * status. The text query is a case-insensitive substring match over the
 * original text, processed text, and speaker display name.
 */
export function filterChunkEntries(
  entries: ChunkInventoryEntry[],
  filters: ChunkSearchFilters
): ChunkInventoryEntry[] {
  const query = filters.query.trim().toLowerCase();

  return entries.filter((entry) => {
    if (
      query &&
      !entry.originalText.toLowerCase().includes(query) &&
      !entry.processedText.toLowerCase().includes(query) &&
      !entry.speakerDisplay.toLowerCase().includes(query)
    ) {
      return false;
    }

    if (
      filters.speaker !== ALL_FILTER &&
      entry.speakerDisplay !== filters.speaker
    ) {
      return false;
    }

    if (
      filters.chunkType !== ALL_FILTER &&
      entry.chunkType !== filters.chunkType
    ) {
      return false;
    }

    switch (filters.status) {
      case 'cached':
        return entry.status === 'cached';
      case 'missing':
        return entry.status === 'missing';
      case 'user-modified':
        return entry.userModified !== null;
      case 'all':
        return true;
    }
  });
}

/** Unique speaker display names present in the inventory, sorted. */
export function getSpeakerOptions(entries: ChunkInventoryEntry[]): string[] {
  return Array.from(new Set(entries.map((e) => e.speakerDisplay))).sort(
    (a, b) => a.localeCompare(b)
  );
}

/** Unique chunk types present in the inventory, sorted. */
export function getChunkTypeOptions(entries: ChunkInventoryEntry[]): string[] {
  return Array.from(new Set(entries.map((e) => e.chunkType))).sort((a, b) =>
    a.localeCompare(b)
  );
}

/**
 * Build the ProblemClipInfo-shaped clip object DialogueItem expects from an
 * inventory entry and the shared per-speaker configs. The speaker config is
 * looked up with `entry.speaker ?? "default"`.
 */
export function buildProblemClip(
  entry: ChunkInventoryEntry,
  speakerConfigs: Record<string, ChunkSpeakerConfig>
): ProblemClipInfo {
  const config = speakerConfigs[entry.speaker ?? 'default'];

  return {
    cacheFilename: entry.cacheFilename,
    speaker: entry.speakerDisplay,
    voiceId: config?.voiceId ?? '',
    provider: config?.provider ?? '',
    text: entry.processedText,
    dbfsLevel: null,
    speakerConfig: config?.speakerConfig ?? {},
    stsId: config?.stsId ?? null,
  };
}
