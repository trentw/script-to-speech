// Voice Editor Types
// Response models use camelCase (CamelModel on the backend).
// Request models use snake_case (BaseModel on the backend).

export interface SchemaPropertyDefinition {
  description: string;
  type: 'range' | 'enum' | 'text';
  min?: number;
  max?: number;
  scalePoints?: Record<string, string>;
  values?: string[];
}

export interface VoiceLibrarySchema {
  voiceProperties: Record<string, SchemaPropertyDefinition>;
}

export interface VoiceUpdateRequest {
  voice_properties?: Record<string, string | number | null>;
  description?: Record<string, string | null>;
  tags?: Record<string, string[] | null>;
}

export interface LLMRunVoiceData {
  result: {
    voice_properties?: Record<string, string | number>;
    description?: Record<string, string>;
    tags?: Record<string, string[]>;
    reasoning?: Record<string, string>;
  };
  flags: string[];
}

export interface LLMRunImportResponse {
  provider: string;
  voices: Record<string, LLMRunVoiceData>;
  audioDir: string;
}
