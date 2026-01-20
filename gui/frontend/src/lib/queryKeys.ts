/**
 * Centralized React Query keys for consistent cache management
 */

export const queryKeys = {
  // Backend status
  backendStatus: ['backend', 'status'] as const,

  // Environment/API keys
  envKeys: ['settings', 'env'] as const,
  apiKeyValidation: ['settings', 'env', 'validation'] as const,

  // Providers
  providers: ['providers'] as const,
  providersInfo: ['providers', 'info'] as const,
  providerInfo: (provider: string) => ['providers', provider] as const,

  // Voice library
  voiceLibrary: (provider: string) => ['voices', 'library', provider] as const,
  voiceDetails: (provider: string, stsId: string) =>
    ['voices', 'details', provider, stsId] as const,
  voiceSearch: (params: Record<string, unknown>) =>
    ['voices', 'search', params] as const,
  voiceLibraryStats: ['voices', 'stats'] as const,

  // Projects
  projectsDiscover: (limit?: number) =>
    limit ? ['projects', 'discover', limit] : (['projects', 'discover'] as const),
  projectStatus: (inputPath: string) =>
    ['projects', 'status', inputPath] as const,

  // Tasks
  allTasks: ['tasks'] as const,
  taskStatus: (taskId: string) => ['tasks', taskId] as const,

  // Audiobook
  audiobookTasks: ['audiobook', 'tasks'] as const,
  audiobookStatus: (taskId: string) => ['audiobook', 'status', taskId] as const,
  audiobookResult: (taskId: string) => ['audiobook', 'result', taskId] as const,

  // Review/clips
  cacheMisses: (projectName: string) =>
    ['review', 'cache-misses', projectName] as const,
  silentClips: (projectName: string) =>
    ['review', 'silent-clips', projectName] as const,
} as const;
