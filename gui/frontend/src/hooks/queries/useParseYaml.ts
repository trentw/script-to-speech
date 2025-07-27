import { useQuery } from '@tanstack/react-query';

import { apiService } from '@/services/api';
import type { VoiceAssignment } from '@/stores/appStore';
import type { VoiceEntry } from '@/types';

interface ParsedYamlResponse {
  assignments: Record<
    string,
    {
      voice_id: string;
      provider: string;
      config?: Record<string, unknown>;
    }
  >;
  screenplay_name?: string;
  metadata?: Record<string, unknown>;
}

interface ParseYamlRequest {
  yaml_content: string;
}

/**
 * Hook to parse YAML content and extract voice assignments
 */
export function useParseYaml(yamlContent: string | undefined) {
  return useQuery({
    queryKey: ['parse-yaml', yamlContent],
    queryFn: async () => {
      if (!yamlContent) {
        throw new Error('YAML content is required');
      }

      const request: ParseYamlRequest = {
        yaml_content: yamlContent,
      };

      // POST to parse endpoint (you may need to add this to your backend)
      const response = await fetch('/api/screenplay/parse-yaml', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        throw new Error('Failed to parse YAML');
      }

      const data = (await response.json()) as ParsedYamlResponse;

      // Convert parsed assignments to Map<string, VoiceAssignment>
      const assignmentsMap = new Map<string, VoiceAssignment>();

      for (const [character, assignment] of Object.entries(data.assignments)) {
        // Optionally fetch voice details
        let voiceEntry: VoiceEntry | undefined;

        try {
          // Try to fetch voice details from library
          const voiceResponse = await apiService.getVoiceDetails(
            assignment.provider,
            assignment.voice_id
          );

          if (voiceResponse.data) {
            voiceEntry = voiceResponse.data;
          }
        } catch {
          // Voice not found in library, that's okay
          console.warn(`Voice ${assignment.voice_id} not found in library`);
        }

        assignmentsMap.set(character, {
          voiceId: assignment.voice_id,
          provider: assignment.provider,
          voiceEntry,
          confidence: 1.0, // Imported assignments have full confidence
          reasoning: 'Imported from YAML configuration',
        });
      }

      return {
        assignments: assignmentsMap,
        screenplay_name: data.screenplay_name,
        metadata: data.metadata,
      };
    },
    enabled: !!yamlContent && yamlContent.trim().length > 0,
    staleTime: 5 * 60 * 1000, // Consider data stale after 5 minutes
    gcTime: 30 * 60 * 1000, // Keep in cache for 30 minutes
    retry: false, // Don't retry parse errors
  });
}
