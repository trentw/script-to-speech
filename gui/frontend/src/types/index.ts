// API Types

export const TaskStatus = {
  PENDING: 'pending',
  PROCESSING: 'processing',
  COMPLETED: 'completed',
  FAILED: 'failed',
} as const;

export type TaskStatus = (typeof TaskStatus)[keyof typeof TaskStatus];

export const FieldType = {
  STRING: 'string',
  INTEGER: 'integer',
  FLOAT: 'float',
  BOOLEAN: 'boolean',
  LIST: 'list',
  DICT: 'dict',
} as const;

export type FieldType = (typeof FieldType)[keyof typeof FieldType];

export interface ProviderField {
  name: string;
  type: FieldType;
  required: boolean;
  description?: string;
  default?: string | number | boolean | string[] | Record<string, unknown>;
  options?: string[];
  min_value?: number;
  max_value?: number;
}

export interface ProviderInfo {
  identifier: string;
  name: string;
  description?: string;
  required_fields: ProviderField[];
  optional_fields: ProviderField[];
  max_threads: number;
}

export interface VoiceProperties {
  accent?: string;
  gender?: string;
  age?: number;
  authority?: number;
  energy?: number;
  pace?: number;
  performative?: number;
  pitch?: number;
  quality?: number;
  range?: number;
}

export interface VoiceDescription {
  provider_name?: string;
  provider_description?: string;
  provider_use_cases?: string;
  custom_description?: string;
  perceived_age?: string;
}

export interface VoiceTags {
  provider_use_cases?: string[];
  custom_tags?: string[];
  character_types?: string[];
}

export interface VoiceEntry {
  sts_id: string;
  provider: string;
  config: Record<string, string | number | boolean | string[]>;
  voice_properties?: VoiceProperties;
  description?: VoiceDescription;
  tags?: VoiceTags;
  preview_url?: string;
}

export interface VoiceDetails extends VoiceEntry {
  expanded_config: Record<string, string | number | boolean | string[]>;
}

export interface GenerationRequest {
  provider: string;
  config: Record<string, string | number | boolean | string[]>;
  text: string;
  sts_id?: string;
  variants?: number;
  output_filename?: string;
}

export interface TaskResponse {
  task_id: string;
  status: TaskStatus;
  message: string;
}

export interface TaskStatusResponse {
  task_id: string;
  status: TaskStatus;
  message: string;
  progress?: number;
  result?: GenerationResult;
  error?: string;
  created_at?: string;
  completed_at?: string;
  audio_urls?: string[];
  request?: GenerationRequest;
}

export interface GenerationResult {
  files: string[];
  provider: string;
  voice_id: string;
  text_preview: string;
  duration_ms?: number;
}

export interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

export interface ErrorResponse {
  error: string;
  detail?: string;
  code?: string;
}

// UI Types

export interface FormField {
  name: string;
  label: string;
  type: FieldType;
  required: boolean;
  value: string | number | boolean | string[] | Record<string, unknown>;
  error?: string;
  description?: string;
  options?: string[];
  min?: number;
  max?: number;
}

export interface AppState {
  selectedProvider?: string;
  providers: ProviderInfo[];
  voiceLibrary: Record<string, VoiceEntry[]>;
  currentConfig: Record<string, string | number | boolean | string[]>;
  selectedVoice?: VoiceEntry;
  text: string;
  generationTasks: TaskStatusResponse[];
  loading: boolean;
  error?: string;
}

export interface ApiResponse<T> {
  data?: T;
  error?: string;
}

// Voice Library Types

export interface VoiceLibraryStats {
  total_voices: number;
  providers: Record<string, number>;
  gender_distribution: Record<string, number>;
  tag_counts: Record<string, number>;
}

export interface ExpandedStsIdResponse {
  provider: string;
  sts_id: string;
  expanded_config: Record<string, string | number | boolean | string[]>;
  voice_properties?: VoiceProperties;
}

// File Types

export interface AudioFile {
  filename: string;
  size: number;
  created_at: string;
  duration_ms?: number;
}

export interface AudioFilesResponse {
  files: AudioFile[];
}

// Screenplay Types

export interface ScreenplayAnalysis {
  chunk_type_counts: Record<string, number>;
  speaker_counts: Record<string, number>;
  total_distinct_speakers: number;
  speakers: string[];
  total_chunks: number;
}

export interface ScreenplayFiles {
  json?: string;
  text?: string;
}

export interface ScreenplayChunk {
  chunk_id: number;
  chunk_type: string;
  speaker?: string;
  dialogue?: string;
  parenthetical?: string;
  action?: string;
  metadata?: Record<string, string | number | boolean>;
}

export interface ScreenplayResult {
  files: ScreenplayFiles;
  analysis?: ScreenplayAnalysis;
  screenplay_name: string;
  original_filename: string;
  text_only: boolean;
  log_file?: string;
  chunks?: ScreenplayChunk[]; // JSON chunks from the parsed screenplay
}

export interface ScreenplayTaskStatus {
  task_id: string;
  status: TaskStatus;
  message: string;
  progress?: number;
  result?: ScreenplayResult;
  error?: string;
  created_at?: string;
  completed_at?: string;
}

export interface RecentScreenplay {
  task_id: string;
  filename: string;
  screenplay_name: string;
  created_at: string;
  completed_at?: string;
  analysis?: ScreenplayAnalysis;
}
