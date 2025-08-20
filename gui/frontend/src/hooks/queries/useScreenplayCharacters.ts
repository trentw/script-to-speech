import { useQuery } from '@tanstack/react-query';

import { apiService } from '@/services/api';
import type { CharacterInfo } from '@/types/voice-casting';

interface ScreenplayCharactersResponse {
  characters: Record<string, CharacterInfo>;
  screenplay_name: string;
  screenplay_json_path: string;
  total_lines: number;
  default_lines: number;
}

/**
 * Hook to fetch and process character information from a parsed screenplay
 * Can accept either a taskId (for backward compatibility) or a direct JSON path
 */
export function useScreenplayCharacters(jsonPathOrTaskId: string | undefined) {
  return useQuery({
    queryKey: ['screenplay-characters', jsonPathOrTaskId],
    queryFn: async (): Promise<ScreenplayCharactersResponse> => {
      if (!jsonPathOrTaskId) {
        throw new Error('JSON path or Task ID is required');
      }

      let jsonPath: string;
      let screenplayName: string;

      // Check if it's a path (contains .json) or a task ID
      if (jsonPathOrTaskId.includes('.json')) {
        // Direct JSON path provided
        jsonPath = jsonPathOrTaskId;
        // Extract screenplay name from path
        const pathParts = jsonPath.split('/');
        const filename = pathParts[pathParts.length - 1];
        screenplayName = filename.replace('.json', '');
      } else {
        // Task ID provided - fetch task details first
        const taskResponse =
          await apiService.getScreenplayTaskStatus(jsonPathOrTaskId);

        if (taskResponse.error) {
          throw new Error(taskResponse.error);
        }

        const taskResult = taskResponse.data!;

        if (taskResult.status !== 'completed' || !taskResult.result) {
          throw new Error('Screenplay processing not completed');
        }

        if (!taskResult.result.files?.json) {
          throw new Error('No screenplay JSON file found');
        }

        jsonPath = taskResult.result.files.json;
        screenplayName = taskResult.result.screenplay_name;
      }

      // Now extract characters using the file path
      const extractResponse = await apiService.extractCharacters(jsonPath);

      if (extractResponse.error) {
        throw new Error(extractResponse.error);
      }

      const extractData = extractResponse.data!;

      // Convert to the expected format
      const characters: Record<string, CharacterInfo> = {};
      extractData.characters.forEach((char) => {
        characters[char.name] = {
          name: char.name,
          lineCount: char.line_count,
          totalCharacters: char.total_characters,
          longestDialogue: char.longest_dialogue,
          isNarrator:
            char.name.toLowerCase() === 'default' ||
            char.name.toLowerCase() === 'narrator',
          // Note: castingNotes and role are user-editable metadata stored in assignments,
          // not provided by the backend
        };
      });

      return {
        characters,
        screenplay_name: screenplayName,
        screenplay_json_path: jsonPath,
        total_lines: extractData.total_lines,
        default_lines: extractData.default_lines,
      };
    },
    enabled: !!jsonPathOrTaskId,
    staleTime: 5 * 60 * 1000, // Consider data stale after 5 minutes
    gcTime: 30 * 60 * 1000, // Keep in cache for 30 minutes
    retry: (failureCount, error) => {
      // Don't retry if it's a 404 (task not found)
      if (error instanceof Error && error.message.includes('404')) {
        return false;
      }
      return failureCount < 3;
    },
  });
}
