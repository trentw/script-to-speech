import type {
  ApiResponse,
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

const API_BASE_URL = 'http://127.0.0.1:8000/api';

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

  async parseYaml(
    yamlContent: string
  ): Promise<ApiResponse<import('../types/voice-casting').ParseYamlResponse>> {
    return this.request<import('../types/voice-casting').ParseYamlResponse>(
      '/voice-casting/parse-yaml',
      {
        method: 'POST',
        body: JSON.stringify({ yaml_content: yamlContent }),
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
