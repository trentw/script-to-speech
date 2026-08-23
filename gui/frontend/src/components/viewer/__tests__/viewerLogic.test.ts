import { describe, expect, it } from 'vitest';

import type { ChunkInventoryEntry } from '@/types/chunks';

import {
  buildPositionByIdx,
  buildViewerMetadata,
  computeAdvanceDelayMs,
  estimateRowSize,
  EXPECTED_SILENCE_MS,
  findNextPlayableIndex,
  getRowTextClasses,
  isPlayable,
  SEQUENTIAL_GAP_MS,
} from '../viewerLogic';

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

/** Build a list where each element's idx matches its array position. */
function makeEntries(
  ...statuses: ChunkInventoryEntry['status'][]
): ChunkInventoryEntry[] {
  return statuses.map((status, idx) => makeEntry({ idx, status }));
}

describe('isPlayable', () => {
  it('is true only for cached entries', () => {
    expect(isPlayable(makeEntry({ status: 'cached' }))).toBe(true);
    expect(isPlayable(makeEntry({ status: 'missing' }))).toBe(false);
    expect(isPlayable(makeEntry({ status: 'expected_silence' }))).toBe(false);
  });
});

describe('findNextPlayableIndex', () => {
  it('returns fromIndex itself when playable', () => {
    const entries = makeEntries('cached', 'cached');
    expect(findNextPlayableIndex(entries, 1)).toBe(1);
  });

  it('skips missing and expected-silence entries', () => {
    const entries = makeEntries(
      'missing',
      'expected_silence',
      'missing',
      'cached'
    );
    expect(findNextPlayableIndex(entries, 0)).toBe(3);
  });

  it('returns null when nothing playable remains', () => {
    const entries = makeEntries('cached', 'missing', 'expected_silence');
    expect(findNextPlayableIndex(entries, 1)).toBeNull();
  });

  it('returns null on an empty list', () => {
    expect(findNextPlayableIndex([], 0)).toBeNull();
  });

  it('clamps a negative fromIndex to the list start', () => {
    const entries = makeEntries('cached');
    expect(findNextPlayableIndex(entries, -5)).toBe(0);
  });
});

describe('computeAdvanceDelayMs', () => {
  it('is one gap between adjacent cached chunks', () => {
    const entries = makeEntries('cached', 'cached');
    expect(computeAdvanceDelayMs(entries, 0, 1)).toBe(SEQUENTIAL_GAP_MS);
  });

  it('is one gap across a missing chunk (missing chunks contribute nothing)', () => {
    const entries = makeEntries('cached', 'missing', 'cached');
    expect(computeAdvanceDelayMs(entries, 0, 2)).toBe(SEQUENTIAL_GAP_MS);
  });

  it('adds the silent-clip duration across one expected-silence chunk', () => {
    const entries = makeEntries('cached', 'expected_silence', 'cached');
    // gap after cached + 10 ms silence; the silence suppresses its own gap
    expect(computeAdvanceDelayMs(entries, 0, 2)).toBe(
      SEQUENTIAL_GAP_MS + EXPECTED_SILENCE_MS
    );
  });

  it('accumulates silent clips across consecutive expected-silence chunks', () => {
    const entries = makeEntries(
      'cached',
      'expected_silence',
      'expected_silence',
      'cached'
    );
    expect(computeAdvanceDelayMs(entries, 0, 3)).toBe(
      SEQUENTIAL_GAP_MS + 2 * EXPECTED_SILENCE_MS
    );
  });

  it('suppresses the final gap when the chunk before the target is expected silence', () => {
    // from an expected-silence chunk straight to the target: no gap at all
    const entries = makeEntries('expected_silence', 'cached');
    expect(computeAdvanceDelayMs(entries, 0, 1)).toBe(0);
  });
});

describe('getRowTextClasses', () => {
  it('styles each known chunk type distinctly', () => {
    expect(getRowTextClasses('title')).toContain('font-bold');
    expect(getRowTextClasses('scene_heading')).toContain('uppercase');
    expect(getRowTextClasses('speaker_attribution')).toContain('text-center');
    expect(getRowTextClasses('dialogue')).toContain('max-w-xl');
    expect(getRowTextClasses('dialogue_modifier')).toContain('italic');
  });

  it('falls back to action styling for unknown types', () => {
    expect(getRowTextClasses('some_custom_type')).toBe(
      getRowTextClasses('action')
    );
  });
});

describe('estimateRowSize', () => {
  it('grows with text length', () => {
    const short = estimateRowSize(makeEntry({ originalText: 'Hi.' }));
    const long = estimateRowSize(
      makeEntry({ originalText: 'A long paragraph. '.repeat(30) })
    );
    expect(long).toBeGreaterThan(short);
  });

  it('gives headings extra room', () => {
    const action = estimateRowSize(
      makeEntry({ chunkType: 'action', originalText: 'Same text.' })
    );
    const heading = estimateRowSize(
      makeEntry({ chunkType: 'scene_heading', originalText: 'Same text.' })
    );
    expect(heading).toBeGreaterThan(action);
  });
});

describe('buildViewerMetadata', () => {
  it('uses the original text and labels the chunk', () => {
    const metadata = buildViewerMetadata(
      makeEntry({ idx: 42, originalText: 'Hello there.' })
    );
    expect(metadata.primaryText).toBe('Hello there.');
    expect(metadata.secondaryText).toBe('JOHN · chunk #42');
  });
});

describe('buildPositionByIdx', () => {
  it('maps task idx to array position even when they diverge', () => {
    const entries = [
      makeEntry({ idx: 5 }),
      makeEntry({ idx: 9 }),
      makeEntry({ idx: 12 }),
    ];
    const map = buildPositionByIdx(entries);
    expect(map.get(5)).toBe(0);
    expect(map.get(9)).toBe(1);
    expect(map.get(12)).toBe(2);
    expect(map.get(7)).toBeUndefined();
  });
});
