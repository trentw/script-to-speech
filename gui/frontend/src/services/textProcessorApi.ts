/**
 * API service for text processor configuration endpoints
 */

import { API_BASE_URL } from '../config/api';
import type {
  TextProcessorConfig,
  TextProcessorEntry,
  TextProcessorGlobalDefault,
  TextProcessorPreview,
  TextProcessorPreviewDiff,
  TextProcessorRegistry,
  ValidationResult,
} from '../types/text-processing';

interface ApiResponse<T = unknown> {
  ok: boolean;
  data?: T;
  error?: string;
  details?: Record<string, unknown>;
}

/** Error carrying the HTTP status so callers can branch on 409 conflicts */
export class TextProcessorApiError extends Error {
  status: number;
  details?: Record<string, unknown> | undefined;

  constructor(
    message: string,
    status: number,
    details?: Record<string, unknown>
  ) {
    super(message);
    this.name = 'TextProcessorApiError';
    this.status = status;
    this.details = details;
  }
}

/** Strip client-only fields before sending entries to the backend */
export type EntryPayload = Pick<
  TextProcessorEntry,
  'kind' | 'name' | 'known' | 'config' | 'config_yaml'
>;

class TextProcessorApiService {
  private baseUrl = API_BASE_URL;

  private async parse<T>(response: Response): Promise<T> {
    if (response.status === 409) {
      const body = await response.json().catch(() => null);
      throw new TextProcessorApiError(
        (body?.detail as string) ||
          'The config file was modified by another source',
        409
      );
    }

    const result: ApiResponse<T> = await response.json();
    if (!result.ok) {
      throw new TextProcessorApiError(
        result.error || 'Text processor request failed',
        response.status,
        result.details
      );
    }
    if (result.data === undefined) {
      throw new TextProcessorApiError('No data returned', response.status);
    }
    return result.data;
  }

  async getRegistry(): Promise<TextProcessorRegistry> {
    const response = await fetch(`${this.baseUrl}/text-processors/registry`);
    return this.parse<TextProcessorRegistry>(response);
  }

  async validateEntries(entries: EntryPayload[]): Promise<ValidationResult> {
    const response = await fetch(`${this.baseUrl}/text-processors/validate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ entries }),
    });
    return this.parse<ValidationResult>(response);
  }

  async getConfig(inputPath: string): Promise<TextProcessorConfig> {
    const response = await fetch(
      `${this.baseUrl}/project/text-processor-config?input_path=${encodeURIComponent(inputPath)}`
    );
    return this.parse<TextProcessorConfig>(response);
  }

  async updateConfig(
    inputPath: string,
    entries: EntryPayload[],
    baseFileHash: string
  ): Promise<TextProcessorConfig> {
    const response = await fetch(
      `${this.baseUrl}/project/text-processor-config?input_path=${encodeURIComponent(inputPath)}`,
      {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ entries, base_file_hash: baseFileHash }),
      }
    );
    return this.parse<TextProcessorConfig>(response);
  }

  async previewConfig(
    inputPath: string,
    entries: EntryPayload[] | null,
    includePreprocessorSnapshots = false,
    maxChangedChunks: number | null = null
  ): Promise<TextProcessorPreview> {
    const response = await fetch(
      `${this.baseUrl}/project/text-processor-config/preview?input_path=${encodeURIComponent(inputPath)}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          entries,
          include_preprocessor_snapshots: includePreprocessorSnapshots,
          max_changed_chunks: maxChangedChunks,
        }),
      }
    );
    return this.parse<TextProcessorPreview>(response);
  }

  async previewDiff(
    inputPath: string,
    draftEntries: EntryPayload[],
    baselineEntries: EntryPayload[] | null,
    maxChangedChunks = 50
  ): Promise<TextProcessorPreviewDiff> {
    const response = await fetch(
      `${this.baseUrl}/project/text-processor-config/preview-diff?input_path=${encodeURIComponent(inputPath)}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          draft_entries: draftEntries,
          baseline_entries: baselineEntries,
          max_changed_chunks: maxChangedChunks,
        }),
      }
    );
    return this.parse<TextProcessorPreviewDiff>(response);
  }

  async convertConfig(inputPath: string): Promise<TextProcessorConfig> {
    const response = await fetch(
      `${this.baseUrl}/project/text-processor-config/convert?input_path=${encodeURIComponent(inputPath)}`,
      { method: 'POST' }
    );
    return this.parse<TextProcessorConfig>(response);
  }

  async resetConfig(
    inputPath: string,
    source: 'shipped_default' | 'user_default'
  ): Promise<TextProcessorConfig> {
    const response = await fetch(
      `${this.baseUrl}/project/text-processor-config/reset?input_path=${encodeURIComponent(inputPath)}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source }),
      }
    );
    return this.parse<TextProcessorConfig>(response);
  }

  async getGlobalDefault(): Promise<TextProcessorGlobalDefault> {
    const response = await fetch(
      `${this.baseUrl}/settings/text-processor-default`
    );
    return this.parse<TextProcessorGlobalDefault>(response);
  }

  async updateGlobalDefault(
    entries: EntryPayload[],
    basedOnDefaultSha256?: string,
    baseFileHash?: string | null
  ): Promise<TextProcessorGlobalDefault> {
    const response = await fetch(
      `${this.baseUrl}/settings/text-processor-default`,
      {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          entries,
          based_on_default_sha256: basedOnDefaultSha256 ?? null,
          base_file_hash: baseFileHash ?? null,
        }),
      }
    );
    return this.parse<TextProcessorGlobalDefault>(response);
  }

  async deleteGlobalDefault(
    baseFileHash?: string | null
  ): Promise<TextProcessorGlobalDefault> {
    const query = baseFileHash
      ? `?base_file_hash=${encodeURIComponent(baseFileHash)}`
      : '';
    const response = await fetch(
      `${this.baseUrl}/settings/text-processor-default${query}`,
      { method: 'DELETE' }
    );
    return this.parse<TextProcessorGlobalDefault>(response);
  }
}

// Export singleton instance
export const textProcessorApi = new TextProcessorApiService();
