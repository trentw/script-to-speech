import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  EXPECTED_SILENCE_MS,
  SEQUENTIAL_GAP_MS,
} from '@/components/viewer/viewerLogic';
import type { ChunkInventoryEntry } from '@/types/chunks';

import { useSequentialPlayback } from '../useSequentialPlayback';

// Minimal fake of the AudioService singleton: the store contract (subscribe /
// subscribeEnded / getState) plus spied commands. The real service drags in
// HTMLAudioElement mocking and a 50 ms command debounce that only add noise
// here - the store contract is what the hook depends on.
const mockAudio = vi.hoisted(() => {
  interface FakeState {
    playbackState: string;
    src: string | null;
    error: string | null;
    endedCount: number;
    ownerToken: string | null;
  }

  const initial = (): FakeState => ({
    playbackState: 'idle',
    src: null,
    error: null,
    endedCount: 0,
    ownerToken: null,
  });

  let state = initial();
  const listeners = new Set<(s: FakeState) => void>();

  const setState = (partial: Partial<FakeState>) => {
    state = { ...state, ...partial };
    listeners.forEach((listener) => listener(state));
  };

  const service = {
    getState: () => state,
    subscribe: (listener: (s: FakeState) => void) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    subscribeEnded: (callback: () => void) => {
      let last = state.endedCount;
      const listener = (s: FakeState) => {
        if (s.endedCount !== last) {
          last = s.endedCount;
          callback();
        }
      };
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    loadAndPlay: vi.fn(
      (src: string, _metadata?: unknown, ownerToken?: string) => {
        setState({
          src,
          playbackState: 'loading',
          error: null,
          ownerToken: ownerToken ?? null,
        });
        return Promise.resolve();
      }
    ),
    stopPlayback: vi.fn(() => {
      if (state.playbackState === 'playing') {
        setState({ playbackState: 'paused' });
      }
    }),
  };

  return {
    service,
    setState,
    startPlaying: () => setState({ playbackState: 'playing' }),
    endPlayback: () =>
      setState({
        playbackState: 'idle',
        endedCount: state.endedCount + 1,
      }),
    reset: () => {
      state = initial();
      listeners.clear();
      service.loadAndPlay.mockClear();
      service.stopPlayback.mockClear();
    },
  };
});

vi.mock('@/services/AudioService', () => ({
  audioService: mockAudio.service,
}));

vi.mock('sonner', () => ({
  toast: Object.assign(vi.fn(), { error: vi.fn() }),
}));

function makeEntry(
  idx: number,
  status: ChunkInventoryEntry['status']
): ChunkInventoryEntry {
  return {
    idx,
    chunkType: 'dialogue',
    speaker: 'JOHN',
    speakerDisplay: 'JOHN',
    originalText: `Line ${idx}.`,
    processedText: `LINE ${idx}.`,
    cacheFilename: `clip-${idx}.mp3`,
    status,
    userModified: null,
    occurrences: [idx],
  };
}

function makeEntries(
  ...statuses: ChunkInventoryEntry['status'][]
): ChunkInventoryEntry[] {
  return statuses.map((status, idx) => makeEntry(idx, status));
}

const getAudioUrl = (entry: ChunkInventoryEntry) =>
  `http://127.0.0.1:8000/api/review/cache-audio/proj/${entry.cacheFilename}`;

function renderPlayback(entries: ChunkInventoryEntry[]) {
  return renderHook(
    ({ entries: currentEntries }) =>
      useSequentialPlayback({ entries: currentEntries, getAudioUrl }),
    { initialProps: { entries } }
  );
}

/** Start playback at `index` and simulate the clip reaching 'playing'. */
function startAt(
  result: { current: ReturnType<typeof useSequentialPlayback> },
  index: number
) {
  act(() => {
    result.current.playFrom(index);
  });
  act(() => {
    mockAudio.startPlaying();
  });
}

describe('useSequentialPlayback', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockAudio.reset();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it('starts at the first playable chunk at or after the requested index', () => {
    const { result } = renderPlayback(
      makeEntries('missing', 'expected_silence', 'cached')
    );

    act(() => {
      result.current.playFrom(0);
    });

    expect(mockAudio.service.loadAndPlay).toHaveBeenCalledTimes(1);
    expect(mockAudio.service.loadAndPlay).toHaveBeenCalledWith(
      getAudioUrl(makeEntry(2, 'cached')),
      expect.objectContaining({ secondaryText: 'JOHN · chunk #2' }),
      expect.stringMatching(/^sequential-/)
    );
    expect(result.current.status).toBe('loading');
    expect(result.current.activeIndex).toBe(2);
  });

  it('stays inactive with a notice when nothing is playable', () => {
    const { result } = renderPlayback(makeEntries('missing', 'missing'));

    act(() => {
      result.current.playFrom(0);
    });

    expect(mockAudio.service.loadAndPlay).not.toHaveBeenCalled();
    expect(result.current.isActive).toBe(false);
  });

  it('advances after the gap, not before', () => {
    const { result } = renderPlayback(makeEntries('cached', 'cached'));
    startAt(result, 0);
    expect(result.current.status).toBe('playing');

    act(() => {
      mockAudio.endPlayback();
    });
    expect(result.current.status).toBe('gap');
    expect(mockAudio.service.loadAndPlay).toHaveBeenCalledTimes(1);

    act(() => {
      vi.advanceTimersByTime(SEQUENTIAL_GAP_MS - 1);
    });
    expect(mockAudio.service.loadAndPlay).toHaveBeenCalledTimes(1);

    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(mockAudio.service.loadAndPlay).toHaveBeenCalledTimes(2);
    expect(mockAudio.service.loadAndPlay).toHaveBeenLastCalledWith(
      getAudioUrl(makeEntry(1, 'cached')),
      expect.anything(),
      expect.any(String)
    );
    expect(result.current.activeIndex).toBe(1);
  });

  it('skips missing chunks without extra delay', () => {
    const { result } = renderPlayback(
      makeEntries('cached', 'missing', 'cached')
    );
    startAt(result, 0);

    act(() => {
      mockAudio.endPlayback();
    });
    act(() => {
      vi.advanceTimersByTime(SEQUENTIAL_GAP_MS);
    });

    expect(mockAudio.service.loadAndPlay).toHaveBeenCalledTimes(2);
    expect(mockAudio.service.loadAndPlay).toHaveBeenLastCalledWith(
      getAudioUrl(makeEntry(2, 'cached')),
      expect.anything(),
      expect.any(String)
    );
  });

  it('adds the silent-clip duration when skipping expected-silence chunks', () => {
    const { result } = renderPlayback(
      makeEntries('cached', 'expected_silence', 'cached')
    );
    startAt(result, 0);

    act(() => {
      mockAudio.endPlayback();
    });
    act(() => {
      vi.advanceTimersByTime(SEQUENTIAL_GAP_MS + EXPECTED_SILENCE_MS - 1);
    });
    expect(mockAudio.service.loadAndPlay).toHaveBeenCalledTimes(1);

    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(mockAudio.service.loadAndPlay).toHaveBeenCalledTimes(2);
  });

  it('deactivates when another component takes over the player', () => {
    const { result } = renderPlayback(makeEntries('cached', 'cached'));
    startAt(result, 0);

    // A different clip (e.g. a voice preview) loads into the shared player
    // (foreign loads never carry this controller's owner token)
    act(() => {
      mockAudio.setState({
        src: 'http://127.0.0.1:8000/static/some-variant.mp3',
        playbackState: 'loading',
        ownerToken: null,
      });
    });

    expect(result.current.isActive).toBe(false);
    // The foreign clip keeps the player - we never pause it
    expect(mockAudio.service.stopPlayback).not.toHaveBeenCalled();
  });

  it('cancels a pending advance when a foreign clip starts during the gap', () => {
    const { result } = renderPlayback(makeEntries('cached', 'cached'));
    startAt(result, 0);

    act(() => {
      mockAudio.endPlayback();
    });
    expect(result.current.status).toBe('gap');

    act(() => {
      mockAudio.setState({
        src: 'http://127.0.0.1:8000/static/other.mp3',
        playbackState: 'loading',
        ownerToken: null,
      });
    });
    expect(result.current.isActive).toBe(false);

    act(() => {
      vi.advanceTimersByTime(SEQUENTIAL_GAP_MS * 2);
    });
    // Pending advance was cancelled - only the initial load happened
    expect(mockAudio.service.loadAndPlay).toHaveBeenCalledTimes(1);
  });

  it('stop() cancels pending playback and chaining', () => {
    const { result } = renderPlayback(makeEntries('cached', 'cached'));
    startAt(result, 0);

    act(() => {
      result.current.stop();
    });

    expect(result.current.isActive).toBe(false);
    expect(mockAudio.service.stopPlayback).toHaveBeenCalledTimes(1);

    act(() => {
      mockAudio.endPlayback();
      vi.advanceTimersByTime(SEQUENTIAL_GAP_MS * 2);
    });
    expect(mockAudio.service.loadAndPlay).toHaveBeenCalledTimes(1);
  });

  it('deactivates cleanly at the end of the list', () => {
    const { result } = renderPlayback(makeEntries('cached', 'missing'));
    startAt(result, 0);

    act(() => {
      mockAudio.endPlayback();
    });

    expect(result.current.isActive).toBe(false);
    expect(result.current.activeIndex).toBeNull();
    expect(mockAudio.service.loadAndPlay).toHaveBeenCalledTimes(1);
  });

  it('does not advance while paused, and resumes chaining after resume', () => {
    const { result } = renderPlayback(makeEntries('cached', 'cached'));
    startAt(result, 0);

    // Footer pause: no ended event fires, so nothing advances
    act(() => {
      mockAudio.setState({ playbackState: 'paused' });
    });
    act(() => {
      vi.advanceTimersByTime(SEQUENTIAL_GAP_MS * 4);
    });
    expect(result.current.status).toBe('playing');
    expect(mockAudio.service.loadAndPlay).toHaveBeenCalledTimes(1);

    // Resume, then the clip ends naturally - the chain continues
    act(() => {
      mockAudio.setState({ playbackState: 'playing' });
    });
    act(() => {
      mockAudio.endPlayback();
    });
    act(() => {
      vi.advanceTimersByTime(SEQUENTIAL_GAP_MS);
    });
    expect(mockAudio.service.loadAndPlay).toHaveBeenCalledTimes(2);
  });

  it('stops chaining on playback error', () => {
    const { result } = renderPlayback(makeEntries('cached', 'cached'));
    startAt(result, 0);

    act(() => {
      mockAudio.setState({ playbackState: 'error', error: 'boom' });
    });

    expect(result.current.isActive).toBe(false);
    act(() => {
      vi.advanceTimersByTime(SEQUENTIAL_GAP_MS * 2);
    });
    expect(mockAudio.service.loadAndPlay).toHaveBeenCalledTimes(1);
  });

  it('toasts exactly once when a load failure also reaches the error state', async () => {
    const { toast } = await import('sonner');
    const { result } = renderPlayback(makeEntries('cached', 'cached'));

    // Simulate loadAndPlay both transitioning to 'error' and rejecting
    mockAudio.service.loadAndPlay.mockImplementationOnce(
      (src: string, _metadata?: unknown, ownerToken?: string) => {
        mockAudio.setState({
          src,
          playbackState: 'loading',
          error: null,
          ownerToken: ownerToken ?? null,
        });
        mockAudio.setState({ playbackState: 'error', error: 'boom' });
        return Promise.reject(new Error('boom'));
      }
    );

    act(() => {
      result.current.playFrom(0);
    });
    // Let the rejection propagate
    await act(async () => {
      await Promise.resolve();
    });

    expect(result.current.isActive).toBe(false);
    expect(toast.error).toHaveBeenCalledTimes(1);
  });

  it('clears a pending advance on unmount', () => {
    const { result, unmount } = renderPlayback(makeEntries('cached', 'cached'));
    startAt(result, 0);

    act(() => {
      mockAudio.endPlayback();
    });
    unmount();

    act(() => {
      vi.advanceTimersByTime(SEQUENTIAL_GAP_MS * 2);
    });
    expect(mockAudio.service.loadAndPlay).toHaveBeenCalledTimes(1);
  });

  it('uses refreshed entries at the next advance', () => {
    const entries = makeEntries('cached', 'cached');
    const { result, rerender } = renderPlayback(entries);
    startAt(result, 0);

    act(() => {
      mockAudio.endPlayback();
    });

    // Inventory refresh flips the next chunk to missing before the gap ends
    rerender({
      entries: entries.map((entry, idx) =>
        idx === 1 ? { ...entry, status: 'missing' as const } : entry
      ),
    });
    act(() => {
      vi.advanceTimersByTime(SEQUENTIAL_GAP_MS);
    });

    // The stale advance target is no longer cached: deactivate, don't load
    expect(mockAudio.service.loadAndPlay).toHaveBeenCalledTimes(1);
    expect(result.current.isActive).toBe(false);
  });

  it('restarts from a new position while already active', () => {
    const { result } = renderPlayback(
      makeEntries('cached', 'cached', 'cached')
    );
    startAt(result, 0);

    act(() => {
      result.current.playFrom(2);
    });

    expect(mockAudio.service.loadAndPlay).toHaveBeenCalledTimes(2);
    expect(mockAudio.service.loadAndPlay).toHaveBeenLastCalledWith(
      getAudioUrl(makeEntry(2, 'cached')),
      expect.anything(),
      expect.any(String)
    );
    expect(result.current.activeIndex).toBe(2);
  });

  it('cedes the player when a foreign load reuses the same URL (shared cache file)', () => {
    const { result } = renderPlayback(makeEntries('cached', 'cached'));
    startAt(result, 0);

    // A row play button for a different chunk that shares this chunk's cache
    // file loads the exact same URL, without an owner token
    act(() => {
      mockAudio.setState({
        src: getAudioUrl(makeEntry(0, 'cached')),
        playbackState: 'loading',
        ownerToken: null,
      });
    });

    expect(result.current.isActive).toBe(false);
    act(() => {
      mockAudio.startPlaying();
      mockAudio.endPlayback();
      vi.advanceTimersByTime(SEQUENTIAL_GAP_MS * 2);
    });
    // The dead sequence must not chain off the foreign clip's ending
    expect(mockAudio.service.loadAndPlay).toHaveBeenCalledTimes(1);
  });

  it('ignores a stale loadAndPlay rejection after a newer playFrom', async () => {
    const { toast } = await import('sonner');
    const { result } = renderPlayback(makeEntries('cached', 'cached'));

    // First load hangs (e.g. a stalled file) and only rejects much later
    let rejectFirst: (error: Error) => void = () => {};
    mockAudio.service.loadAndPlay.mockImplementationOnce(
      (src: string, _metadata?: unknown, ownerToken?: string) => {
        mockAudio.setState({
          src,
          playbackState: 'loading',
          error: null,
          ownerToken: ownerToken ?? null,
        });
        return new Promise<void>((_resolve, reject) => {
          rejectFirst = reject;
        });
      }
    );

    act(() => {
      result.current.playFrom(0);
    });
    // The user starts over from another chunk while the first load is stuck
    act(() => {
      result.current.playFrom(1);
    });
    act(() => {
      mockAudio.startPlaying();
    });

    // The abandoned load's timeout rejection lands - the new sequence survives
    await act(async () => {
      rejectFirst(new Error('Timeout waiting for state: idle'));
      await Promise.resolve();
    });

    expect(result.current.isActive).toBe(true);
    expect(result.current.activeIndex).toBe(1);
    expect(toast.error).not.toHaveBeenCalled();
  });

  describe('preloading', () => {
    // The hook warms the next chunk with a detached Audio element; these
    // tests track every element it creates so its download lifecycle
    // (created -> aborted) is observable
    let createdAudios: InstanceType<typeof MockAudio>[];

    beforeEach(() => {
      createdAudios = [];
      const BaseAudio = globalThis.Audio as unknown as typeof MockAudio;
      class TrackingAudio extends BaseAudio {
        constructor() {
          super();
          createdAudios.push(this);
        }
      }
      vi.stubGlobal('Audio', TrackingAudio);
    });

    afterEach(() => {
      vi.unstubAllGlobals();
    });

    it('warms the next playable chunk once the current one starts playing', () => {
      const { result } = renderPlayback(
        makeEntries('cached', 'missing', 'cached')
      );
      act(() => {
        result.current.playFrom(0);
      });
      expect(createdAudios).toHaveLength(0);

      act(() => {
        mockAudio.startPlaying();
      });
      expect(createdAudios).toHaveLength(1);
      expect(createdAudios[0]!.src).toBe(getAudioUrl(makeEntry(2, 'cached')));
    });

    it('creates no preload when no playable chunk remains', () => {
      const { result } = renderPlayback(makeEntries('cached', 'missing'));
      startAt(result, 0);
      expect(createdAudios).toHaveLength(0);
    });

    it('aborts the preload download on stop()', () => {
      const { result } = renderPlayback(makeEntries('cached', 'cached'));
      startAt(result, 0);
      expect(createdAudios).toHaveLength(1);

      act(() => {
        result.current.stop();
      });
      expect(createdAudios[0]!.removeAttribute).toHaveBeenCalledWith('src');
      expect(createdAudios[0]!.load).toHaveBeenCalled();
    });

    it('aborts the preload download on unmount', () => {
      const { result, unmount } = renderPlayback(
        makeEntries('cached', 'cached')
      );
      startAt(result, 0);
      expect(createdAudios).toHaveLength(1);

      unmount();
      expect(createdAudios[0]!.removeAttribute).toHaveBeenCalledWith('src');
      expect(createdAudios[0]!.load).toHaveBeenCalled();
    });

    it('aborts the preload when a foreign clip takes over the player', () => {
      const { result } = renderPlayback(makeEntries('cached', 'cached'));
      startAt(result, 0);
      expect(createdAudios).toHaveLength(1);

      act(() => {
        mockAudio.setState({
          src: 'http://127.0.0.1:8000/api/other-clip.mp3',
          ownerToken: 'voice-preview',
        });
      });
      expect(result.current.isActive).toBe(false);
      expect(createdAudios[0]!.removeAttribute).toHaveBeenCalledWith('src');
    });

    it('replaces the previous preload as playback advances', () => {
      const { result } = renderPlayback(
        makeEntries('cached', 'cached', 'cached')
      );
      startAt(result, 0);
      expect(createdAudios).toHaveLength(1);

      act(() => {
        mockAudio.endPlayback();
      });
      act(() => {
        vi.advanceTimersByTime(SEQUENTIAL_GAP_MS);
      });
      act(() => {
        mockAudio.startPlaying();
      });

      expect(createdAudios).toHaveLength(2);
      expect(createdAudios[0]!.removeAttribute).toHaveBeenCalledWith('src');
      expect(createdAudios[1]!.src).toBe(getAudioUrl(makeEntry(2, 'cached')));
    });
  });
});
