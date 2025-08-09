import { enableMapSet } from 'immer';
import { beforeEach, describe, expect, it } from 'vitest';

import useAppStore from '../appStore';

// Enable Map/Set support for immer (required for the store)
enableMapSet();

describe('Voice Casting Store', () => {
  beforeEach(() => {
    // Clear state before each test - use partial state update
    const store = useAppStore.getState();
    useAppStore.setState({
      ...store,
      sessions: new Map(),
      activeSessionId: undefined,
    });
  });

  describe('Session Management', () => {
    it('should create a new session', () => {
      const store = useAppStore.getState();

      store.selectOrCreateSession('test-session-1', {
        screenplayName: 'Test Screenplay',
        screenplayJsonPath: '/path/to/screenplay.json',
      });

      const session = store.getActiveSession();
      expect(session).toBeDefined();
      expect(session?.screenplayName).toBe('Test Screenplay');
      expect(session?.screenplayJsonPath).toBe('/path/to/screenplay.json');
    });

    it('should set active session', () => {
      const store = useAppStore.getState();

      store.selectOrCreateSession('test-session-1', {
        screenplayName: 'Test Screenplay',
      });

      // Verify via getActiveSession (activeSessionId not directly exposed)
      const activeSession = store.getActiveSession();
      expect(activeSession).toBeDefined();
      expect(activeSession?.sessionId).toBe('test-session-1');
      expect(activeSession?.screenplayName).toBe('Test Screenplay');
    });

    it('should switch between multiple sessions', () => {
      const store = useAppStore.getState();

      // Create two sessions
      store.selectOrCreateSession('session-1', {
        screenplayName: 'Screenplay 1',
      });

      store.selectOrCreateSession('session-2', {
        screenplayName: 'Screenplay 2',
      });

      // Switch between them
      store.selectOrCreateSession('session-1');
      expect(store.getActiveSession()?.screenplayName).toBe('Screenplay 1');

      store.selectOrCreateSession('session-2');
      expect(store.getActiveSession()?.screenplayName).toBe('Screenplay 2');
    });

    it('should delete a session', () => {
      const store = useAppStore.getState();

      store.selectOrCreateSession('test-session', {
        screenplayName: 'Test',
      });

      // Verify session exists
      expect(store.getActiveSession()?.sessionId).toBe('test-session');

      store.deleteSession('test-session');

      // After deleting active session, activeSessionId should be undefined
      expect(store.getActiveSession()).toBeUndefined();
    });

    it('should handle deleting active session', () => {
      const store = useAppStore.getState();

      store.selectOrCreateSession('test-session', {
        screenplayName: 'Test',
      });

      expect(store.getActiveSession()).toBeDefined();

      store.deleteSession('test-session');
      expect(store.getActiveSession()).toBeUndefined();
    });
  });

  describe('Character Voice Assignment', () => {
    beforeEach(() => {
      const store = useAppStore.getState();

      // Set up a test session with character data
      store.selectOrCreateSession('test-session', {
        screenplayName: 'Test Screenplay',
        screenplayData: {
          characters: new Map([
            [
              'John',
              {
                name: 'John',
                displayName: 'John',
                lineCount: 50,
                totalCharacters: 1000,
                longestDialogue: 200,
                isNarrator: false,
                role: 'protagonist',
                castingNotes: 'Young male voice',
              },
            ],
            [
              'Jane',
              {
                name: 'Jane',
                displayName: 'Jane',
                lineCount: 40,
                totalCharacters: 800,
                longestDialogue: 150,
                isNarrator: false,
                role: 'deuteragonist',
                castingNotes: 'Female voice, confident',
              },
            ],
          ]),
        },
      });
    });

    it('should assign voice to character', () => {
      const store = useAppStore.getState();

      store.setCharacterVoice('John', {
        provider: 'openai',
        sts_id: 'alloy',
      });

      const session = store.getActiveSession();
      expect(session?.assignments.has('John')).toBe(true);

      const assignment = session?.assignments.get('John');
      expect(assignment?.provider).toBe('openai');
      expect(assignment?.sts_id).toBe('alloy');
    });

    it('should update character metadata', () => {
      const store = useAppStore.getState();

      store.setCharacterVoice('Jane', {
        provider: 'elevenlabs',
        sts_id: 'voice-123',
      });

      store.setCharacterMetadata('Jane', {
        castingNotes: 'Updated casting notes',
        role: 'Updated role',
      });

      const session = store.getActiveSession();
      const assignment = session?.assignments.get('Jane');
      expect(assignment?.castingNotes).toBe('Updated casting notes');
      expect(assignment?.role).toBe('Updated role');
      expect(assignment?.provider).toBe('elevenlabs');
      expect(assignment?.sts_id).toBe('voice-123');
    });

    it('should remove character assignment', () => {
      const store = useAppStore.getState();

      store.setCharacterVoice('John', {
        provider: 'openai',
        sts_id: 'alloy',
      });

      expect(store.getActiveSession()?.assignments.has('John')).toBe(true);

      store.removeCharacterAssignment('John');
      expect(store.getActiveSession()?.assignments.has('John')).toBe(false);
    });

    it('should import assignments', () => {
      const store = useAppStore.getState();

      const assignments = new Map([
        [
          'John',
          {
            provider: 'openai',
            sts_id: 'alloy',
            castingNotes: 'Imported notes for John',
          },
        ],
        [
          'Jane',
          {
            provider: 'elevenlabs',
            sts_id: 'voice-456',
            castingNotes: 'Imported notes for Jane',
          },
        ],
      ]);

      store.importAssignments(assignments);

      const session = store.getActiveSession();
      expect(session?.assignments.size).toBe(2);
      expect(session?.assignments.get('John')?.provider).toBe('openai');
      expect(session?.assignments.get('Jane')?.provider).toBe('elevenlabs');
    });
  });

  describe('Casting Method and Content', () => {
    beforeEach(() => {
      const store = useAppStore.getState();
      store.selectOrCreateSession('test-session', {
        screenplayName: 'Test',
      });
    });

    it('should set casting method', () => {
      const store = useAppStore.getState();

      store.setCastingMethod('llm-assisted');
      expect(store.getActiveSession()?.castingMethod).toBe('llm-assisted');

      store.setCastingMethod('manual');
      expect(store.getActiveSession()?.castingMethod).toBe('manual');
    });

    it('should set YAML content', () => {
      const store = useAppStore.getState();

      const yamlContent = 'character1:\n  provider: openai\n  sts_id: alloy';
      store.setYamlContent(yamlContent);

      expect(store.getActiveSession()?.yamlContent).toBe(yamlContent);
    });

    it('should add to voice cache', () => {
      const store = useAppStore.getState();

      const voiceEntry = {
        sts_id: 'test-voice',
        provider: 'openai',
        config: { voice: 'alloy' },
        description: { custom_description: 'Test Voice' },
      };

      store.addToVoiceCache('openai', 'test-voice', voiceEntry);

      const session = store.getActiveSession();
      expect(session?.voiceCache.has('openai:test-voice')).toBe(true);
      expect(session?.voiceCache.get('openai:test-voice')).toEqual(voiceEntry);
    });
  });

  describe('Session Statistics', () => {
    beforeEach(() => {
      const store = useAppStore.getState();

      store.selectOrCreateSession('test-session', {
        screenplayName: 'Test Screenplay',
        screenplayData: {
          characters: new Map([
            [
              'John',
              {
                name: 'John',
                displayName: 'John',
                lineCount: 50,
                totalCharacters: 1000,
                longestDialogue: 200,
                isNarrator: false,
              },
            ],
            [
              'Jane',
              {
                name: 'Jane',
                displayName: 'Jane',
                lineCount: 40,
                totalCharacters: 800,
                longestDialogue: 150,
                isNarrator: false,
              },
            ],
          ]),
        },
      });

      // Assign one voice
      store.setCharacterVoice('John', {
        provider: 'openai',
        sts_id: 'alloy',
      });
    });

    it('should calculate session statistics', () => {
      const store = useAppStore.getState();

      const stats = store.getSessionStats('test-session');
      expect(stats).toBeDefined();
      expect(stats?.sessionId).toBe('test-session');
      expect(stats?.screenplayName).toBe('Test Screenplay');
      expect(stats?.total).toBe(2);
      expect(stats?.assigned).toBe(1);
      expect(stats?.completed).toBe(false);
    });

    it('should detect completed sessions', () => {
      const store = useAppStore.getState();

      // Assign second voice
      store.setCharacterVoice('Jane', {
        provider: 'elevenlabs',
        sts_id: 'voice-123',
      });

      const stats = store.getSessionStats('test-session');
      expect(stats?.assigned).toBe(2);
      expect(stats?.completed).toBe(true);
    });
  });

  describe('Error Handling', () => {
    it('should handle invalid sessionId gracefully', () => {
      const store = useAppStore.getState();

      // Should not throw error - creates session with minimal data
      store.selectOrCreateSession('non-existent', {
        screenplayName: 'Test Session',
      });
      expect(store.getActiveSession()).toBeDefined();
      expect(store.getActiveSession()?.sessionId).toBe('non-existent');
    });

    it('should handle operations on null active session', () => {
      const store = useAppStore.getState();

      // Reset to no active session
      store.resetCastingState();
      expect(store.getActiveSession()).toBeUndefined();

      // These operations should throw errors when no active session
      expect(() => {
        store.setCharacterVoice('John', {
          provider: 'openai',
          sts_id: 'alloy',
        });
      }).toThrow('No active session to update');

      expect(() => {
        store.removeCharacterAssignment('John');
      }).toThrow('No active session to update');
    });
  });

  describe('Recent Sessions', () => {
    it('should return recent sessions sorted by last updated', async () => {
      const store = useAppStore.getState();

      // Create first session
      store.selectOrCreateSession('session-1', {
        screenplayName: 'First',
      });

      // Wait a bit to ensure different timestamps
      await new Promise((resolve) => setTimeout(resolve, 10));

      // Create second session
      store.selectOrCreateSession('session-2', {
        screenplayName: 'Second',
      });

      const recentSessions = store.getRecentSessions(5);
      expect(recentSessions).toHaveLength(2);
      expect(recentSessions[0]?.screenplayName).toBe('Second'); // Most recent
      expect(recentSessions[1]?.screenplayName).toBe('First');
    });
  });

  describe('State Reset', () => {
    it('should reset casting state', () => {
      const store = useAppStore.getState();

      store.selectOrCreateSession('test-session', {
        screenplayName: 'Test',
      });

      expect(store.getActiveSession()).toBeDefined();

      store.resetCastingState();
      expect(store.getActiveSession()).toBeUndefined();
    });
  });
});
