import { apiService } from '@/services/api';
import type { CharacterInfo, VoiceAssignment as ApiVoiceAssignment } from '@/types/voice-casting';
import type { VoiceAssignment as StoreVoiceAssignment } from '@/stores/appStore';

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
    // Convert Map to array of assignments for API
    const assignmentsArray: ApiVoiceAssignment[] = [];
    
    for (const [characterName, assignment] of assignments) {
      assignmentsArray.push({
        character: characterName,
        provider: assignment.provider,
        sts_id: assignment.sts_id,
        casting_notes: assignment.castingNotes,
        role: assignment.role,
        additional_notes: assignment.additional_notes,
        line_count: assignment.line_count,
        total_characters: assignment.total_characters,
        longest_dialogue: assignment.longest_dialogue,
      });
    }
    
    // Call backend generateYaml API
    const response = await apiService.generateYaml({
      assignments: assignmentsArray,
      character_info: characterInfo,
      include_comments: true,
    });
    
    if (response.error) {
      const errorMessage = typeof response.error === 'string' 
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
  yamlToAssignments: async (yamlContent: string): Promise<Map<string, StoreVoiceAssignment>> => {
    // Call backend parseYaml API
    const response = await apiService.parseYaml({ yamlContent });
    
    if (response.error) {
      const errorMessage = typeof response.error === 'string' 
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
    
    result.assignments.forEach(assignment => {
      assignments.set(assignment.character, {
        sts_id: assignment.sts_id,
        provider: assignment.provider,
        castingNotes: assignment.casting_notes,
        role: assignment.role,
        additional_notes: assignment.additional_notes,
        line_count: assignment.line_count,
        total_characters: assignment.total_characters,
        longest_dialogue: assignment.longest_dialogue,
        voiceEntry: {
          sts_id: assignment.sts_id,
          provider: assignment.provider,
          config: assignment.provider_config || {},
          // Add other VoiceEntry fields if needed
        },
      });
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
    const extractResponse = await apiService.extractCharacters(screenplayJsonPath);
    if (extractResponse.error) {
      throw new Error(`Failed to extract characters: ${extractResponse.error}`);
    }

    const charactersData = extractResponse.data!;
    
    let yamlContent = '# Voice configuration for speakers\n';
    yamlContent += '# Each speaker requires provider and sts_id fields\n';
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
      const quotedName = character.name.includes(' ') || character.name.includes('#') 
        ? `"${character.name}"` 
        : character.name;
      
      yamlContent += `${quotedName}:\n`;
      yamlContent += `  provider: # TO BE FILLED BY LLM\n`;
      yamlContent += `  sts_id: # TO BE FILLED BY LLM\n\n`;
    }

    return yamlContent;
  },
};