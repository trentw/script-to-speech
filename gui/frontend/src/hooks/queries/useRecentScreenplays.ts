import { useQuery } from '@tanstack/react-query';

import { apiService } from '@/services/api';

export function useRecentScreenplays(limit = 10) {
  return useQuery({
    queryKey: ['recent-screenplays', limit],
    queryFn: async () => {
      const response = await apiService.getRecentScreenplays(limit);
      if (response.error) {
        throw new Error(response.error);
      }
      return response.data || [];
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  });
}
