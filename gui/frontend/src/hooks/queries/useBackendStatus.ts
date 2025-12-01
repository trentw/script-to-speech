import { useQuery } from '@tanstack/react-query';
import { useEffect, useState } from 'react';

import { isTauriEnvironment } from '../../config/api';
import { queryKeys } from '../../lib/queryKeys';
import { apiService } from '../../services/api';

/**
 * Query hook for checking backend connection status
 * In Tauri mode: shows "Connecting..." until first successful health check
 * In web mode: shows "Disconnected" immediately if backend not running
 */
export const useBackendStatus = () => {
  // Track if we've ever successfully connected
  // Web mode: start as true (show "Disconnected" immediately if not running)
  // Tauri mode: start as false (show "Connecting..." until first success)
  const [hasEverConnected, setHasEverConnected] =
    useState(!isTauriEnvironment());

  const query = useQuery({
    queryKey: queryKeys.backendStatus,
    queryFn: async (): Promise<{
      status: string;
      connected: boolean;
    }> => {
      const connected = await apiService.healthCheck();
      return {
        status: connected ? 'connected' : 'disconnected',
        connected,
      };
    },
    // CRITICAL: This query must run even when "offline" to detect backend readiness
    // Without this, onlineManager.setOnline(false) would pause this query too,
    // creating a chicken-and-egg problem where we can never detect the backend
    networkMode: 'always',
    refetchInterval: hasEverConnected ? 5000 : 1000, // Poll faster during startup
    refetchIntervalInBackground: true,
    staleTime: 0,
    gcTime: 1000 * 30,
    retry: (failureCount) => {
      return failureCount < 2;
    },
  });

  // Update hasEverConnected when we first connect
  useEffect(() => {
    if (query.data?.connected && !hasEverConnected) {
      setHasEverConnected(true);
    }
  }, [query.data?.connected, hasEverConnected]);

  // Add isStarting flag based on hasEverConnected
  const data = query.data
    ? {
        ...query.data,
        isStarting: !hasEverConnected,
      }
    : undefined;

  return {
    ...query,
    data,
  };
};
