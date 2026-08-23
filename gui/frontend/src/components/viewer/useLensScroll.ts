import type { RefObject } from 'react';
import { useCallback, useEffect, useRef } from 'react';

/**
 * Quiet window after a programmatic scroll during which scroll events are not
 * treated as user scrolling. Covers the corrective scroll frames virtualized
 * lists emit while dynamic row measurements settle.
 */
const PROGRAMMATIC_QUIET_MS = 250;

interface UseLensScrollOptions {
  scrollRef: RefObject<HTMLElement | null>;
  /** Topmost visible list position right now, or null when unknown. */
  getTopPosition: () => number | null;
  /** Fired on genuine user scrolling, with the topmost visible position. */
  onUserScroll: (topPosition: number | null) => void;
}

/**
 * Shared per-lens scroll plumbing: listens to the container's `scroll` event
 * (so scrollbar drags and keyboard scrolling count, not just wheel/touch) and
 * reports genuine user scrolls upward with the topmost visible position — the
 * shell's reading anchor. Lenses must call `markProgrammaticScroll()` around
 * every scroll they initiate themselves (follow, restore, jumps) so those
 * don't read as the user taking over.
 */
export function useLensScroll({
  scrollRef,
  getTopPosition,
  onUserScroll,
}: UseLensScrollOptions): { markProgrammaticScroll: () => void } {
  const quietUntilRef = useRef(0);
  // Live refs so the listener effect never needs to re-subscribe
  const getTopPositionRef = useRef(getTopPosition);
  const onUserScrollRef = useRef(onUserScroll);
  getTopPositionRef.current = getTopPosition;
  onUserScrollRef.current = onUserScroll;

  const markProgrammaticScroll = useCallback(() => {
    quietUntilRef.current = Date.now() + PROGRAMMATIC_QUIET_MS;
  }, []);

  useEffect(() => {
    const element = scrollRef.current;
    if (!element) return;
    const handleScroll = () => {
      if (Date.now() < quietUntilRef.current) return;
      onUserScrollRef.current(getTopPositionRef.current());
    };
    element.addEventListener('scroll', handleScroll, { passive: true });
    return () => {
      element.removeEventListener('scroll', handleScroll);
    };
  }, [scrollRef]);

  return { markProgrammaticScroll };
}
