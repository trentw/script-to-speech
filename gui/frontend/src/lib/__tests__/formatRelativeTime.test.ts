import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { formatRelativeTime } from '../formatRelativeTime';

const NOW = new Date('2026-07-06T12:00:00Z');

describe('formatRelativeTime', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(NOW);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('reports moments under a minute old as "just now"', () => {
    expect(formatRelativeTime('2026-07-06T11:59:30Z')).toBe('just now');
  });

  it('reports future timestamps as "just now" (clock skew)', () => {
    expect(formatRelativeTime('2026-07-06T12:05:00Z')).toBe('just now');
  });

  it('pluralizes minutes and hours correctly', () => {
    expect(formatRelativeTime('2026-07-06T11:59:00Z')).toBe('1 minute ago');
    expect(formatRelativeTime('2026-07-06T11:45:00Z')).toBe('15 minutes ago');
    expect(formatRelativeTime('2026-07-06T11:00:00Z')).toBe('1 hour ago');
    expect(formatRelativeTime('2026-07-06T05:00:00Z')).toBe('7 hours ago');
  });

  it('falls back to the locale date beyond a day', () => {
    expect(formatRelativeTime('2026-07-04T12:00:00Z')).toBe(
      new Date('2026-07-04T12:00:00Z').toLocaleDateString()
    );
  });

  it('degrades gracefully on unparsable input', () => {
    // NaN comparisons are all false -> the locale-date fallback, which
    // renders "Invalid Date" rather than throwing
    expect(formatRelativeTime('not-a-date')).toBe(
      new Date('not-a-date').toLocaleDateString()
    );
  });
});
