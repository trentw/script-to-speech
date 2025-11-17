/**
 * Project API service for interacting with project endpoints
 */

import { API_BASE_URL } from '../config/api';
import type { ProjectStatus } from '../types/project';

interface ApiResponse<T = unknown> {
  ok: boolean;
  data?: T;
  error?: string;
  details?: Record<string, unknown>;
}

interface ProjectMeta {
  name: string;
  input_path: string;
  output_path: string;
  has_json: boolean;
  has_voice_config: boolean;
  last_modified: string;
}

interface ProjectCreateData {
  inputPath: string;
  outputPath: string;
  screenplayName: string;
}

class ProjectApiService {
  private baseUrl = API_BASE_URL;

  /**
   * Discover existing projects in the workspace
   */
  async discoverProjects(limit = 20): Promise<ProjectMeta[]> {
    const response = await fetch(
      `${this.baseUrl}/projects/discover?limit=${limit}`
    );
    const result: ApiResponse<ProjectMeta[]> = await response.json();

    if (!result.ok) {
      throw new Error(result.error || 'Failed to discover projects');
    }

    return result.data || [];
  }

  /**
   * Get detailed status for a specific project
   */
  async getProjectStatus(inputPath: string): Promise<ProjectStatus> {
    const response = await fetch(
      `${this.baseUrl}/project/status?input_path=${encodeURIComponent(inputPath)}`
    );
    const result: ApiResponse<Record<string, unknown>> = await response.json();

    if (!result.ok) {
      throw new Error(result.error || 'Failed to get project status');
    }

    if (!result.data) {
      throw new Error('No project status data returned');
    }

    // Transform snake_case API response to camelCase frontend interface
    const statusData = result.data as Record<string, unknown>;
    return {
      hasPdf: statusData.has_pdf as boolean,
      hasJson: statusData.has_json as boolean,
      hasVoiceConfig: statusData.has_voice_config as boolean,
      hasOptionalConfig: statusData.has_optional_config as boolean,
      hasOutputMp3: statusData.has_output_mp3 as boolean,
      screenplayParsed: statusData.screenplay_parsed as boolean,
      voicesCast: statusData.voices_cast as boolean,
      audioGenerated: statusData.audio_generated as boolean,
      speakerCount: statusData.speaker_count as number | undefined,
      dialogueChunks: statusData.dialogue_chunks as number | undefined,
      voicesAssigned: statusData.voices_assigned as number | undefined,
      jsonError: statusData.json_error as string | undefined,
      voiceConfigError: statusData.voice_config_error as string | undefined,
    };
  }

  /**
   * Upload a screenplay file to temporary storage
   */
  async uploadFile(file: File): Promise<string> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${this.baseUrl}/upload`, {
      method: 'POST',
      body: formData,
    });

    const result: ApiResponse<{ tempPath: string }> = await response.json();

    if (!result.ok) {
      throw new Error(result.error || 'Failed to upload file');
    }

    if (!result.data?.tempPath) {
      throw new Error('No temporary path returned from upload');
    }

    return result.data.tempPath;
  }

  /**
   * Create a new project from an uploaded screenplay file
   */
  async createProject(sourceFile: string): Promise<ProjectCreateData> {
    const response = await fetch(`${this.baseUrl}/project/new`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ sourceFile }),
    });

    const result: ApiResponse<ProjectCreateData> = await response.json();

    if (!result.ok) {
      throw new Error(result.error || 'Failed to create project');
    }

    if (!result.data) {
      throw new Error('No project data returned');
    }

    return result.data;
  }

  /**
   * Complete workflow for creating a new project from file upload
   */
  async createProjectFromFile(file: File): Promise<ProjectCreateData> {
    // Step 1: Upload file to temporary storage
    const tempPath = await this.uploadFile(file);

    try {
      // Step 2: Create project from uploaded file
      const projectData = await this.createProject(tempPath);
      return projectData;
    } catch (error) {
      // Clean up temp file on error if possible
      // Note: Backend should handle cleanup, but we can try a best effort
      console.warn(
        'Project creation failed, temporary file may need cleanup:',
        tempPath
      );
      throw error;
    }
  }
}

// Export singleton instance
export const projectApi = new ProjectApiService();

// Export types for use in components
export type { ApiResponse, ProjectCreateData, ProjectMeta };
