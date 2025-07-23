import { QueryClient } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it } from 'vitest';

import { server } from '@/test/setup';
import { createWrapper } from '@/test/utils/render';
import { TEST_PROVIDERS } from '@/test/utils/test-data';

import { useProviders } from '../queries/useProviders';

describe('useProviders Hook', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    // Create a new QueryClient for each test
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false, // Don't retry failed requests in tests
        },
      },
    });
  });

  describe('Successful Data Fetching', () => {
    it('should fetch providers data successfully', async () => {
      // Arrange - using default MSW handler which returns TEST_PROVIDERS

      // Act
      const { result } = renderHook(() => useProviders(), {
        wrapper: createWrapper(queryClient),
      });

      // Assert - initial state
      expect(result.current.isLoading).toBe(true);
      expect(result.current.data).toBeUndefined();
      expect(result.current.error).toBeNull();

      // Wait for the query to resolve
      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Assert - after successful fetch
      expect(result.current.data).toEqual(TEST_PROVIDERS);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it('should handle empty providers list', async () => {
      // Arrange
      const emptyProviders: any[] = [];

      server.use(
        http.get('http://127.0.0.1:8000/api/providers/info', () => {
          return HttpResponse.json(emptyProviders);
        })
      );

      // Act
      const { result } = renderHook(() => useProviders(), {
        wrapper: createWrapper(queryClient),
      });

      // Assert
      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(emptyProviders);
      expect(result.current.data).toHaveLength(0);
    });

    it('should cache providers data', async () => {
      // Arrange
      let fetchCount = 0;
      server.use(
        http.get('http://127.0.0.1:8000/api/providers/info', () => {
          fetchCount++;
          return HttpResponse.json(TEST_PROVIDERS);
        })
      );

      // Act - first render
      const { result: firstResult } = renderHook(() => useProviders(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(firstResult.current.isSuccess).toBe(true);
      });

      // Act - second render (should use cache)
      const { result: secondResult } = renderHook(() => useProviders(), {
        wrapper: createWrapper(queryClient),
      });

      // Assert
      expect(secondResult.current.isSuccess).toBe(true);
      expect(secondResult.current.data).toEqual(TEST_PROVIDERS);
      expect(fetchCount).toBe(1); // Should only fetch once
    });
  });

  describe('Error Handling', () => {
    it('should handle network errors', async () => {
      // Arrange
      server.use(
        http.get('http://127.0.0.1:8000/api/providers/info', () => {
          return HttpResponse.error();
        })
      );

      // Act
      const { result } = renderHook(() => useProviders(), {
        wrapper: createWrapper(queryClient),
      });

      // Assert
      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error).toBeDefined();
      expect(result.current.data).toBeUndefined();
      expect(result.current.isLoading).toBe(false);
    });

    it('should handle server errors', async () => {
      // Arrange
      server.use(
        http.get('http://127.0.0.1:8000/api/providers/info', () => {
          return new HttpResponse(null, { status: 500 });
        })
      );

      // Act
      const { result } = renderHook(() => useProviders(), {
        wrapper: createWrapper(queryClient),
      });

      // Assert
      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error).toBeDefined();
      expect(result.current.data).toBeUndefined();
    });
  });

  describe('Loading States', () => {
    it('should show loading state during fetch', async () => {
      // Arrange
      let resolvePromise: (value: unknown) => void;
      const promise = new Promise((resolve) => {
        resolvePromise = resolve;
      });

      server.use(
        http.get('http://127.0.0.1:8000/api/providers/info', async () => {
          await promise;
          return HttpResponse.json([]);
        })
      );

      // Act
      const { result } = renderHook(() => useProviders(), {
        wrapper: createWrapper(queryClient),
      });

      // Assert - should be loading
      expect(result.current.isLoading).toBe(true);
      expect(result.current.isFetching).toBe(true);
      expect(result.current.data).toBeUndefined();

      // Resolve the promise
      resolvePromise!(null);

      // Assert - should complete
      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });
      expect(result.current.isLoading).toBe(false);
      expect(result.current.isFetching).toBe(false);
    });
  });

  describe('Refetch Functionality', () => {
    it('should support manual refetch', async () => {
      // Arrange
      let fetchCount = 0;

      server.use(
        http.get('http://127.0.0.1:8000/api/providers/info', () => {
          fetchCount++;
          return HttpResponse.json(TEST_PROVIDERS);
        })
      );

      // Act
      const { result } = renderHook(() => useProviders(), {
        wrapper: createWrapper(queryClient),
      });

      // Wait for initial fetch
      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });
      expect(fetchCount).toBe(1);

      // Manually refetch
      await result.current.refetch();

      // Assert
      expect(fetchCount).toBe(2);
      expect(result.current.data).toEqual(TEST_PROVIDERS);
    });
  });
});
