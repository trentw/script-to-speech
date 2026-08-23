import { useMutation, useQueryClient } from '@tanstack/react-query';

import { queryKeys } from '../../lib/queryKeys';
import {
  type EntryPayload,
  textProcessorApi,
} from '../../services/textProcessorApi';
import type { TextProcessorConfig } from '../../types/text-processing';

/**
 * Mutation hooks for the per-project text processor config.
 *
 * Writes are optimistic-locked: the backend rejects saves with a stale
 * base_file_hash (HTTP 409 via TextProcessorApiError.status === 409), which
 * callers surface as a reload prompt.
 */

interface UpdateConfigParams {
  inputPath: string;
  entries: EntryPayload[];
  baseFileHash: string;
}

function projectNameFromInputPath(inputPath: string): string | null {
  const normalized = inputPath.replace(/[\\/]+$/, '');
  return normalized.split(/[\\/]/).pop() || null;
}

function invalidateViewerQueries(
  queryClient: ReturnType<typeof useQueryClient>,
  inputPath: string
) {
  const projectName = projectNameFromInputPath(inputPath);
  if (!projectName) return;
  queryClient.invalidateQueries({
    queryKey: queryKeys.chunkInventory(projectName),
  });
  queryClient.invalidateQueries({
    queryKey: queryKeys.pdfAnchors(projectName),
  });
}

export const useUpdateTextProcessorConfig = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      inputPath,
      entries,
      baseFileHash,
    }: UpdateConfigParams) => {
      return await textProcessorApi.updateConfig(
        inputPath,
        entries,
        baseFileHash
      );
    },
    onSuccess: (data: TextProcessorConfig, { inputPath }) => {
      queryClient.setQueryData(queryKeys.textProcessorConfig(inputPath), data);
      invalidateViewerQueries(queryClient, inputPath);
    },
    onError: (_error, { inputPath }) => {
      // On conflict/validation errors, refetch so the editor can reconcile
      queryClient.invalidateQueries({
        queryKey: queryKeys.textProcessorConfig(inputPath),
      });
    },
  });
};

export const useConvertTextProcessorConfig = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (inputPath: string) => {
      return await textProcessorApi.convertConfig(inputPath);
    },
    onSuccess: (data: TextProcessorConfig, inputPath) => {
      queryClient.setQueryData(queryKeys.textProcessorConfig(inputPath), data);
      invalidateViewerQueries(queryClient, inputPath);
    },
  });
};

interface ResetConfigParams {
  inputPath: string;
  source: 'shipped_default' | 'user_default';
}

export const useResetTextProcessorConfig = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ inputPath, source }: ResetConfigParams) => {
      return await textProcessorApi.resetConfig(inputPath, source);
    },
    onSuccess: (data: TextProcessorConfig, { inputPath }) => {
      queryClient.setQueryData(queryKeys.textProcessorConfig(inputPath), data);
      invalidateViewerQueries(queryClient, inputPath);
    },
  });
};

export const useValidateTextProcessorEntries = () => {
  return useMutation({
    mutationFn: async (entries: EntryPayload[]) => {
      return await textProcessorApi.validateEntries(entries);
    },
  });
};

interface PreviewParams {
  inputPath: string;
  entries: EntryPayload[] | null;
  includePreprocessorSnapshots?: boolean;
  maxChangedChunks?: number | null;
}

export const usePreviewTextProcessors = () => {
  return useMutation({
    mutationFn: async ({
      inputPath,
      entries,
      includePreprocessorSnapshots = false,
      maxChangedChunks = null,
    }: PreviewParams) => {
      return await textProcessorApi.previewConfig(
        inputPath,
        entries,
        includePreprocessorSnapshots,
        maxChangedChunks
      );
    },
  });
};

interface PreviewDiffParams {
  inputPath: string;
  draftEntries: EntryPayload[];
  /** null resolves the baseline from disk server-side */
  baselineEntries: EntryPayload[] | null;
  maxChangedChunks?: number;
}

export const usePreviewTextProcessorDiff = () => {
  return useMutation({
    mutationFn: async ({
      inputPath,
      draftEntries,
      baselineEntries,
      maxChangedChunks = 50,
    }: PreviewDiffParams) => {
      return await textProcessorApi.previewDiff(
        inputPath,
        draftEntries,
        baselineEntries,
        maxChangedChunks
      );
    },
  });
};
