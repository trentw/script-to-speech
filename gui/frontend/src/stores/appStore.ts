import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { persist } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';
import { useShallow } from 'zustand/react/shallow';

import type { ScreenplayResult, VoiceEntry } from '../types';
import { createSuperJSONStorage } from '../utils/superJSONStorage';

// Type for configuration values matching VoiceEntry config structure
type ConfigValue = string | number | boolean | string[];
type Config = Record<string, ConfigValue>;

// Voice Casting Types
export interface CharacterInfo {
  name: string;
  lineCount: number;
  firstAppearance?: number;
  totalCharacters?: number;
  longestDialogue?: number;
  isNarrator?: boolean;
  description?: string;
  notes?: string;
}

export interface VoiceAssignment {
  sts_id?: string; // Present = library voice, absent = custom voice
  provider: string;
  provider_config?: Record<string, unknown>; // Provider-specific configuration
  voiceEntry?: VoiceEntry;
  confidence?: number;
  reasoning?: string;
  castingNotes?: string;
  role?: string;
  additional_notes?: string[]; // New field for arbitrary comments
  // Parsed metadata (not stored in YAML)
  line_count?: number;
  total_characters?: number;
  longest_dialogue?: number;
}

// Voice Casting Session Data - for multi-session support
export interface VoiceCastingSessionData {
  sessionId: string;
  screenplayName: string;
  screenplayJsonPath: string;
  assignments: Map<string, VoiceAssignment>;
  castingMethod: 'manual' | 'llm-assisted';
  yamlContent: string;
  voiceCache: Map<string, VoiceEntry>;
  lastUpdated: number;
  screenplayData?: { characters: Map<string, CharacterInfo> };
  yaml_version_id?: number; // Add version tracking for optimistic locking
}

// Configuration slice - handles TTS provider/voice settings
interface ConfigurationSlice {
  selectedProvider: string | undefined;
  selectedVoice: VoiceEntry | undefined;
  currentConfig: Config;

  // Actions
  setSelectedProvider: (provider: string | undefined) => void;
  setSelectedVoice: (voice: VoiceEntry | undefined) => void;
  setCurrentConfig: (config: Config) => void;
  setConfiguration: (
    provider: string,
    voice: VoiceEntry | undefined,
    config: Config
  ) => void;
  resetConfiguration: () => void;
}

// User Input slice - handles text input for TTS generation
interface UserInputSlice {
  text: string;

  // Actions
  setText: (text: string) => void;
  clearText: () => void;
}

// UI slice - handles UI state like errors, loading indicators
interface UISlice {
  error: string | undefined;

  // Actions
  setError: (error: string | undefined) => void;
  clearError: () => void;
}

// Layout slice - handles responsive layout state
interface LayoutSlice {
  viewportSize: 'mobile' | 'tablet' | 'desktop';
  sidebarExpanded: boolean;
  rightPanelExpanded: boolean;
  activeModal: 'settings' | 'history' | null;

  // Actions
  setViewportSize: (size: 'mobile' | 'tablet' | 'desktop') => void;
  setSidebarExpanded: (expanded: boolean) => void;
  toggleSidebar: () => void;
  setRightPanelExpanded: (expanded: boolean) => void;
  toggleRightPanel: () => void;
  setActiveModal: (modal: 'settings' | 'history' | null) => void;
  closeModal: () => void;
}

// Screenplay slice - handles screenplay parsing state
interface ScreenplaySlice {
  currentTaskId: string | undefined;
  selectedScreenplay: ScreenplayResult | undefined;
  viewMode: 'upload' | 'status' | 'result';

  // Actions
  setCurrentTaskId: (taskId: string | undefined) => void;
  setSelectedScreenplay: (screenplay: ScreenplayResult | undefined) => void;
  setViewMode: (mode: 'upload' | 'status' | 'result') => void;
  resetScreenplayState: () => void;
}

// Voice Casting slice - SINGLE SOURCE OF TRUTH
interface VoiceCastingSlice {
  // Data
  sessions: Map<string, VoiceCastingSessionData>;
  activeSessionId: string | undefined;

  // Core helper - all mutations go through this
  updateActiveSession: (
    updater: (session: VoiceCastingSessionData) => void
  ) => void;

  // Session management - CONSOLIDATED API
  deleteSession: (sessionId: string) => void;
  selectOrCreateSession: (
    sessionId: string,
    sessionData?: Partial<VoiceCastingSessionData>
  ) => void;
  resetCastingState: () => void;

  // Character operations
  setCharacterVoice: (character: string, voice: VoiceAssignment) => void;
  setCharacterMetadata: (
    character: string,
    metadata: Partial<VoiceAssignment>
  ) => void;
  removeCharacterAssignment: (character: string) => void;
  removeVoiceFromAssignment: (character: string) => void;
  importAssignments: (assignments: Map<string, VoiceAssignment>) => void;
  setYamlContent: (content: string) => void;
  setCastingMethod: (method: 'manual' | 'llm-assisted') => void;
  addToVoiceCache: (
    provider: string,
    sts_id: string,
    voice: VoiceEntry
  ) => void;
  updateVersionId: (versionId: number) => void;

  // Computed getters
  getActiveSession: () => VoiceCastingSessionData | undefined;
  getSessionStats: (sessionId: string) => SessionStats | undefined;
  getRecentSessions: (limit?: number) => VoiceCastingSessionData[];
}

// Add this type if not present
interface SessionStats {
  sessionId: string;
  screenplayName: string;
  total: number;
  assigned: number;
  completed: boolean;
  lastUpdated: number;
}

// Combined store type
type AppStore = ConfigurationSlice &
  UserInputSlice &
  UISlice &
  LayoutSlice &
  ScreenplaySlice &
  VoiceCastingSlice;

// Create the store with domain slices
const useAppStore = create<AppStore>()(
  devtools(
    persist(
      immer((set, get) => ({
        // Configuration slice implementation
        selectedProvider: undefined,
        selectedVoice: undefined,
        currentConfig: {},

        setSelectedProvider: (provider) => {
          set(
            { selectedProvider: provider },
            false,
            'configuration/setSelectedProvider'
          );
        },

        setSelectedVoice: (voice) => {
          set(
            { selectedVoice: voice },
            false,
            'configuration/setSelectedVoice'
          );
        },

        setCurrentConfig: (config) => {
          set(
            { currentConfig: config },
            false,
            'configuration/setCurrentConfig'
          );
        },

        setConfiguration: (provider, voice, config) => {
          set(
            {
              selectedProvider: provider,
              selectedVoice: voice,
              currentConfig: config,
            },
            false,
            'configuration/setConfiguration'
          );
        },

        resetConfiguration: () => {
          set(
            {
              selectedProvider: undefined,
              selectedVoice: undefined,
              currentConfig: {},
            },
            false,
            'configuration/reset'
          );
        },

        // User Input slice implementation
        text: '',

        setText: (text) => {
          set({ text }, false, 'userInput/setText');
        },

        clearText: () => {
          set({ text: '' }, false, 'userInput/clearText');
        },

        // UI slice implementation
        error: undefined,

        setError: (error) => {
          set({ error }, false, 'ui/setError');
        },

        clearError: () => {
          set({ error: undefined }, false, 'ui/clearError');
        },

        // Layout slice implementation
        viewportSize: 'desktop',
        sidebarExpanded: true,
        rightPanelExpanded: true,
        activeModal: null,

        setViewportSize: (size) => {
          set({ viewportSize: size }, false, 'layout/setViewportSize');
        },

        setSidebarExpanded: (expanded) => {
          set(
            { sidebarExpanded: expanded },
            false,
            'layout/setSidebarExpanded'
          );
        },

        toggleSidebar: () => {
          set(
            (state) => ({ sidebarExpanded: !state.sidebarExpanded }),
            false,
            'layout/toggleSidebar'
          );
        },

        setRightPanelExpanded: (expanded) => {
          set(
            { rightPanelExpanded: expanded },
            false,
            'layout/setRightPanelExpanded'
          );
        },

        toggleRightPanel: () => {
          set(
            (state) => ({ rightPanelExpanded: !state.rightPanelExpanded }),
            false,
            'layout/toggleRightPanel'
          );
        },

        setActiveModal: (modal) => {
          set({ activeModal: modal }, false, 'layout/setActiveModal');
        },

        closeModal: () => {
          set({ activeModal: null }, false, 'layout/closeModal');
        },

        // Screenplay slice implementation
        currentTaskId: undefined,
        selectedScreenplay: undefined,
        viewMode: 'upload',

        setCurrentTaskId: (taskId) => {
          set({ currentTaskId: taskId }, false, 'screenplay/setCurrentTaskId');
        },

        setSelectedScreenplay: (screenplay) => {
          set(
            { selectedScreenplay: screenplay },
            false,
            'screenplay/setSelectedScreenplay'
          );
        },

        setViewMode: (mode) => {
          set({ viewMode: mode }, false, 'screenplay/setViewMode');
        },

        resetScreenplayState: () => {
          set(
            {
              currentTaskId: undefined,
              selectedScreenplay: undefined,
              viewMode: 'upload',
            },
            false,
            'screenplay/reset'
          );
        },

        // Voice Casting slice implementation - SINGLE SOURCE OF TRUTH
        sessions: new Map(),
        activeSessionId: undefined,

        // Core helper - all mutations go through this
        updateActiveSession: (updater) => {
          const state = get();
          if (
            !state.activeSessionId ||
            !state.sessions.has(state.activeSessionId)
          ) {
            throw new Error(
              '[Voice Casting] No active session to update. Please select or create a session first.'
            );
          }
          set(
            (draft) => {
              const session = draft.sessions.get(draft.activeSessionId!)!;
              updater(session);
              session.lastUpdated = Date.now();
            },
            false,
            'voiceCasting/updateActiveSession'
          );
        },

        // Session management - CONSOLIDATED API

        deleteSession: (sessionId) => {
          set(
            (draft) => {
              draft.sessions.delete(sessionId);
              if (draft.activeSessionId === sessionId) {
                draft.activeSessionId = undefined;
              }
            },
            false,
            'voiceCasting/deleteSession'
          );
        },

        // Consolidated session selection - creates if needed and sets as active
        selectOrCreateSession: (sessionId, sessionData) => {
          set(
            (draft) => {
              const existing = draft.sessions.get(sessionId);
              
              if (existing && sessionData) {
                // Update existing session, preserving user-modified data
                // Assignments are the source of truth for user data (voices, metadata)
                console.log('[Store] Updating existing session:', {
                  sessionId,
                  existingAssignments: Array.from(existing.assignments.entries()),
                  incomingData: sessionData,
                });
                Object.assign(existing, {
                  screenplayName: sessionData.screenplayName || existing.screenplayName,
                  screenplayJsonPath: sessionData.screenplayJsonPath || existing.screenplayJsonPath,
                  screenplayData: sessionData.screenplayData || existing.screenplayData,
                  // Use incoming assignments if provided, otherwise preserve existing
                  assignments: sessionData.assignments || existing.assignments,
                  // Preserve other user data
                  castingMethod: sessionData.castingMethod || existing.castingMethod,
                  yamlContent: sessionData.yamlContent || existing.yamlContent,
                  voiceCache: sessionData.voiceCache || existing.voiceCache,
                  yaml_version_id: sessionData.yaml_version_id || existing.yaml_version_id || 1,
                  lastUpdated: Date.now(),
                });
              } else if (!existing && sessionData) {
                // Create new session
                console.log('[Store] Creating new session:', {
                  sessionId,
                  incomingAssignments: sessionData.assignments ? 
                    Array.from(sessionData.assignments.entries()) : [],
                });
                const newSession: VoiceCastingSessionData = {
                  sessionId,
                  screenplayName: sessionData.screenplayName || '',
                  screenplayJsonPath: sessionData.screenplayJsonPath || '',
                  assignments: sessionData.assignments || new Map(),
                  castingMethod: sessionData.castingMethod || 'manual',
                  yamlContent: sessionData.yamlContent || '',
                  voiceCache: sessionData.voiceCache || new Map(),
                  yaml_version_id: sessionData.yaml_version_id || 1,
                  lastUpdated: Date.now(),
                  screenplayData: sessionData.screenplayData,
                };
                draft.sessions.set(sessionId, newSession);
              } else if (existing && !sessionData) {
                console.log('[Store] Selecting existing session without update:', {
                  sessionId,
                  existingAssignments: Array.from(existing.assignments.entries()),
                });
              }
              // Set as active
              draft.activeSessionId = sessionId;
            },
            false,
            'voiceCasting/selectOrCreateSession'
          );
        },

        // Character operations - all use updateActiveSession helper
        setCharacterVoice: async (character, voice) => {
          const session = get().getActiveSession();
          if (!session) return;

          // Optimistically update local state
          get().updateActiveSession((session) => {
            const existing = session.assignments.get(character);
            const updated = {
              ...existing, // Preserve metadata
              ...voice, // Update voice data
            };
            session.assignments.set(character, updated);
          });

          // Call API to update YAML on backend
          if (session.sessionId) {
            const { apiService } = await import('@/services/api');
            const existing = session.assignments.get(character);
            const updated = {
              ...existing,
              ...voice,
            };
            
            const result = await apiService.updateCharacterAssignment(
              session.sessionId,
              character,
              { character, ...updated },  // Add character field for API
              session.yaml_version_id || 0
            );

            if (result.data) {
              // Update session with new data from backend
              get().updateActiveSession((session) => {
                session.yamlContent = result.data.session.yamlContent;
                session.yaml_version_id = result.data.session.yaml_version_id;
              });
            } else if (result.error) {
              // Revert on error
              console.error('Failed to update character assignment:', result.error);
              get().updateActiveSession((session) => {
                if (existing) {
                  session.assignments.set(character, existing);
                } else {
                  session.assignments.delete(character);
                }
              });
            }
          }
        },

        setCharacterMetadata: async (character, metadata) => {
          const session = get().getActiveSession();
          if (!session) return;

          // Optimistically update local state
          get().updateActiveSession((session) => {
            const existing = session.assignments.get(character) || {
              provider: '',
            };
            const updated = { ...existing, ...metadata };
            session.assignments.set(character, updated);
          });

          // Call API to update YAML on backend
          if (session.sessionId) {
            const { apiService } = await import('@/services/api');
            const existing = session.assignments.get(character) || { provider: '' };
            const updated = { ...existing, ...metadata };
            
            const result = await apiService.updateCharacterAssignment(
              session.sessionId,
              character,
              { character, ...updated },  // Add character field for API
              session.yaml_version_id || 0
            );

            if (result.data) {
              // Update session with new data from backend
              get().updateActiveSession((session) => {
                session.yamlContent = result.data.session.yamlContent;
                session.yaml_version_id = result.data.session.yaml_version_id;
              });
            } else if (result.error) {
              // Revert on error
              console.error('Failed to update character metadata:', result.error);
              get().updateActiveSession((session) => {
                if (existing.provider) {
                  session.assignments.set(character, existing);
                } else {
                  session.assignments.delete(character);
                }
              });
            }
          }
        },

        removeCharacterAssignment: async (character) => {
          const session = get().getActiveSession();
          if (!session) return;

          // Store old value for potential revert
          const oldValue = session.assignments.get(character);

          // Optimistically update local state
          get().updateActiveSession((session) => {
            session.assignments.delete(character);
          });

          // Call API to update YAML on backend
          if (session.sessionId) {
            const { apiService } = await import('@/services/api');
            
            // Send empty assignment to remove from YAML
            const result = await apiService.updateCharacterAssignment(
              session.sessionId,
              character,
              { character, provider: '' }, // Empty assignment with character field to remove
              session.yaml_version_id || 0
            );

            if (result.data) {
              // Update session with new data from backend
              get().updateActiveSession((session) => {
                session.yamlContent = result.data.session.yamlContent;
                session.yaml_version_id = result.data.session.yaml_version_id;
              });
            } else if (result.error) {
              // Revert on error
              console.error('Failed to remove character assignment:', result.error);
              if (oldValue) {
                get().updateActiveSession((session) => {
                  session.assignments.set(character, oldValue);
                });
              }
            }
          }
        },
        removeVoiceFromAssignment: (character) => {
          get().updateActiveSession((session) => {
            const existing = session.assignments.get(character);
            if (existing) {
              // Keep metadata, clear voice data
              session.assignments.set(character, {
                provider: '',
                sts_id: undefined,
                provider_config: undefined,
                role: existing.role,
                castingNotes: existing.castingNotes,
                additional_notes: existing.additional_notes,
              });
            }
          });
        },

        importAssignments: (assignments) => {
          console.log('[Store] Importing assignments:', Array.from(assignments.entries()));
          get().updateActiveSession((session) => {
            session.assignments = assignments;
            console.log('[Store] Assignments after import:', Array.from(session.assignments.entries()));
          });
        },

        setYamlContent: (content) => {
          get().updateActiveSession((session) => {
            session.yamlContent = content;
          });
        },

        setCastingMethod: (method) => {
          get().updateActiveSession((session) => {
            session.castingMethod = method;
          });
        },

        addToVoiceCache: (provider, sts_id, voice) => {
          get().updateActiveSession((session) => {
            const cacheKey = `${provider}:${sts_id}`;
            session.voiceCache.set(cacheKey, voice);
          });
        },

        updateVersionId: (versionId) => {
          get().updateActiveSession((session) => {
            session.yaml_version_id = versionId;
          });
        },

        // Computed getters
        getActiveSession: () => {
          const state = get();
          if (!state.activeSessionId) return undefined;
          return state.sessions.get(state.activeSessionId);
        },

        getSessionStats: (sessionId) => {
          const state = get();
          const session = state.sessions.get(sessionId);
          if (!session) return undefined;

          const total = session.screenplayData?.characters.size || 0;
          // Count only assignments with actual voices (provider and sts_id or provider_config)
          const assigned = Array.from(session.assignments.values()).filter(
            (a) => a.provider && (a.sts_id || a.provider_config)
          ).length;
          return {
            sessionId,
            screenplayName: session.screenplayName,
            total,
            assigned,
            completed: total > 0 && assigned >= total,
            lastUpdated: session.lastUpdated,
          };
        },

        getRecentSessions: (limit = 10) => {
          const state = get();
          const sessions = Array.from(state.sessions.values());
          return sessions
            .sort((a, b) => b.lastUpdated - a.lastUpdated)
            .slice(0, limit);
        },

        // State reset - clears active session
        resetCastingState: () => {
          set(
            (draft) => {
              draft.activeSessionId = undefined;
            },
            false,
            'voiceCasting/resetCastingState'
          );
        },
      })),
      {
        name: 'sts-app-store-v3', // New key to avoid old data conflicts
        storage: createSuperJSONStorage<AppStore>(), // Use superjson for Map serialization
        
        // Selective persistence - only persist user preferences and voice-casting data
        partialize: (state) => ({
          // User preferences
          selectedProvider: state.selectedProvider,
          selectedVoice: state.selectedVoice,
          currentConfig: state.currentConfig,
          sidebarExpanded: state.sidebarExpanded,
          rightPanelExpanded: state.rightPanelExpanded,

          // Voice-casting sessions - already a plain Map since partialize runs after immer
          // Superjson handles Map serialization directly
          sessions: state.sessions,
          activeSessionId: state.activeSessionId,

          // text, error, viewportSize, activeModal are NOT persisted (ephemeral state)
        }),

        // Rehydration handler - just handle cleanup, no conversion needed!
        onRehydrateStorage: () => (state, error) => {
          if (error) {
            console.error('[Voice Casting] Hydration error:', error);
            return;
          }

          if (state && state.sessions) {
            console.log(
              `[Voice Casting] Loaded ${state.sessions.size} sessions from storage`
            );
            // Log the actual assignments for each session
            state.sessions.forEach((session, id) => {
              console.log(`[Voice Casting] Session ${id} assignments:`, 
                Array.from(session.assignments.entries()));
            });
            
            // Clean old sessions on startup
            const now = Date.now();
            const twelveHours = 12 * 60 * 60 * 1000;
            const maxSessions = 10;

            const sortedSessions = Array.from(state.sessions.entries())
              .sort((a, b) => b[1].lastUpdated - a[1].lastUpdated);

            // Keep only recent sessions (< 12 hours) and limit to 10
            state.sessions = new Map(
              sortedSessions
                .filter(([_, session], index) => 
                  now - session.lastUpdated < twelveHours && index < maxSessions
                )
            );
            
            console.log(
              `[Voice Casting] After cleanup: ${state.sessions.size} sessions`
            );

            // Validate active session still exists
            if (state.activeSessionId && !state.sessions.has(state.activeSessionId)) {
              state.activeSessionId = undefined;
            }
          }
        },
      }
    ),
    {
      name: 'sts-app-store',
    }
  )
);

// Selectors using useShallow for optimized re-renders
export const useConfiguration = () =>
  useAppStore(
    useShallow((state) => ({
      selectedProvider: state.selectedProvider,
      selectedVoice: state.selectedVoice,
      currentConfig: state.currentConfig,
      setSelectedProvider: state.setSelectedProvider,
      setSelectedVoice: state.setSelectedVoice,
      setCurrentConfig: state.setCurrentConfig,
      setConfiguration: state.setConfiguration,
      resetConfiguration: state.resetConfiguration,
    }))
  );

export const useUserInput = () =>
  useAppStore(
    useShallow((state) => ({
      text: state.text,
      setText: state.setText,
      clearText: state.clearText,
    }))
  );

export const useUIState = () =>
  useAppStore(
    useShallow((state) => ({
      error: state.error,
      setError: state.setError,
      clearError: state.clearError,
    }))
  );

export const useLayout = () =>
  useAppStore(
    useShallow((state) => ({
      viewportSize: state.viewportSize,
      sidebarExpanded: state.sidebarExpanded,
      rightPanelExpanded: state.rightPanelExpanded,
      activeModal: state.activeModal,
      setViewportSize: state.setViewportSize,
      setSidebarExpanded: state.setSidebarExpanded,
      toggleSidebar: state.toggleSidebar,
      setRightPanelExpanded: state.setRightPanelExpanded,
      toggleRightPanel: state.toggleRightPanel,
      setActiveModal: state.setActiveModal,
      closeModal: state.closeModal,
    }))
  );

export const useScreenplay = () =>
  useAppStore(
    useShallow((state) => ({
      currentTaskId: state.currentTaskId,
      selectedScreenplay: state.selectedScreenplay,
      viewMode: state.viewMode,
      setCurrentTaskId: state.setCurrentTaskId,
      setSelectedScreenplay: state.setSelectedScreenplay,
      setViewMode: state.setViewMode,
      resetScreenplayState: state.resetScreenplayState,
    }))
  );

export const useVoiceCasting = () =>
  useAppStore(
    useShallow((state) => ({
      // Data access
      sessions: state.sessions,
      activeSessionId: state.activeSessionId,

      // Actions
      updateActiveSession: state.updateActiveSession,
      deleteSession: state.deleteSession,
      selectOrCreateSession: state.selectOrCreateSession,
      resetCastingState: state.resetCastingState,
      setCharacterVoice: state.setCharacterVoice,
      setCharacterMetadata: state.setCharacterMetadata,
      removeCharacterAssignment: state.removeCharacterAssignment,
      removeVoiceFromAssignment: state.removeVoiceFromAssignment,
      importAssignments: state.importAssignments,
      setYamlContent: state.setYamlContent,
      setCastingMethod: state.setCastingMethod,
      addToVoiceCache: state.addToVoiceCache,
      updateVersionId: state.updateVersionId,

      // Computed getters
      getActiveSession: state.getActiveSession,
      getSessionStats: state.getSessionStats,
      getRecentSessions: state.getRecentSessions,
    }))
  );

// Helper function to clear persisted voice-casting data when starting a new session
// Note: This is now deprecated in favor of multi-session support
export const clearPersistedVoiceCastingData = () => {
  console.log(
    '[Voice Casting] clearPersistedVoiceCastingData is deprecated - sessions are now preserved'
  );
};

export default useAppStore;
