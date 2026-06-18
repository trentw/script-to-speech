import { describe, expect, it, vi } from 'vitest';

import { render, screen } from '@/test/utils/render';
import type { ProblemClipInfo } from '@/types/review';

import { ProblemClipsSection } from '../ProblemClipsSection';

// Stub the speaker group (renders audio players / network) so we can focus on
// the section's scan-progress UI.
vi.mock('../SpeakerGroup', () => ({
  SpeakerGroupComponent: () => <div data-testid="speaker-group" />,
}));

const clip: ProblemClipInfo = {
  cacheFilename: 'a~~openai~~alloy.mp3',
  speaker: '(default)',
  voiceId: 'alloy',
  provider: 'openai',
  text: 'sighs',
  dbfsLevel: -51.8,
  speakerConfig: {},
  stsId: null,
};

function baseProps() {
  return {
    title: 'Silent Clips',
    description: 'Audio clips detected as silent.',
    clips: [],
    projectName: 'demo',
    cacheFolder: '/tmp/cache',
    onRefresh: vi.fn(),
  };
}

describe('ProblemClipsSection scan progress', () => {
  it('shows a progress bar + percentage in the body when scanning with no clips', () => {
    render(
      <ProblemClipsSection
        {...baseProps()}
        isScanning
        scanProgress={0.4}
        hasScanned={false}
      />
    );

    expect(screen.getByText(/Scanning for silent clips/i)).toBeInTheDocument();
    // Percentage appears in both the body block and under the Refresh button
    expect(screen.getAllByText(/40%/).length).toBeGreaterThan(0);
    // Radix Progress exposes a progressbar role
    expect(screen.getAllByRole('progressbar').length).toBeGreaterThan(0);
  });

  it('shows progress under the Refresh button when scanning with existing clips', () => {
    render(
      <ProblemClipsSection
        {...baseProps()}
        clips={[clip]}
        isScanning
        scanProgress={0.6}
        scannedAt="2026-06-17T00:00:00+00:00"
      />
    );

    // Existing clips still render
    expect(screen.getByTestId('speaker-group')).toBeInTheDocument();
    // Progress shown near the button...
    expect(screen.getByText(/Scanning… 60%/)).toBeInTheDocument();
    // ...and the "Last refreshed" line is replaced while scanning
    expect(screen.queryByText(/Last refreshed/i)).not.toBeInTheDocument();
  });

  it('shows "Finishing…" once progress reaches 100% but scan still running', () => {
    render(
      <ProblemClipsSection {...baseProps()} isScanning scanProgress={1} />
    );
    expect(screen.getAllByText(/Finishing/).length).toBeGreaterThan(0);
  });

  it('shows last-refreshed timestamp and no progress bar when not scanning', () => {
    render(
      <ProblemClipsSection
        {...baseProps()}
        clips={[clip]}
        scannedAt="2026-06-17T00:00:00+00:00"
      />
    );
    expect(screen.getByText(/Last refreshed/i)).toBeInTheDocument();
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
  });
});
