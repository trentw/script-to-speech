import { useMutation } from '@tanstack/react-query';

import { apiService } from '../../services/api';
import type { DetectHeadersParams, DetectionResult } from '../../types';

/**
 * Mutation hook for detecting headers and footers in a PDF screenplay
 *
 * Features:
 * - Runs header/footer detection with configurable thresholds
 * - Returns patterns classified as auto-apply (>=40%) or suggestions (20-40%)
 * - Adjusts min_occurrences for short scripts automatically
 */
export const useDetectHeaders = () => {
  return useMutation({
    mutationFn: async (
      params: DetectHeadersParams
    ): Promise<DetectionResult> => {
      const response = await apiService.detectHeaders(params);

      if (response.error) {
        throw new Error(response.error);
      }

      if (!response.data) {
        throw new Error('No detection result returned');
      }

      return response.data;
    },

    onError: (error) => {
      console.error('Header/footer detection failed:', error);
    },
  });
};
