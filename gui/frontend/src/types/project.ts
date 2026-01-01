// Project Mode Types

export interface ProjectStatus {
  // File existence checks
  hasPdf: boolean;
  hasJson: boolean;
  hasVoiceConfig: boolean;
  hasOptionalConfig: boolean;
  hasOutputMp3: boolean;

  // Derived states
  screenplayParsed: boolean;
  voicesCast: boolean;
  audioGenerated: boolean;

  // Metadata (if files exist)
  speakerCount?: number;
  dialogueChunks?: number;
  voicesAssigned?: number;

  // Error states for corrupt files
  jsonError?: string;
  voiceConfigError?: string;
}

// API response type from backend
export interface ProjectMeta {
  name: string;
  inputPath: string;
  outputPath: string;
  hasJson: boolean;
  hasVoiceConfig: boolean;
  lastModified: string;
}

// Store type for project state (used in Zustand)
export interface ProjectMetaStore {
  screenplayName: string;
  inputPath: string;
  outputPath: string;
}

export interface CreateProjectRequest {
  sourceFile: string; // Path to uploaded temp file
}

export interface CreateProjectResponse {
  inputPath: string;
  outputPath: string;
  screenplayName: string;
  // Header/footer detection results for popover display
  autoRemovedPatterns?: DetectedPattern[];
  suggestedPatterns?: DetectedPattern[];
}

// Import for forward reference
import type { DetectedPattern } from './index';

export interface GenerateOptionalConfigRequest {
  inputPath: string;
}

export interface GenerateOptionalConfigResponse {
  created: boolean;
  path: string;
}
