import { useCallback, useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';

import {
  buildViewerMetadata,
  computeAdvanceDelayMs,
  findNextPlayableIndex,
  isPlayable,
} from '@/components/viewer/viewerLogic';
import { audioService } from '@/services/AudioService';
import type { ChunkInventoryEntry } from '@/types/chunks';

export type SequentialStatus = 'inactive' | 'loading' | 'playing' | 'gap';

interface SequentialState {
  status: SequentialStatus;
  /** Array index of the chunk currently being played/loaded, else null. */
  activeIndex: number | null;
}

export interface SequentialPlayback {
  activeIndex: number | null;
  status: SequentialStatus;
  isActive: boolean;
  /** Start (or restart) sequential playback at the first playable chunk >= index. */
  playFrom: (index: number) => void;
  /** Stop chaining and pause the current audio. */
  stop: () => void;
}

const INACTIVE: SequentialState = { status: 'inactive', activeIndex: null };

// Unique per hook instance; distinct chunks can share one cached audio file
// (same URL), so ownership of the shared player is tracked by token, not src
let sequenceCounter = 0;

/**
 * Sequential "play from here" playback over the chunk inventory, orchestrating
 * the app-wide AudioService singleton (the built-in player): one chunk plays
 * at a time through the shared player, and when it ends naturally the next
 * playable chunk is chained after a concatenator-faithful gap.
 *
 * Interactions with the shared player follow singleton semantics:
 * - Playing any other clip anywhere in the app (row play, side-panel variant,
 *   voice preview) cancels sequential mode and lets the new clip play.
 * - Pausing via the footer transport halts the chain in place; resuming
 *   continues it (no 'ended' event fires while paused).
 * - Unmounting stops the chaining but lets the current chunk finish.
 *
 * Note: a replay of the just-ended chunk started during the gap is overridden
 * by the pending advance when the gap timer fires (rare and benign - the gap
 * is 500 ms).
 */
export function useSequentialPlayback(options: {
  entries: ChunkInventoryEntry[];
  getAudioUrl: (entry: ChunkInventoryEntry) => string;
}): SequentialPlayback {
  const [state, setState] = useState<SequentialState>(INACTIVE);

  // Mirror of `state` for use inside stable subscriptions
  const stateRef = useRef<SequentialState>(INACTIVE);
  // Live entries/getAudioUrl so inventory refreshes mid-sequence are picked
  // up at the next advance without restarting playback
  const entriesRef = useRef(options.entries);
  const getAudioUrlRef = useRef(options.getAudioUrl);
  entriesRef.current = options.entries;
  getAudioUrlRef.current = options.getAudioUrl;

  const gapTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Loads not carrying this token are "foreign" (another component took over
  // the player). URL comparison can't do this job: chunks share cache files.
  const ownerTokenRef = useRef<string | null>(null);
  if (ownerTokenRef.current === null) {
    ownerTokenRef.current = `sequential-${++sequenceCounter}`;
  }
  // Monotonic id per advance so a stale loadAndPlay rejection (e.g. a load
  // timeout from an abandoned chunk) can't tear down a newer sequence
  const advanceSeqRef = useRef(0);
  // Detached, never-audible element that warms the next chunk's URL
  const preloadRef = useRef<HTMLAudioElement | null>(null);

  const setSeqState = useCallback((next: SequentialState) => {
    stateRef.current = next;
    setState(next);
  }, []);

  const clearGapTimer = useCallback(() => {
    if (gapTimerRef.current !== null) {
      clearTimeout(gapTimerRef.current);
      gapTimerRef.current = null;
    }
  }, []);

  // Abort the preload's in-flight download; without this the detached element
  // keeps fetching to completion (and stays pinned) after a Stop
  const releasePreload = useCallback(() => {
    const element = preloadRef.current;
    if (element) {
      element.removeAttribute('src');
      element.load();
      preloadRef.current = null;
    }
  }, []);

  const deactivate = useCallback(() => {
    clearGapTimer();
    releasePreload();
    setSeqState(INACTIVE);
  }, [clearGapTimer, releasePreload, setSeqState]);

  const warmNext = useCallback(
    (fromIndex: number) => {
      releasePreload();
      const entries = entriesRef.current;
      const next = findNextPlayableIndex(entries, fromIndex + 1);
      const nextEntry = next === null ? undefined : entries[next];
      if (!nextEntry) {
        return;
      }
      const element = new Audio();
      element.preload = 'auto';
      element.src = getAudioUrlRef.current(nextEntry);
      preloadRef.current = element;
    },
    [releasePreload]
  );

  const advanceTo = useCallback(
    (index: number) => {
      const entry = entriesRef.current[index];
      // The inventory may have refreshed since this advance was scheduled
      if (!entry || !isPlayable(entry)) {
        deactivate();
        return;
      }
      const url = getAudioUrlRef.current(entry);
      const advanceSeq = ++advanceSeqRef.current;
      setSeqState({ status: 'loading', activeIndex: index });
      void audioService
        .loadAndPlay(url, buildViewerMetadata(entry), ownerTokenRef.current!)
        .catch(() => {
          // The store watcher's 'error' branch usually handles the failure
          // (and toasts) before this rejection lands - only report here for
          // rejections that never reach the error state (e.g. load timeout),
          // and only if a newer advance hasn't superseded this one
          if (
            advanceSeqRef.current === advanceSeq &&
            stateRef.current.status !== 'inactive'
          ) {
            toast.error('Playback failed — sequential playback stopped');
            deactivate();
          }
        });
    },
    [deactivate, setSeqState]
  );

  // Chain to the next chunk when the current one ends naturally
  useEffect(() => {
    const unsubscribe = audioService.subscribeEnded(() => {
      const current = stateRef.current;
      if (current.status !== 'playing' && current.status !== 'loading') {
        return;
      }
      // Only chain on endings of clips this controller loaded
      const { ownerToken } = audioService.getState();
      if (
        ownerToken !== ownerTokenRef.current ||
        current.activeIndex === null
      ) {
        return;
      }

      const entries = entriesRef.current;
      const next = findNextPlayableIndex(entries, current.activeIndex + 1);
      if (next === null) {
        deactivate();
        toast('Reached the end of the screenplay');
        return;
      }

      const delay = computeAdvanceDelayMs(entries, current.activeIndex, next);
      setSeqState({ status: 'gap', activeIndex: current.activeIndex });
      gapTimerRef.current = setTimeout(() => {
        gapTimerRef.current = null;
        advanceTo(next);
      }, delay);
    });
    return unsubscribe;
  }, [advanceTo, deactivate, setSeqState]);

  // Watch the shared player: foreign clips cancel the sequence, errors stop
  // it, and the loading -> playing transition triggers preloading
  useEffect(() => {
    const unsubscribe = audioService.subscribe((audioState) => {
      const current = stateRef.current;
      if (current.status === 'inactive') {
        return;
      }

      if (audioState.src && audioState.ownerToken !== ownerTokenRef.current) {
        // Another component loaded a clip (possibly the same URL - chunks can
        // share cache files) - cede the player to it
        deactivate();
        return;
      }

      // Errors stop the chain even when they land during the 500 ms gap
      // window - the pending advance would otherwise play on past them
      if (audioState.playbackState === 'error') {
        deactivate();
        toast.error(audioState.error ?? 'Audio playback failed');
        return;
      }

      if (current.status === 'gap') {
        return;
      }

      if (
        audioState.playbackState === 'playing' &&
        current.status === 'loading'
      ) {
        setSeqState({ status: 'playing', activeIndex: current.activeIndex });
        if (current.activeIndex !== null) {
          warmNext(current.activeIndex);
        }
      }
    });
    return unsubscribe;
  }, [deactivate, setSeqState, warmNext]);

  // Unmount: stop chaining but let the current chunk finish (singleton
  // semantics - navigating away doesn't cut off the shared player)
  useEffect(() => {
    return () => {
      clearGapTimer();
      releasePreload();
    };
  }, [clearGapTimer, releasePreload]);

  const playFrom = useCallback(
    (index: number) => {
      const next = findNextPlayableIndex(entriesRef.current, index);
      if (next === null) {
        toast('No playable audio from here');
        return;
      }
      clearGapTimer();
      // No gap on user-initiated starts
      advanceTo(next);
    },
    [advanceTo, clearGapTimer]
  );

  const stop = useCallback(() => {
    const wasActive = stateRef.current.status !== 'inactive';
    deactivate();
    if (wasActive) {
      audioService.stopPlayback();
    }
  }, [deactivate]);

  return {
    activeIndex: state.activeIndex,
    status: state.status,
    isActive: state.status !== 'inactive',
    playFrom,
    stop,
  };
}
