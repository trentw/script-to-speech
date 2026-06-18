import { QueryClient } from '@tanstack/react-query';
import { act, renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it } from 'vitest';

import { BACKEND_URL } from '@/config';
import { server } from '@/test/setup';
import { createWrapper } from '@/test/utils/render';

import { useSilentClips } from '../useSilentClips';

const PROJECT = 'demo';
const base = `${BACKEND_URL}/api/review/silent-clips/${PROJECT}`;

// Backend uses CamelModel, so responses are camelCase (the client does not transform).
const emptyClips = {
  silentClips: [],
  totalClipsScanned: 0,
  cacheFolder: '',
  scannedAt: null,
};

const withClips = {
  silentClips: [
    {
      cacheFilename: 'a~~openai~~alloy.mp3',
      speaker: '(default)',
      voiceId: 'alloy',
      provider: 'openai',
      text: 'sighs',
      dbfsLevel: -51.8,
      speakerConfig: {},
      stsId: null,
    },
  ],
  totalClipsScanned: 5,
  cacheFolder: '/tmp/cache',
  scannedAt: '2026-06-17T00:00:00+00:00',
};

const idleProgress = {
  status: 'idle',
  progress: 0,
  totalClips: 0,
  completedClips: 0,
  source: null,
  error: null,
  scannedAt: null,
};

const runningProgress = {
  status: 'running',
  progress: 0.5,
  totalClips: 5,
  completedClips: 2,
  source: 'review',
  error: null,
  scannedAt: null,
};

const completedProgress = {
  status: 'completed',
  progress: 1,
  totalClips: 5,
  completedClips: 5,
  source: 'review',
  error: null,
  scannedAt: '2026-06-17T00:00:00+00:00',
};

describe('useSilentClips scan lifecycle', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    // Default handlers: empty clips, idle scan.
    server.use(
      http.get(base, () => HttpResponse.json(emptyClips)),
      http.get(`${base}/scan-progress`, () => HttpResponse.json(idleProgress))
    );
  });

  it('starts a scan, reports progress, and pops in results on completion', async () => {
    const { result } = renderHook(() => useSilentClips(PROJECT), {
      wrapper: createWrapper(queryClient),
    });

    // Initial cached read resolves to empty, not scanning.
    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(result.current.isScanning).toBe(false);
    expect(result.current.data?.silentClips).toHaveLength(0);

    // Arrange: POST returns running; scan-progress stays running for now.
    server.use(
      http.post(`${base}/scan`, () => HttpResponse.json(runningProgress)),
      http.get(`${base}/scan-progress`, () =>
        HttpResponse.json(runningProgress)
      )
    );

    // Act: trigger a refresh -> starts the scan.
    await act(async () => {
      await result.current.refresh();
    });

    // Progress is reflected immediately from the POST response.
    await waitFor(() => expect(result.current.isScanning).toBe(true));
    expect(result.current.scanProgress).toBeCloseTo(0.5);

    // Arrange: scan completes and the cache now has clips.
    server.use(
      http.get(`${base}/scan-progress`, () =>
        HttpResponse.json(completedProgress)
      ),
      http.get(base, () => HttpResponse.json(withClips))
    );

    // The poll observes completion -> refetches silent clips -> results pop in.
    await waitFor(
      () => {
        expect(result.current.isScanning).toBe(false);
        expect(result.current.data?.silentClips).toHaveLength(1);
      },
      { timeout: 4000 }
    );
  });

  it('surfaces an in-flight generation scan without starting one', async () => {
    // scan-progress already running (source generation) on mount.
    server.use(
      http.get(`${base}/scan-progress`, () =>
        HttpResponse.json({ ...runningProgress, source: 'generation' })
      )
    );

    const { result } = renderHook(() => useSilentClips(PROJECT), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.isScanning).toBe(true));
    expect(result.current.scanProgress).toBeCloseTo(0.5);
  });
});
