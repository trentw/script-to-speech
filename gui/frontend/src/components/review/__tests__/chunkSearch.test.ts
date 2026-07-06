import { describe, expect, it } from 'vitest';

import type { ChunkInventoryEntry, ChunkSpeakerConfig } from '@/types/chunks';

import {
  ALL_FILTER,
  buildProblemClip,
  type ChunkSearchFilters,
  dedupeEntriesByCacheFilename,
  filterChunkEntries,
  getChunkTypeOptions,
  getSpeakerOptions,
  hasActiveSearch,
} from '../chunkSearch';

function makeEntry(
  overrides: Partial<ChunkInventoryEntry> = {}
): ChunkInventoryEntry {
  return {
    idx: 0,
    chunkType: 'dialogue',
    speaker: 'JOHN',
    speakerDisplay: 'JOHN',
    originalText: 'Hello world.',
    processedText: 'HELLO WORLD.',
    cacheFilename: 'abc~~def~~openai~~nova_tts-1.mp3',
    status: 'cached',
    userModified: null,
    occurrences: [0],
    ...overrides,
  };
}

const ENTRIES: ChunkInventoryEntry[] = [
  makeEntry({ idx: 0, originalText: 'Hello world.' }),
  makeEntry({
    idx: 1,
    speaker: null,
    speakerDisplay: '(default)',
    chunkType: 'action',
    originalText: 'John walks in.',
    processedText: 'John walks in.',
    status: 'missing',
  }),
  makeEntry({
    idx: 2,
    speaker: 'NORMA',
    speakerDisplay: 'NORMA',
    originalText: 'Goodbye now.',
    processedText: 'GOODBYE NOW.',
    userModified: 'edit',
  }),
  makeEntry({
    idx: 3,
    chunkType: 'dual_dialogue',
    originalText: 'Wait for me!',
    processedText: 'WAIT FOR ME!',
    status: 'expected_silence',
    userModified: 'retake',
  }),
];

const NO_FILTERS: ChunkSearchFilters = {
  query: '',
  speaker: ALL_FILTER,
  chunkType: ALL_FILTER,
  status: 'all',
};

describe('filterChunkEntries', () => {
  it('returns all entries when no filters are applied', () => {
    expect(filterChunkEntries(ENTRIES, NO_FILTERS)).toHaveLength(4);
  });

  it('matches query case-insensitively against originalText', () => {
    const result = filterChunkEntries(ENTRIES, {
      ...NO_FILTERS,
      query: 'hello',
    });
    expect(result.map((e) => e.idx)).toEqual([0]);
  });

  it('matches query against processedText', () => {
    const result = filterChunkEntries(ENTRIES, {
      ...NO_FILTERS,
      query: 'GOODBYE',
    });
    expect(result.map((e) => e.idx)).toEqual([2]);
  });

  it('matches query against speakerDisplay', () => {
    const result = filterChunkEntries(ENTRIES, {
      ...NO_FILTERS,
      query: 'norma',
    });
    expect(result.map((e) => e.idx)).toEqual([2]);
  });

  it('treats a whitespace-only query as no query', () => {
    expect(
      filterChunkEntries(ENTRIES, { ...NO_FILTERS, query: '   ' })
    ).toHaveLength(4);
  });

  it('filters by speaker display name', () => {
    const result = filterChunkEntries(ENTRIES, {
      ...NO_FILTERS,
      speaker: '(default)',
    });
    expect(result.map((e) => e.idx)).toEqual([1]);
  });

  it('filters by chunk type', () => {
    const result = filterChunkEntries(ENTRIES, {
      ...NO_FILTERS,
      chunkType: 'dual_dialogue',
    });
    expect(result.map((e) => e.idx)).toEqual([3]);
  });

  it('filters by cached status', () => {
    const result = filterChunkEntries(ENTRIES, {
      ...NO_FILTERS,
      status: 'cached',
    });
    expect(result.map((e) => e.idx)).toEqual([0, 2]);
  });

  it('filters by missing status', () => {
    const result = filterChunkEntries(ENTRIES, {
      ...NO_FILTERS,
      status: 'missing',
    });
    expect(result.map((e) => e.idx)).toEqual([1]);
  });

  it('filters user-modified entries regardless of edit/retake kind', () => {
    const result = filterChunkEntries(ENTRIES, {
      ...NO_FILTERS,
      status: 'user-modified',
    });
    expect(result.map((e) => e.idx)).toEqual([2, 3]);
  });

  it('combines query and filters (AND semantics)', () => {
    const result = filterChunkEntries(ENTRIES, {
      query: 'o',
      speaker: 'JOHN',
      chunkType: 'dialogue',
      status: 'cached',
    });
    expect(result.map((e) => e.idx)).toEqual([0]);
  });
});

describe('hasActiveSearch', () => {
  it('is inactive with no query and all-default filters', () => {
    expect(hasActiveSearch(NO_FILTERS)).toBe(false);
  });

  it('is inactive for a whitespace-only query', () => {
    expect(hasActiveSearch({ ...NO_FILTERS, query: '   ' })).toBe(false);
  });

  it('is active for non-empty trimmed search text', () => {
    expect(hasActiveSearch({ ...NO_FILTERS, query: 'hello' })).toBe(true);
    expect(hasActiveSearch({ ...NO_FILTERS, query: ' h ' })).toBe(true);
  });

  it('is active when a speaker is selected', () => {
    expect(hasActiveSearch({ ...NO_FILTERS, speaker: 'JOHN' })).toBe(true);
  });

  it('is active when a chunk type is selected', () => {
    expect(hasActiveSearch({ ...NO_FILTERS, chunkType: 'dialogue' })).toBe(
      true
    );
  });

  it('is active when a status is selected', () => {
    expect(hasActiveSearch({ ...NO_FILTERS, status: 'cached' })).toBe(true);
  });
});

describe('dedupeEntriesByCacheFilename', () => {
  it('collapses entries sharing a cache filename to the first occurrence', () => {
    const shared = 'shared~~openai~~nova_tts-1.mp3';
    const entries = [
      makeEntry({ idx: 0, cacheFilename: shared, occurrences: [0, 2, 5] }),
      makeEntry({ idx: 1, cacheFilename: 'unique-1.mp3', occurrences: [1] }),
      makeEntry({ idx: 2, cacheFilename: shared, occurrences: [0, 2, 5] }),
      makeEntry({ idx: 5, cacheFilename: shared, occurrences: [0, 2, 5] }),
    ];

    const result = dedupeEntriesByCacheFilename(entries);

    expect(result.map((e) => e.idx)).toEqual([0, 1]);
  });

  it('preserves input order of unique files', () => {
    const entries = [
      makeEntry({ idx: 3, cacheFilename: 'c.mp3' }),
      makeEntry({ idx: 1, cacheFilename: 'a.mp3' }),
      makeEntry({ idx: 2, cacheFilename: 'b.mp3' }),
    ];

    expect(dedupeEntriesByCacheFilename(entries).map((e) => e.idx)).toEqual([
      3, 1, 2,
    ]);
  });

  it('returns an empty array for no entries', () => {
    expect(dedupeEntriesByCacheFilename([])).toEqual([]);
  });

  it('keeps the occurrences list on the surviving entry', () => {
    const shared = 'shared.mp3';
    const entries = [
      makeEntry({ idx: 0, cacheFilename: shared, occurrences: [0, 4] }),
      makeEntry({ idx: 4, cacheFilename: shared, occurrences: [0, 4] }),
    ];

    const result = dedupeEntriesByCacheFilename(entries);

    expect(result).toHaveLength(1);
    expect(result[0].occurrences).toEqual([0, 4]);
  });
});

describe('getSpeakerOptions / getChunkTypeOptions', () => {
  it('returns unique sorted speaker display names', () => {
    expect(getSpeakerOptions(ENTRIES)).toEqual(['(default)', 'JOHN', 'NORMA']);
  });

  it('returns unique sorted chunk types', () => {
    expect(getChunkTypeOptions(ENTRIES)).toEqual([
      'action',
      'dialogue',
      'dual_dialogue',
    ]);
  });
});

describe('buildProblemClip', () => {
  const speakerConfigs: Record<string, ChunkSpeakerConfig> = {
    JOHN: {
      provider: 'openai',
      voiceId: 'nova_tts-1',
      speakerConfig: { provider: 'openai', voice: 'nova' },
      stsId: 'sarah',
    },
    default: {
      provider: 'elevenlabs',
      voiceId: 'onyx_tts-1',
      speakerConfig: {},
      stsId: null,
    },
  };

  it('builds a ProblemClipInfo from the entry and its speaker config', () => {
    const clip = buildProblemClip(ENTRIES[0], speakerConfigs);
    expect(clip).toEqual({
      cacheFilename: 'abc~~def~~openai~~nova_tts-1.mp3',
      speaker: 'JOHN',
      voiceId: 'nova_tts-1',
      provider: 'openai',
      text: 'HELLO WORLD.',
      dbfsLevel: null,
      speakerConfig: { provider: 'openai', voice: 'nova' },
      stsId: 'sarah',
    });
  });

  it('uses the "default" config when the entry speaker is null', () => {
    const clip = buildProblemClip(ENTRIES[1], speakerConfigs);
    expect(clip.speaker).toBe('(default)');
    expect(clip.provider).toBe('elevenlabs');
    expect(clip.voiceId).toBe('onyx_tts-1');
    expect(clip.speakerConfig).toEqual({});
    expect(clip.stsId).toBeNull();
  });

  it('uses the processed text (what is spoken) as the clip text', () => {
    const clip = buildProblemClip(ENTRIES[2], speakerConfigs);
    expect(clip.text).toBe('GOODBYE NOW.');
  });
});
