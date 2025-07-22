import type { ProviderInfo } from '@/types/api/provider'
import type { TaskResponse, TaskStatus } from '@/types/api/task'
import type { VoiceEntry } from '@/types/api/voice'

// Provider Info mock factory
export function createMockProviderInfo(overrides?: Partial<ProviderInfo>): ProviderInfo {
  return {
    provider_id: 'test-provider',
    display_name: 'Test Provider',
    has_voice_library_support: true,
    supports_ssml: false,
    voice_library_voices: ['voice-1', 'voice-2'],
    direct_input_voices: ['custom-voice-1', 'custom-voice-2'],
    ...overrides,
  }
}

// Voice Entry mock factory
export function createMockVoiceEntry(overrides?: Partial<VoiceEntry>): VoiceEntry {
  return {
    voice_id: 'test-voice-id',
    name: 'Test Voice',
    gender: 'M',
    age: 'adult',
    accent: 'american',
    description: 'A test voice for unit tests',
    provider: 'test-provider',
    tags: ['test', 'mock'],
    ...overrides,
  }
}

// Task Response mock factory
export function createMockTaskResponse(overrides?: Partial<TaskResponse>): TaskResponse {
  return {
    task_id: 'test-task-123',
    status: 'pending' as TaskStatus,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    message: 'Task created successfully',
    ...overrides,
  }
}

// Common test data constants
export const TEST_PROVIDERS: ProviderInfo[] = [
  createMockProviderInfo({
    provider_id: 'openai',
    display_name: 'OpenAI',
    has_voice_library_support: false,
    supports_ssml: false,
    voice_library_voices: [],
    direct_input_voices: ['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'],
  }),
  createMockProviderInfo({
    provider_id: 'elevenlabs',
    display_name: 'ElevenLabs',
    has_voice_library_support: true,
    supports_ssml: false,
    voice_library_voices: ['rachel', 'drew', 'clyde'],
    direct_input_voices: [],
  }),
]

export const TEST_VOICES: VoiceEntry[] = [
  createMockVoiceEntry({
    voice_id: 'rachel',
    name: 'Rachel',
    gender: 'F',
    age: 'young-adult',
    accent: 'american',
    description: 'Warm and conversational voice',
    provider: 'elevenlabs',
    tags: ['narrative', 'conversational'],
  }),
  createMockVoiceEntry({
    voice_id: 'drew',
    name: 'Drew',
    gender: 'M',
    age: 'middle-aged',
    accent: 'british',
    description: 'Deep and authoritative voice',
    provider: 'elevenlabs',
    tags: ['news', 'documentary'],
  }),
]

export const TEST_TASK_PENDING = createMockTaskResponse({
  task_id: 'task-pending-123',
  status: 'pending',
  message: 'Task is pending',
})

export const TEST_TASK_PROCESSING = createMockTaskResponse({
  task_id: 'task-processing-123',
  status: 'processing',
  message: 'Generating audio...',
  progress: 45,
})

export const TEST_TASK_COMPLETED = createMockTaskResponse({
  task_id: 'task-completed-123',
  status: 'completed',
  message: 'Audio generation completed',
  result: {
    audio_url: '/api/audio/test-audio.mp3',
    duration: 10.5,
  },
})

export const TEST_TASK_FAILED = createMockTaskResponse({
  task_id: 'task-failed-123',
  status: 'failed',
  message: 'Failed to generate audio',
  error: 'Invalid API key',
})