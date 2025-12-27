import { API_BASE_URL } from '../config/api';
import type {
  ApiResponse,
  AudiobookGenerationProgress,
  AudiobookGenerationRequest,
  AudiobookGenerationResult,
  AudiobookTaskResponse,
  AudioFilesResponse,
  ExpandedStsIdResponse,
  GenerationRequest,
  ProviderInfo,
  RecentScreenplay,
  ScreenplayResult,
  TaskResponse,
  TaskStatusResponse,
  ValidationResult,
  VoiceDetails,
  VoiceEntry,
  VoiceLibraryStats,
} from '../types';

class ApiService {
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
        ...options,
      });

      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => ({ error: 'Unknown error' }));
        return {
          error:
            errorData.detail || errorData.error || `HTTP ${response.status}`,
          status: response.status,
        };
      }

      const data = await response.json();
      return { data };
    } catch (error) {
      return {
        error: error instanceof Error ? error.message : 'Network error',
      };
    }
  }

  // Provider endpoints
  async getProviders(): Promise<ApiResponse<string[]>> {
    return this.request<string[]>('/providers');
  }

  async getProvidersInfo(): Promise<ApiResponse<ProviderInfo[]>> {
    return this.request<ProviderInfo[]>('/providers/info');
  }

  async getProviderInfo(provider: string): Promise<ApiResponse<ProviderInfo>> {
    return this.request<ProviderInfo>(`/providers/${provider}`);
  }

  async validateProviderConfig(
    provider: string,
    config: Record<string, string | number | boolean | string[]>
  ): Promise<ApiResponse<ValidationResult>> {
    return this.request<ValidationResult>(`/providers/${provider}/validate`, {
      method: 'POST',
      body: JSON.stringify(config),
    });
  }

  // Voice library endpoints
  async getVoiceLibraryProviders(): Promise<ApiResponse<string[]>> {
    return this.request<string[]>('/voice-library/providers');
  }

  async getProviderVoices(
    provider: string
  ): Promise<ApiResponse<VoiceEntry[]>> {
    return this.request<VoiceEntry[]>(`/voice-library/${provider}`);
  }

  async getVoiceDetails(
    provider: string,
    stsId: string
  ): Promise<ApiResponse<VoiceDetails>> {
    return this.request<VoiceDetails>(`/voice-library/${provider}/${stsId}`);
  }

  async searchVoices(params: {
    query?: string;
    provider?: string;
    gender?: string;
    tags?: string[];
  }): Promise<ApiResponse<VoiceEntry[]>> {
    const searchParams = new URLSearchParams();
    if (params.query) searchParams.append('query', params.query);
    if (params.provider) searchParams.append('provider', params.provider);
    if (params.gender) searchParams.append('gender', params.gender);
    if (params.tags) {
      params.tags.forEach((tag) => searchParams.append('tags', tag));
    }

    return this.request<VoiceEntry[]>(`/voice-library/search?${searchParams}`);
  }

  async getVoiceLibraryStats(): Promise<ApiResponse<VoiceLibraryStats>> {
    return this.request<VoiceLibraryStats>('/voice-library/stats');
  }

  async expandStsId(
    provider: string,
    stsId: string
  ): Promise<ApiResponse<ExpandedStsIdResponse>> {
    return this.request<ExpandedStsIdResponse>(
      `/voice-library/${provider}/${stsId}/expand`,
      {
        method: 'POST',
      }
    );
  }

  // Generation endpoints
  async createGenerationTask(
    request: GenerationRequest
  ): Promise<ApiResponse<TaskResponse>> {
    return this.request<TaskResponse>('/generate', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async getTaskStatus(
    taskId: string
  ): Promise<ApiResponse<TaskStatusResponse>> {
    return this.request<TaskStatusResponse>(`/generate/status/${taskId}`);
  }

  async getAllTasks(): Promise<ApiResponse<TaskStatusResponse[]>> {
    return this.request<TaskStatusResponse[]>('/generate/tasks');
  }

  async cleanupOldTasks(
    maxAgeHours: number = 24
  ): Promise<ApiResponse<{ message: string }>> {
    return this.request<{ message: string }>(
      `/generate/cleanup?max_age_hours=${maxAgeHours}`,
      {
        method: 'DELETE',
      }
    );
  }

  // File endpoints
  getAudioFile(filename: string): string {
    return `${API_BASE_URL}/files/${filename}`;
  }

  getScreenplayDownloadUrl(
    taskId: string,
    fileType: 'json' | 'text' | 'log'
  ): string {
    return `${API_BASE_URL}/screenplay/download/${taskId}/${fileType}`;
  }

  getScreenplayDownloadFromPathUrl(filePath: string, filename: string): string {
    const params = new URLSearchParams({
      file_path: filePath,
      filename: filename,
    });
    return `${API_BASE_URL}/screenplay/download-from-path?${params}`;
  }

  async listAudioFiles(): Promise<ApiResponse<AudioFilesResponse>> {
    return this.request<AudioFilesResponse>('/files');
  }

  // Screenplay endpoints
  async uploadScreenplay(
    file: File,
    textOnly: boolean = false
  ): Promise<ApiResponse<TaskResponse>> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('text_only', textOnly.toString());

    try {
      const response = await fetch(`${API_BASE_URL}/screenplay/parse`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => ({ error: 'Unknown error' }));
        return {
          error:
            errorData.detail || errorData.error || `HTTP ${response.status}`,
        };
      }

      const data = await response.json();
      return { data };
    } catch (error) {
      return {
        error: error instanceof Error ? error.message : 'Network error',
      };
    }
  }

  async getScreenplayTaskStatus(
    taskId: string
  ): Promise<ApiResponse<TaskStatusResponse>> {
    return this.request<TaskStatusResponse>(`/screenplay/status/${taskId}`);
  }

  async getAllScreenplayTasks(): Promise<ApiResponse<TaskStatusResponse[]>> {
    return this.request<TaskStatusResponse[]>('/screenplay/tasks');
  }

  async getScreenplayResult(
    taskId: string
  ): Promise<ApiResponse<ScreenplayResult>> {
    return this.request<ScreenplayResult>(`/screenplay/result/${taskId}`);
  }

  async getRecentScreenplays(
    limit: number = 10
  ): Promise<ApiResponse<RecentScreenplay[]>> {
    return this.request<RecentScreenplay[]>(
      `/screenplay/recent?limit=${limit}`
    );
  }

  async deleteScreenplayTask(
    taskId: string,
    deleteFiles: boolean = false
  ): Promise<ApiResponse<{ message: string }>> {
    return this.request<{ message: string }>(
      `/screenplay/${taskId}?delete_files=${deleteFiles}`,
      {
        method: 'DELETE',
      }
    );
  }

  async cleanupOldScreenplayTasks(
    maxAgeHours: number = 24
  ): Promise<ApiResponse<{ message: string }>> {
    return this.request<{ message: string }>(
      `/screenplay/cleanup?max_age_hours=${maxAgeHours}`,
      {
        method: 'DELETE',
      }
    );
  }

  // Voice Casting endpoints
  async extractCharacters(
    screenplayJsonPath: string
  ): Promise<
    ApiResponse<import('../types/voice-casting').ExtractCharactersResponse>
  > {
    return this.request<
      import('../types/voice-casting').ExtractCharactersResponse
    >('/voice-casting/extract-characters', {
      method: 'POST',
      body: JSON.stringify({ screenplay_json_path: screenplayJsonPath }),
    });
  }

  async generateYaml(params: {
    assignments: Record<
      string,
      import('../types/voice-casting').VoiceAssignment
    >;
    character_info: Record<
      string,
      import('../types/voice-casting').CharacterInfo
    >;
    include_comments?: boolean;
  }): Promise<
    ApiResponse<import('../types/voice-casting').GenerateYamlResponse>
  > {
    return this.request<import('../types/voice-casting').GenerateYamlResponse>(
      '/voice-casting/generate-yaml',
      {
        method: 'POST',
        body: JSON.stringify(params),
      }
    );
  }

  async validateYaml(params: {
    yaml_content: string;
    screenplay_json_path: string;
  }): Promise<
    ApiResponse<import('../types/voice-casting').ValidateYamlResponse>
  > {
    return this.request<import('../types/voice-casting').ValidateYamlResponse>(
      '/voice-casting/validate-yaml',
      {
        method: 'POST',
        body: JSON.stringify(params),
      }
    );
  }

  async parseYaml(params: {
    yamlContent: string;
    allowPartial?: boolean;
  }): Promise<ApiResponse<import('../types/voice-casting').ParseYamlResponse>> {
    return this.request<import('../types/voice-casting').ParseYamlResponse>(
      '/voice-casting/parse-yaml',
      {
        method: 'POST',
        body: JSON.stringify({
          yaml_content: params.yamlContent,
          allow_partial: params.allowPartial,
        }),
      }
    );
  }

  async generateCharacterNotesPrompt(params: {
    session_id: string;
    yaml_content: string;
    custom_prompt_path?: string;
  }): Promise<ApiResponse<{ prompt_content: string; privacy_notice: string }>> {
    return this.request<{ prompt_content: string; privacy_notice: string }>(
      '/voice-casting/generate-character-notes-prompt',
      {
        method: 'POST',
        body: JSON.stringify(params),
      }
    );
  }

  async generateVoiceLibraryPrompt(params: {
    yaml_content: string;
    providers: string[];
    custom_prompt_path?: string;
  }): Promise<ApiResponse<{ prompt_content: string; privacy_notice: string }>> {
    return this.request<{ prompt_content: string; privacy_notice: string }>(
      '/voice-casting/generate-voice-library-prompt',
      {
        method: 'POST',
        body: JSON.stringify(params),
      }
    );
  }

  async uploadScreenplayJson(
    file: File
  ): Promise<
    ApiResponse<import('../types/voice-casting').VoiceCastingSession>
  > {
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(
        `${API_BASE_URL}/voice-casting/upload-json`,
        {
          method: 'POST',
          body: formData,
        }
      );

      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => ({ error: 'Unknown error' }));
        return {
          error:
            errorData.detail || errorData.error || `HTTP ${response.status}`,
        };
      }

      const data = await response.json();
      return { data };
    } catch (error) {
      return {
        error: error instanceof Error ? error.message : 'Network error',
      };
    }
  }

  async getVoiceCastingSession(
    sessionId: string
  ): Promise<
    ApiResponse<import('../types/voice-casting').VoiceCastingSession>
  > {
    return this.request<import('../types/voice-casting').VoiceCastingSession>(
      `/voice-casting/session/${sessionId}`
    );
  }

  async getSessionWithCharacters(sessionId: string): Promise<
    ApiResponse<{
      session: import('../types/voice-casting').VoiceCastingSession;
      characters: import('../types/voice-casting').CharacterInfo[];
      total_lines: number;
      default_lines: number;
    }>
  > {
    return this.request<{
      session: import('../types/voice-casting').VoiceCastingSession;
      characters: import('../types/voice-casting').CharacterInfo[];
      total_lines: number;
      default_lines: number;
    }>(`/voice-casting/session/${sessionId}/details`);
  }

  async createSessionFromTask(
    taskId: string
  ): Promise<
    ApiResponse<import('../types/voice-casting').VoiceCastingSession>
  > {
    return this.request<import('../types/voice-casting').VoiceCastingSession>(
      '/voice-casting/create-session-from-task',
      {
        method: 'POST',
        body: JSON.stringify({ task_id: taskId }),
      }
    );
  }

  async uploadScreenplaySource(
    sessionId: string,
    file: File
  ): Promise<
    ApiResponse<import('../types/voice-casting').VoiceCastingSession>
  > {
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(
        `${API_BASE_URL}/voice-casting/session/${sessionId}/screenplay-source`,
        {
          method: 'POST',
          body: formData,
        }
      );

      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => ({ error: 'Unknown error' }));
        return {
          error:
            errorData.detail || errorData.error || `HTTP ${response.status}`,
        };
      }

      const data = await response.json();
      return { data };
    } catch (error) {
      return {
        error: error instanceof Error ? error.message : 'Network error',
      };
    }
  }

  async updateSessionYaml(
    sessionId: string,
    yamlContent: string,
    versionId: number
  ): Promise<
    ApiResponse<{
      session: import('../types/voice-casting').VoiceCastingSession;
      warnings: string[];
    }>
  > {
    return this.request<{
      session: import('../types/voice-casting').VoiceCastingSession;
      warnings: string[];
    }>(`/voice-casting/session/${sessionId}/yaml`, {
      method: 'PUT',
      body: JSON.stringify({
        yaml_content: yamlContent,
        version_id: versionId,
      }),
    });
  }

  async updateCharacterAssignment(
    sessionId: string,
    character: string,
    assignment: import('../types/voice-casting').VoiceAssignment,
    versionId: number
  ): Promise<
    ApiResponse<{
      session: import('../types/voice-casting').VoiceCastingSession;
      success: boolean;
    }>
  > {
    return this.request<{
      session: import('../types/voice-casting').VoiceCastingSession;
      success: boolean;
    }>(
      `/voice-casting/session/${sessionId}/assignment/${encodeURIComponent(character)}`,
      {
        method: 'PUT',
        body: JSON.stringify({
          assignment,
          version_id: versionId,
        }),
      }
    );
  }

  async clearCharacterVoice(
    sessionId: string,
    character: string,
    versionId: number
  ): Promise<
    ApiResponse<{
      session: import('../types/voice-casting').VoiceCastingSession;
      success: boolean;
    }>
  > {
    return this.request<{
      session: import('../types/voice-casting').VoiceCastingSession;
      success: boolean;
    }>(
      `/voice-casting/session/${sessionId}/assignment/${encodeURIComponent(character)}/voice?version_id=${versionId}`,
      {
        method: 'DELETE',
      }
    );
  }

  async getRecentSessions(limit: number = 5): Promise<
    ApiResponse<{
      sessions: Array<{
        session_id: string;
        screenplay_name: string;
        status: 'in-progress' | 'completed';
        assigned_count: number;
        total_count: number;
        updated_at: string;
        created_at: string;
      }>;
    }>
  > {
    return this.request<{
      sessions: Array<{
        session_id: string;
        screenplay_name: string;
        status: 'in-progress' | 'completed';
        assigned_count: number;
        total_count: number;
        updated_at: string;
        created_at: string;
      }>;
    }>(`/voice-casting/sessions?limit=${limit}`);
  }

  // Audiobook Generation endpoints
  // Backend uses CamelModel for responses, so they come back as camelCase automatically.
  // Request bodies still need snake_case since AudiobookGenerationRequest uses BaseModel.

  async createAudiobookTask(
    request: AudiobookGenerationRequest
  ): Promise<ApiResponse<AudiobookTaskResponse>> {
    return this.request<AudiobookTaskResponse>('/audiobook/generate', {
      method: 'POST',
      body: JSON.stringify({
        project_name: request.projectName,
        input_json_path: request.inputJsonPath,
        voice_config_path: request.voiceConfigPath,
        mode: request.mode || 'full',
        silence_threshold: request.silenceThreshold,
        cache_overrides_dir: request.cacheOverridesDir,
        text_processor_configs: request.textProcessorConfigs,
        gap_ms: request.gapMs || 500,
        max_workers: request.maxWorkers || 12,
      }),
    });
  }

  async getAudiobookStatus(
    taskId: string
  ): Promise<ApiResponse<AudiobookGenerationProgress>> {
    return this.request<AudiobookGenerationProgress>(
      `/audiobook/status/${taskId}`
    );
  }

  async getAudiobookResult(
    taskId: string
  ): Promise<ApiResponse<AudiobookGenerationResult>> {
    return this.request<AudiobookGenerationResult>(
      `/audiobook/result/${taskId}`
    );
  }

  async getAllAudiobookTasks(): Promise<
    ApiResponse<AudiobookGenerationProgress[]>
  > {
    return this.request<AudiobookGenerationProgress[]>('/audiobook/tasks');
  }

  async cleanupAudiobookTasks(
    maxAgeHours: number = 24
  ): Promise<ApiResponse<{ message: string }>> {
    return this.request<{ message: string }>(
      `/audiobook/cleanup?max_age_hours=${maxAgeHours}`,
      {
        method: 'DELETE',
      }
    );
  }

  // Utility methods
  async healthCheck(): Promise<boolean> {
    try {
      const response = await fetch(
        `${API_BASE_URL.replace('/api', '')}/health`
      );
      return response.ok;
    } catch {
      return false;
    }
  }
}

export const apiService = new ApiService();
