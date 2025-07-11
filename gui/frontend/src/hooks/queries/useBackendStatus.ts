import { useQuery } from '@tanstack/react-query'
import { apiService } from '../../services/api'
import { queryKeys } from '../../lib/queryKeys'

/**
 * Query hook for checking backend connection status
 * Polls regularly to ensure backend availability
 */
export const useBackendStatus = () => {
  return useQuery({
    queryKey: queryKeys.backendStatus,
    queryFn: async (): Promise<{ status: string; connected: boolean }> => {
      const connected = await apiService.healthCheck()
      return {
        status: connected ? 'connected' : 'disconnected',
        connected,
      }
    },
    refetchInterval: 5000, // Poll every 5 seconds
    refetchIntervalInBackground: true, // Keep polling in background
    staleTime: 0, // Always consider stale to enable regular checks
    gcTime: 1000 * 30, // Short cache time for status
    retry: (failureCount) => {
      // Don't retry health checks too aggressively
      return failureCount < 2
    },
  })
}