import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import { ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { projectApi } from '../../../services/projectApi';
import { useProjectStatus } from '../useProjectStatus';

// Mock the project API service
vi.mock('../../../services/projectApi', () => ({
  projectApi: {
    getProjectStatus: vi.fn(),
  },
}));

const mockProjectApi = projectApi as {
  getProjectStatus: ReturnType<typeof vi.fn>;
};

describe('useProjectStatus', () => {
  let queryClient: QueryClient;
  let wrapper: ({ children }: { children: ReactNode }) => JSX.Element;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    });
    wrapper = ({ children }: { children: ReactNode }) => {
      return (
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      );
    };
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should return undefined when inputPath is undefined', async () => {
    const { result } = renderHook(() => useProjectStatus(undefined), {
      wrapper,
    });

    expect(result.current.status).toBeUndefined();
    expect(result.current.isLoading).toBe(false);
    expect(mockProjectApi.getProjectStatus).not.toHaveBeenCalled();
  });

  it('should fetch project status when inputPath is provided', async () => {
    const mockStatus = {
      hasPdf: true,
      hasJson: true,
      hasVoiceConfig: false,
      hasOptionalConfig: false,
      hasOutputMp3: false,
      screenplayParsed: true,
      voicesCast: false,
      audioGenerated: false,
      speakerCount: 5,
      dialogueChunks: 234,
    };

    mockProjectApi.getProjectStatus.mockResolvedValue(mockStatus);

    const { result } = renderHook(() => useProjectStatus('/test/input/path'), {
      wrapper,
    });

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.status).toEqual(mockStatus);
    expect(mockProjectApi.getProjectStatus).toHaveBeenCalledWith(
      '/test/input/path'
    );
  });

  it('should handle API errors gracefully', async () => {
    mockProjectApi.getProjectStatus.mockRejectedValue(
      new Error('Project not found')
    );

    const { result } = renderHook(() => useProjectStatus('/test/input/path'), {
      wrapper,
    });

    await waitFor(() => {
      expect(result.current.error).toBeTruthy();
    });

    expect(result.current.status).toBeUndefined();
    expect(result.current.error?.message).toBe('Project not found');
  });

  it('should provide invalidate function for cache refresh', async () => {
    const mockStatus = {
      hasPdf: true,
      hasJson: true,
      hasVoiceConfig: false,
      hasOptionalConfig: false,
      hasOutputMp3: false,
      screenplayParsed: true,
      voicesCast: false,
      audioGenerated: false,
    };

    mockProjectApi.getProjectStatus.mockResolvedValue(mockStatus);

    const { result } = renderHook(() => useProjectStatus('/test/input/path'), {
      wrapper,
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(typeof result.current.invalidate).toBe('function');

    // Test that invalidate can be called without errors
    await result.current.invalidate();
  });
});
