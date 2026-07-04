/**
 * Types for the text processor configuration feature.
 *
 * These payloads are deeply nested and flow in both directions (read and
 * write), so they intentionally mirror the backend wire format (snake_case)
 * instead of being remapped to camelCase at the service layer.
 */

export type ProcessorKind = 'preprocessor' | 'processor';

export type FieldType =
  | 'string'
  | 'integer'
  | 'boolean'
  | 'enum'
  | 'list'
  | 'object'
  | 'dict_of_string_lists';

export interface ItemSchema {
  type: FieldType;
  suggestions_ref?: 'chunk_types' | 'chunk_fields';
  fields?: FieldSpec[];
}

export interface FieldSpec {
  name: string;
  type: FieldType;
  required?: boolean;
  default?: unknown;
  label?: string;
  description?: string;
  advanced?: boolean;
  enum?: string[];
  min?: number;
  format?: 'regex';
  suggestions_ref?: 'chunk_types' | 'chunk_fields';
  xor_group?: string;
  item_schema?: ItemSchema;
}

export interface ProcessorSchema {
  label: string;
  description: string;
  /** Longer usage/setup notes, shown behind the card's help button */
  help?: string;
  fields: FieldSpec[];
}

export interface RegistryProcessor {
  name: string;
  kind: ProcessorKind;
  label: string;
  description: string;
  multi_config_mode: 'chain' | 'override';
  schema: ProcessorSchema | null;
}

export interface TextProcessorRegistry {
  preprocessors: RegistryProcessor[];
  processors: RegistryProcessor[];
  chunk_types: string[];
  chunk_fields: string[];
}

export interface TextProcessorEntry {
  id?: string | null;
  kind: ProcessorKind;
  name: string;
  known: boolean;
  /** Structured config; used when config_yaml is empty */
  config: Record<string, unknown> | null;
  /**
   * YAML text of the config sub-tree. Authoritative over `config` when
   * non-empty (preserves comments); cleared by the form editor after edits.
   */
  config_yaml: string | null;
}

export interface TextProcessorMetadata {
  mode?: string;
  seeded_from?: string;
  seeded_by_version?: string;
  default_config_sha256?: string;
}

export interface TextProcessorConfig {
  path: string;
  yaml_text: string;
  file_hash: string;
  entries: TextProcessorEntry[];
  metadata: TextProcessorMetadata | null;
  stale: boolean;
  is_legacy_additive: boolean;
  current_default_hash: string;
}

export interface TextProcessorGlobalDefault
  extends Partial<TextProcessorConfig> {
  exists: boolean;
  path: string;
}

export interface ValidationIssue {
  entry_index: number;
  kind?: ProcessorKind;
  name?: string;
  message: string;
}

export interface ValidationResult {
  valid: boolean;
  errors: ValidationIssue[];
  warnings: ValidationIssue[];
}

export type Chunk = Record<string, unknown> & {
  type?: string;
  speaker?: string;
  text?: string;
  raw_text?: string;
};

export interface PreviewStep {
  name: string;
  before: Chunk;
  after: Chunk;
}

export interface PreviewChangedChunk {
  index: number;
  chunk_type: string;
  speaker: string;
  before: Chunk;
  after: Chunk;
  steps: PreviewStep[];
}

export interface PreviewPreprocessorStage {
  name: string;
  modified: boolean;
  before_count: number;
  after_count: number;
  before?: Chunk[];
  after?: Chunk[];
}

export interface TextProcessorPreview {
  input_chunk_count: number;
  final_chunk_count: number;
  preprocessor_stages: PreviewPreprocessorStage[];
  changed_chunks: PreviewChangedChunk[];
  changed_chunk_count: number;
  /** True when changed_chunks was capped server-side */
  truncated: boolean;
}

export interface PreviewDiffChangedChunk {
  index: number;
  chunk_type: string;
  speaker: string;
  before: Chunk;
  after: Chunk;
}

export interface PreviewDiffStage {
  name: string;
  modified: boolean;
  before_count: number;
  after_count: number;
}

/**
 * Result of diffing a draft pipeline against a baseline: only chunks whose
 * final output differs between the two runs. alignment is "counts_differ"
 * when a preprocessor change altered chunk counts (per-chunk pairing is then
 * ill-posed and only the stage summaries tell the story).
 */
export interface TextProcessorPreviewDiff {
  alignment: 'index' | 'counts_differ';
  input_chunk_count: number;
  baseline_final_count: number;
  draft_final_count: number;
  baseline_stages: PreviewDiffStage[];
  draft_stages: PreviewDiffStage[];
  changed_chunks: PreviewDiffChangedChunk[];
  changed_chunk_count: number;
  truncated: boolean;
}
