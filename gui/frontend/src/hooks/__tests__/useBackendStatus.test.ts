import { act, renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { BACKEND_URL } from '@/config';
import { server } from '@/test/setup';

import { useBackendStatus } from '../useBackendStatus';

const API_BASE_URL = BACKEND_URL;

describe('useBackendStatus', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    vi.clearAllTimers();
    vi.useRealTimers();
  });

  describe('Initial Status Check', () => {
    it('should start with checking status', () => {
      // Arrange & Act
      const { result } = renderHook(() => useBackendStatus());

      // Assert
      expect(result.current.connectionStatus).toBe('checking');
    });

    it('should check health on mount and set connected status', async () => {
      // Arrange
      server.use(
        http.get(`${API_BASE_URL}/health`, () => {
          return new HttpResponse(null, { status: 200 });
        })
      );

      // Act
      const { result } = renderHook(() => useBackendStatus());

      // Assert
      await waitFor(() => {
        expect(result.current.connectionStatus).toBe('connected');
      });
    });

    it('should set disconnected status when health check fails', async () => {
      // Arrange
      server.use(
        http.get(`${API_BASE_URL}/health`, () => {
          return new HttpResponse(null, { status: 500 });
        })
      );

      // Act
      const { result } = renderHook(() => useBackendStatus());

      // Assert
      await waitFor(() => {
        expect(result.current.connectionStatus).toBe('disconnected');
      });
    });

    it('should handle network errors and set disconnected status', async () => {
      // Arrange
      server.use(
        http.get(`${API_BASE_URL}/health`, () => {
          return HttpResponse.error();
        })
      );

      // Act
      const { result } = renderHook(() => useBackendStatus());

      // Assert
      await waitFor(() => {
        expect(result.current.connectionStatus).toBe('disconnected');
      });
    });
  });

  describe('Periodic Checking', () => {
    it('should check backend status every 30 seconds', async () => {
      // Arrange
      let checkCount = 0;
      server.use(
        http.get(`${API_BASE_URL}/health`, () => {
          checkCount++;
          return new HttpResponse(null, { status: 200 });
        })
      );

      // Act
      renderHook(() => useBackendStatus());

      // Assert - initial check
      await waitFor(() => {
        expect(checkCount).toBe(1);
      });

      // Act - advance timer by 30 seconds
      act(() => {
        vi.advanceTimersByTime(30000);
      });

      // Assert - second check
      await waitFor(() => {
        expect(checkCount).toBe(2);
      });

      // Act - advance timer by another 30 seconds
      act(() => {
        vi.advanceTimersByTime(30000);
      });

      // Assert - third check
      await waitFor(() => {
        expect(checkCount).toBe(3);
      });
    });

    it('should update status from connected to disconnected', async () => {
      // Arrange
      let requestCount = 0;
      server.use(
        http.get(`${API_BASE_URL}/health`, () => {
          requestCount++;
          // First request succeeds, subsequent requests fail
          if (requestCount === 1) {
            return new HttpResponse(null, { status: 200 });
          }
          return new HttpResponse(null, { status: 500 });
        })
      );

      // Act
      const { result } = renderHook(() => useBackendStatus());

      // Assert - initially connected
      await waitFor(() => {
        expect(result.current.connectionStatus).toBe('connected');
      });

      // Act - trigger next check
      act(() => {
        vi.advanceTimersByTime(30000);
      });

      // Assert - now disconnected
      await waitFor(() => {
        expect(result.current.connectionStatus).toBe('disconnected');
      });
    });

    it('should clean up interval on unmount', async () => {
      // Arrange
      server.use(
        http.get(`${API_BASE_URL}/health`, () => {
          return new HttpResponse(null, { status: 200 });
        })
      );

      // Act
      const { result, unmount } = renderHook(() => useBackendStatus());

      // Wait for initial check to complete
      await waitFor(() => {
        expect(result.current.connectionStatus).toBe('connected');
      });

      // Spy on clearInterval after initial setup
      const clearIntervalSpy = vi.spyOn(global, 'clearInterval');

      // Act - unmount
      unmount();

      // Assert - should have called clearInterval at least once
      expect(clearIntervalSpy).toHaveBeenCalled();
    });
  });

  describe('Manual Check Function', () => {
    it('should allow manual status check', async () => {
      // Arrange
      let checkCount = 0;
      server.use(
        http.get(`${API_BASE_URL}/health`, () => {
          checkCount++;
          return new HttpResponse(null, { status: 200 });
        })
      );

      // Act
      const { result } = renderHook(() => useBackendStatus());

      // Wait for initial check
      await waitFor(() => {
        expect(checkCount).toBe(1);
      });

      // Act - manual check
      await act(async () => {
        await result.current.checkBackendStatus();
      });

      // Assert
      expect(checkCount).toBe(2);
      expect(result.current.connectionStatus).toBe('connected');
    });

    it('should handle errors in manual check gracefully', async () => {
      // Arrange
      server.use(
        http.get(`${API_BASE_URL}/health`, () => {
          return HttpResponse.error();
        })
      );

      // Act
      const { result } = renderHook(() => useBackendStatus());

      // Wait for initial check
      await waitFor(() => {
        expect(result.current.connectionStatus).toBe('disconnected');
      });

      // Act - manual check should not throw
      await act(async () => {
        await expect(
          result.current.checkBackendStatus()
        ).resolves.toBeUndefined();
      });

      // Assert - still disconnected
      expect(result.current.connectionStatus).toBe('disconnected');
    });
  });

  describe('State Recovery', () => {
    it('should recover from disconnected to connected state', async () => {
      // Arrange
      let requestCount = 0;
      server.use(
        http.get(`${API_BASE_URL}/health`, () => {
          requestCount++;
          // First 2 requests fail, then succeed
          if (requestCount <= 2) {
            return new HttpResponse(null, { status: 500 });
          }
          return new HttpResponse(null, { status: 200 });
        })
      );

      // Act
      const { result } = renderHook(() => useBackendStatus());

      // Assert - initially disconnected
      await waitFor(() => {
        expect(result.current.connectionStatus).toBe('disconnected');
      });

      // Act - advance time for retry
      act(() => {
        vi.advanceTimersByTime(30000);
      });

      // Still disconnected after second check
      await waitFor(() => {
        expect(requestCount).toBe(2);
      });
      expect(result.current.connectionStatus).toBe('disconnected');

      // Act - advance time for another retry
      act(() => {
        vi.advanceTimersByTime(30000);
      });

      // Assert - now connected
      await waitFor(() => {
        expect(result.current.connectionStatus).toBe('connected');
      });
    });
  });
});
