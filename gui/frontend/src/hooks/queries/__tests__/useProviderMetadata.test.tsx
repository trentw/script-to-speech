import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import React from 'react';
import { vi } from 'vitest';

import { apiService } from '@/services/api';
import { FieldType } from '@/types';

import { useProviderMetadata } from '../useProviderMetadata';

// Mock the API service
vi.mock('@/services/api', () => ({
  apiService: {
    getProviderInfo: vi.fn(),
  },
}));

describe('useProviderMetadata', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });
    vi.clearAllMocks();
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  it('fetches provider metadata successfully', async () => {
    const mockProviderInfo = {
      identifier: 'openai',
      name: 'OpenAI',
      description: 'OpenAI TTS Provider',
      required_fields: [
        {
          name: 'voice',
          type: FieldType.STRING,
          required: true,
          description: 'OpenAI voice identifier',
          options: ['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'],
        },
      ],
      optional_fields: [],
      max_threads: 5,
    };

    vi.mocked(apiService.getProviderInfo).mockResolvedValueOnce({
      data: mockProviderInfo,
      error: null,
    });

    const { result } = renderHook(() => useProviderMetadata('openai'), {
      wrapper,
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockProviderInfo);
    expect(apiService.getProviderInfo).toHaveBeenCalledWith('openai');
  });

  it('handles error when fetching provider metadata', async () => {
    const errorMessage = 'Provider not found';
    vi.mocked(apiService.getProviderInfo).mockResolvedValueOnce({
      data: null,
      error: errorMessage,
    });

    const { result } = renderHook(
      () => useProviderMetadata('invalid-provider'),
      { wrapper }
    );

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error?.message).toBe(errorMessage);
  });

  it('does not fetch when provider is not provided', () => {
    const { result } = renderHook(() => useProviderMetadata(undefined), {
      wrapper,
    });

    expect(result.current.isSuccess).toBe(false);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.data).toBeUndefined();
    expect(apiService.getProviderInfo).not.toHaveBeenCalled();
  });

  it('refetches when provider changes', async () => {
    const mockProviderInfo1 = {
      identifier: 'openai',
      name: 'OpenAI',
      description: 'OpenAI TTS Provider',
      required_fields: [],
      optional_fields: [],
      max_threads: 5,
    };

    const mockProviderInfo2 = {
      identifier: 'elevenlabs',
      name: 'ElevenLabs',
      description: 'ElevenLabs TTS Provider',
      required_fields: [],
      optional_fields: [],
      max_threads: 3,
    };

    vi.mocked(apiService.getProviderInfo)
      .mockResolvedValueOnce({ data: mockProviderInfo1, error: null })
      .mockResolvedValueOnce({ data: mockProviderInfo2, error: null });

    const { result, rerender } = renderHook(
      ({ provider }) => useProviderMetadata(provider),
      {
        wrapper,
        initialProps: { provider: 'openai' },
      }
    );

    await waitFor(() => {
      expect(result.current.data?.identifier).toBe('openai');
    });

    // Change provider
    rerender({ provider: 'elevenlabs' });

    await waitFor(() => {
      expect(result.current.data?.identifier).toBe('elevenlabs');
    });

    expect(apiService.getProviderInfo).toHaveBeenCalledTimes(2);
    expect(apiService.getProviderInfo).toHaveBeenNthCalledWith(1, 'openai');
    expect(apiService.getProviderInfo).toHaveBeenNthCalledWith(2, 'elevenlabs');
  });
});
