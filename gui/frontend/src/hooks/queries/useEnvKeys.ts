import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { API_BASE_URL } from '@/config/api';
import { queryKeys } from '@/lib/queryKeys';

interface EnvKeysResponse {
  ok: boolean;
  data?: {
    keys: Record<string, string | boolean>;
    env_path: string;
  };
  error?: string;
}

interface ApiKeyValidationResponse {
  ok: boolean;
  data?: {
    keys: Record<string, boolean>;
  };
  error?: string;
}

interface EnvKeyUpdate {
  key: string;
  value: string;
}

interface UpdateEnvKeyResponse {
  ok: boolean;
  data?: {
    key: string;
    updated: boolean;
  };
  error?: string;
  details?: Record<string, unknown>;
}

/**
 * Query hook for fetching masked API keys from .env file
 * Returns masked values (last 4 chars) for security
 */
export const useEnvKeys = () => {
  return useQuery({
    queryKey: queryKeys.envKeys,
    queryFn: async (): Promise<
      Record<string, string | boolean> & { _envPath?: string }
    > => {
      const response = await fetch(`${API_BASE_URL}/settings/env`);

      if (!response.ok) {
        throw new Error(`Failed to fetch env keys: ${response.statusText}`);
      }

      const result: EnvKeysResponse = await response.json();

      if (!result.ok || !result.data) {
        throw new Error(result.error || 'Failed to fetch env keys');
      }

      // Include env_path as metadata
      return {
        ...result.data.keys,
        _envPath: result.data.env_path,
      };
    },
    staleTime: 1000 * 60 * 5, // 5 minutes - env keys don't change often
    refetchOnMount: true,
  });
};

/**
 * Query hook for validating which API keys are currently configured
 * Checks the process environment for key existence
 */
export const useValidateApiKeys = () => {
  return useQuery({
    queryKey: queryKeys.apiKeyValidation,
    queryFn: async (): Promise<Record<string, boolean>> => {
      const response = await fetch(`${API_BASE_URL}/settings/env/validate`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error(`Failed to validate API keys: ${response.statusText}`);
      }

      const result: ApiKeyValidationResponse = await response.json();

      if (!result.ok || !result.data) {
        throw new Error(result.error || 'Failed to validate API keys');
      }

      return result.data.keys;
    },
    staleTime: Infinity, // Never auto-refetch - only invalidate on save
    refetchOnMount: false,
    refetchOnWindowFocus: false,
  });
};

/**
 * Mutation hook for updating a single API key in .env file
 * Invalidates both env keys and validation queries on success
 */
export const useUpdateEnvKey = () => {
  const queryClient = useQueryClient();

  return useMutation<UpdateEnvKeyResponse, Error, EnvKeyUpdate>({
    mutationFn: async (update: EnvKeyUpdate) => {
      const response = await fetch(`${API_BASE_URL}/settings/env`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(update),
      });

      const result: UpdateEnvKeyResponse = await response.json();

      if (!response.ok || !result.ok) {
        throw new Error(
          result.error ||
            `Failed to update ${update.key}: ${response.statusText}`
        );
      }

      return result;
    },
    onSuccess: () => {
      // Invalidate env keys query to show updated masked value
      queryClient.invalidateQueries({ queryKey: queryKeys.envKeys });

      // Invalidate validation query to reflect new API key status
      queryClient.invalidateQueries({ queryKey: queryKeys.apiKeyValidation });

      // Also invalidate providers since API keys affect provider availability
      queryClient.invalidateQueries({ queryKey: queryKeys.providersInfo });
    },
  });
};
