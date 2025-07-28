export interface CharacterInfo {
  name: string;
  line_count: number;
  total_characters: number;
  longest_dialogue: number;
  casting_notes?: string;
  role?: string;
}

export interface VoiceAssignment {
  character: string;
  provider: string;
  sts_id?: string; // Optional - only for library voices
  casting_notes?: string;
  role?: string;
  provider_config?: Record<string, unknown>;
  additional_notes?: string[];
  // Parsed metadata (not stored in YAML)
  line_count?: number;
  total_characters?: number;
  longest_dialogue?: number;
}

export interface ExtractCharactersResponse {
  characters: CharacterInfo[];
  total_lines: number;
  default_lines: number;
}

export interface ValidateYamlResponse {
  is_valid: boolean;
  missing_speakers: string[];
  extra_speakers: string[];
  duplicate_speakers: string[];
  invalid_configs: Record<string, string>;
  message: string;
}

export interface GenerateYamlResponse {
  yaml_content: string;
}

export interface ParseYamlResponse {
  assignments: VoiceAssignment[];
  has_errors: boolean;
  errors: string[];
}

export interface VoiceCastingSession {
  session_id: string;
  screenplay_json_path: string;
  screenplay_name: string;
  screenplay_source_path?: string;
  created_at: string;
  updated_at: string;
  status: 'active' | 'completed' | 'expired';
}
