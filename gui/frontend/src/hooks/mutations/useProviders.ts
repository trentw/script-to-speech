import { useMutation, useQueryClient } from '@tanstack/react-query';

import { queryKeys } from '../../lib/queryKeys';
import { apiService } from '../../services/api';
import type { ValidationResult } from '../../types';

/**
 * Mutation hook for validating provider configuration
 * Provides immediate feedback on configuration validity
 */
export const useValidateProviderConfig = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      provider,
      config,
    }: {
      provider: string;
      config: Record<string, any>;
    }): Promise<ValidationResult> => {
      const response = await apiService.validateProviderConfig(
        provider,
        config
      );
      if (response.error) {
        throw new Error(response.error);
      }
      return response.data!;
    },
    onSuccess: (data, variables) => {
      // Optionally update provider info cache if validation affects it
      if (data.valid) {
        queryClient.invalidateQueries({
          queryKey: queryKeys.providerInfo(variables.provider),
        });
      }
    },
    onError: (error, variables) => {
      console.error(
        `Configuration validation failed for ${variables.provider}:`,
        error
      );
    },
  });
};

/**
 * Mutation hook for expanding STS ID to full configuration
 */
export const useExpandStsId = () => {
  return useMutation({
    mutationFn: async ({
      provider,
      stsId,
    }: {
      provider: string;
      stsId: string;
    }): Promise<Record<string, any>> => {
      const response = await apiService.expandStsId(provider, stsId);
      if (response.error) {
        throw new Error(response.error);
      }
      return response.data!;
    },
    onError: (error, variables) => {
      console.error(
        `STS ID expansion failed for ${variables.provider}:${variables.stsId}:`,
        error
      );
    },
  });
};
