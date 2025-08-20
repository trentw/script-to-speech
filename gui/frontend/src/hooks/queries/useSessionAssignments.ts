import { useQuery } from '@tanstack/react-query';

import { apiService } from '@/services/api';
import type { CharacterInfo, VoiceAssignment } from '@/types/voice-casting';
import type { VoiceCastingSession } from '@/types/voice-casting';
import { yamlUtils } from '@/utils/yamlUtils';

export interface SessionAssignmentsData {
  // Core data
  assignments: Map<string, VoiceAssignment>;
  characters: Map<string, CharacterInfo>;
  yamlContent: string;
  yamlVersionId?: number;

  // Derived state
  assignedCount: number;
  totalCount: number;
  progress: number; // 0-100 percentage

  // Session metadata
  session: VoiceCastingSession;
}

/**
 * Query hook that fetches session data and derives voice assignment state
 *
 * Features:
 * - Fetches session data from backend
 * - Parses YAML content to assignments Map at query level
 * - Computes derived state (progress, counts, etc.)
 * - Proper caching and refetch strategies
 * - Type-safe return values
 */
export function useSessionAssignments(sessionId: string | undefined) {
  return useQuery<SessionAssignmentsData, Error>({
    queryKey: ['session', sessionId],
    queryFn: async (): Promise<SessionAssignmentsData> => {
      if (!sessionId) {
        throw new Error('Session ID is required');
      }

      // 1. Fetch session data from backend
      const sessionResponse =
        await apiService.getVoiceCastingSession(sessionId);

      if (sessionResponse.error) {
        throw new Error(sessionResponse.error);
      }

      const session = sessionResponse.data!;

      // 2. Initialize assignments and characters maps
      let assignments = new Map<string, VoiceAssignment>();
      const characters = new Map<string, CharacterInfo>();

      // 3. Parse YAML content if it exists
      if (session.yaml_content?.trim()) {
        try {
          // Parse YAML to get assignments
          assignments = await yamlUtils.yamlToAssignments(
            session.yaml_content,
            {
              allowPartial: true, // Allow partial assignments for progress tracking
            }
          );
        } catch (error) {
          // Log parse error but don't fail the query - allow partial state
          console.warn('Failed to parse YAML content:', error);
        }
      }

      // 4. Extract characters from screenplay if session has screenplay path
      if (session.screenplay_json_path) {
        try {
          const extractResponse = await apiService.extractCharacters(
            session.screenplay_json_path
          );

          if (extractResponse.data) {
            // Convert character array to Map
            extractResponse.data.characters.forEach((char) => {
              characters.set(char.name, {
                name: char.name,
                lineCount: char.line_count,
                totalCharacters: char.total_characters,
                longestDialogue: char.longest_dialogue,
                isNarrator:
                  char.name.toLowerCase() === 'default' ||
                  char.name.toLowerCase() === 'narrator',
                description: char.casting_notes,
                notes: char.role,
              });
            });
          }
        } catch (error) {
          // Log character extraction error but don't fail the query
          console.warn('Failed to extract characters:', error);
        }
      }

      // 5. Compute derived state
      const totalCount = characters.size;
      const assignedCount = assignments.size;
      const progress =
        totalCount > 0 ? Math.round((assignedCount / totalCount) * 100) : 0;

      return {
        // Core data
        assignments,
        characters,
        yamlContent: session.yaml_content || '',
        yamlVersionId: session.yaml_version_id,

        // Derived state
        assignedCount,
        totalCount,
        progress,

        // Session metadata
        session,
      };
    },
    enabled: !!sessionId,

    // React Query configuration
    staleTime: 5 * 60 * 1000, // Consider data fresh for 5 minutes
    gcTime: 10 * 60 * 1000, // Keep in cache for 10 minutes
    refetchOnWindowFocus: true, // Refetch when window gains focus
    refetchOnReconnect: true, // Refetch when network reconnects

    // Retry configuration
    retry: (failureCount, error) => {
      // Don't retry for 404 errors (session not found)
      if (error instanceof Error && error.message.includes('404')) {
        return false;
      }
      // Retry up to 3 times for other errors
      return failureCount < 3;
    },

    // Retry delay with exponential backoff
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });
}
