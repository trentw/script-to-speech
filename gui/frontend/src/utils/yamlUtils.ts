import { apiService } from '@/services/api';
import type { VoiceAssignment as StoreVoiceAssignment } from '@/stores/appStore';
import type {
  CharacterInfo,
  VoiceAssignment as ApiVoiceAssignment,
} from '@/types/voice-casting';

/**
 * Centralized YAML utilities for voice casting
 */
export const yamlUtils = {
  /**
   * Convert assignments Map from store to YAML string
   * @param assignments Map from voice casting store
   * @param characterInfo Character information for comments
   * @returns Promise<string> YAML content
   */
  assignmentsToYaml: async (
    assignments: Map<string, StoreVoiceAssignment>,
    characterInfo: CharacterInfo[]
  ): Promise<string> => {
    // Convert Map to Record for API (no transformation needed, just different structure)
    const assignmentsRecord: Record<string, ApiVoiceAssignment> = {};
    const characterInfoRecord: Record<string, CharacterInfo> = {};

    // Convert assignments Map to Record and fix field name mappings
    for (const [characterName, assignment] of assignments) {
      assignmentsRecord[characterName] = {
        character: characterName,
        provider: assignment.provider,
        sts_id: assignment.sts_id, // Optional - only for library voices
        provider_config: assignment.provider_config,
        casting_notes: assignment.castingNotes,
        role: assignment.role,
        additional_notes: assignment.additional_notes,
        line_count: assignment.line_count,
        total_characters: assignment.total_characters,
        longest_dialogue: assignment.longest_dialogue,
      };
    }

    // Convert characterInfo Array to Record and fix field name mappings
    for (const info of characterInfo) {
      characterInfoRecord[info.name] = {
        name: info.name,
        line_count: info.lineCount,
        total_characters: info.totalCharacters,
        longest_dialogue: info.longestDialogue,
        casting_notes: info.casting_notes,
        role: info.role,
      };
    }

    // Call backend generateYaml API with Record format
    const response = await apiService.generateYaml({
      assignments: assignmentsRecord,
      character_info: characterInfoRecord,
      include_comments: true,
    });

    if (response.error) {
      const errorMessage =
        typeof response.error === 'string'
          ? response.error
          : JSON.stringify(response.error);
      throw new Error(errorMessage);
    }

    return response.data!.yaml_content;
  },

  /**
   * Parse YAML string to assignments Map for store
   * @param yamlContent YAML configuration content
   * @returns Promise<Map<string, StoreVoiceAssignment>> assignments Map
   */
  yamlToAssignments: async (
    yamlContent: string
  ): Promise<Map<string, StoreVoiceAssignment>> => {
    // Call backend parseYaml API
    const response = await apiService.parseYaml({ yamlContent });

    if (response.error) {
      const errorMessage =
        typeof response.error === 'string'
          ? response.error
          : JSON.stringify(response.error);
      throw new Error(errorMessage);
    }

    const result = response.data!;

    if (result.has_errors) {
      throw new Error(`YAML parsing failed: ${result.errors.join(', ')}`);
    }

    // Convert API response to store format
    const assignments = new Map<string, StoreVoiceAssignment>();

    result.assignments.forEach((assignment) => {
      // Extract sts_id from assignment
      const sts_id = assignment.sts_id;

      const storeAssignment: StoreVoiceAssignment = {
        sts_id, // Use the resolved sts_id
        provider: assignment.provider,
        provider_config: assignment.provider_config,
        castingNotes: assignment.casting_notes,
        role: assignment.role,
        additional_notes: assignment.additional_notes,
        line_count: assignment.line_count,
        total_characters: assignment.total_characters,
        longest_dialogue: assignment.longest_dialogue,
        voiceEntry: sts_id
          ? {
              sts_id: sts_id,
              provider: assignment.provider,
              config: assignment.provider_config || {},
            }
          : undefined,
      };

      assignments.set(assignment.character, storeAssignment);
    });

    return assignments;
  },

  /**
   * Export screenplay character data to YAML format when no assignments exist
   * @param screenplayJsonPath Path to screenplay JSON file
   * @returns Promise<string> YAML content with empty assignments for LLM filling
   */
  charactersToYaml: async (screenplayJsonPath: string): Promise<string> => {
    // Extract characters from the screenplay
    const extractResponse =
      await apiService.extractCharacters(screenplayJsonPath);
    if (extractResponse.error) {
      throw new Error(`Failed to extract characters: ${extractResponse.error}`);
    }

    const charactersData = extractResponse.data!;

    let yamlContent = '# Voice configuration for speakers\n';
    yamlContent +=
      '# Each speaker requires provider and either sts_id (for library voices) or provider-specific fields\n';
    yamlContent += '# Generated from screenplay character data\n\n';

    // Create YAML entries for each character with empty provider/sts_id for LLM to fill
    for (const character of charactersData.characters) {
      yamlContent += `# ${character.name}: ${character.line_count} lines\n`;
      yamlContent += `# Total characters: ${character.total_characters}, Longest dialogue: ${character.longest_dialogue} characters\n`;

      if (character.casting_notes) {
        yamlContent += `# Casting notes: ${character.casting_notes}\n`;
      }
      if (character.role) {
        yamlContent += `# Role: ${character.role}\n`;
      }

      // Quote character names with spaces or special characters
      const quotedName =
        character.name.includes(' ') || character.name.includes('#')
          ? `"${character.name}"`
          : character.name;

      yamlContent += `${quotedName}:\n`;
      yamlContent += `  provider: # TO BE FILLED BY LLM (e.g., openai, elevenlabs, cartesia)\n`;
      yamlContent += `  sts_id: # TO BE FILLED BY LLM (for library voices) OR omit and add provider-specific fields below\n`;
      yamlContent += `  # For custom voices, add provider-specific fields instead of sts_id\n`;
      yamlContent += `  # e.g., voice_id: custom_voice_id (for elevenlabs/cartesia)\n\n`;
    }

    return yamlContent;
  },
};
