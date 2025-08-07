import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { createJSONStorage, persist } from 'zustand/middleware';
import { useShallow } from 'zustand/react/shallow';

import type { ScreenplayResult, VoiceEntry } from '../types';
import { createTTLStorage } from '../utils/ttlStorage';

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
  yamlContent?: string;
  voiceCache: Map<string, VoiceEntry>;
  lastUpdated: number;
  screenplayData?: { characters: Map<string, CharacterInfo> };
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

// Voice Casting slice - handles voice assignment for screenplay characters
interface VoiceCastingSlice {
  // Multi-session support
  voiceCastingSessions: Map<string, VoiceCastingSessionData>;
  activeSessionId: string | undefined;
  
  // Legacy fields for backward compatibility (will map to active session)
  castingSessionId: string | undefined;
  screenplayJsonPath: string | undefined;
  screenplayData: { characters: Map<string, CharacterInfo> } | undefined;
  assignments: Map<string, VoiceAssignment>;
  castingMethod: 'manual' | 'llm-assisted';
  yamlContent: string | undefined;
  voiceCache: Map<string, VoiceEntry>;

  // Actions
  setCastingSessionId: (sessionId: string | undefined) => void;
  setScreenplayJsonPath: (path: string | undefined) => void;
  setScreenplayData: (
    data: { characters: Map<string, CharacterInfo> } | undefined
  ) => void;

  // Character metadata operations (role, casting notes, etc.)
  setCharacterMetadata: (
    characterName: string,
    metadata: Partial<
      Pick<VoiceAssignment, 'role' | 'castingNotes' | 'additional_notes'>
    >
  ) => void;

  // Voice assignment operations (provider, sts_id, config)
  setCharacterVoice: (
    characterName: string,
    voiceData: {
      sts_id?: string;
      provider: string;
      provider_config?: Record<string, unknown>;
      voiceEntry?: VoiceEntry;
    }
  ) => void;

  // Full replacement (replaces entire assignment)
  replaceCharacterAssignment: (
    characterName: string,
    assignment: VoiceAssignment
  ) => void;

  removeCharacterAssignment: (characterName: string) => void;
  removeVoiceFromAssignment: (characterName: string) => void;
  importAssignments: (assignments: Map<string, VoiceAssignment>) => void;
  setYamlContent: (content: string | undefined) => void;
  setCastingMethod: (method: 'manual' | 'llm-assisted') => void;
  setVoiceCache: (cache: Map<string, VoiceEntry>) => void;
  addToVoiceCache: (
    provider: string,
    sts_id: string,
    voice: VoiceEntry
  ) => void;
  resetCastingState: () => void;
  
  // New multi-session actions
  setActiveSession: (sessionId: string) => void;
  createOrUpdateSession: (sessionData: Partial<VoiceCastingSessionData>) => void;
  getRecentSessions: (limit?: number) => VoiceCastingSessionData[];
  cleanOldSessions: () => void;
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
      (set, get) => ({
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
          set({ sidebarExpanded: expanded }, false, 'layout/setSidebarExpanded');
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

        // Voice Casting slice implementation
        voiceCastingSessions: new Map(),
        activeSessionId: undefined,
        castingSessionId: undefined,
        screenplayJsonPath: undefined,
        screenplayData: undefined,
        assignments: new Map(),
        castingMethod: 'manual',
        yamlContent: undefined,
        voiceCache: new Map(),

        setCastingSessionId: (sessionId) => {
          set(
            (state) => {
              // Update both legacy and active session
              const updates: Partial<VoiceCastingSlice> = {
                castingSessionId: sessionId,
                activeSessionId: sessionId,
              };
              
              // If we have a session, load its data
              if (sessionId && state.voiceCastingSessions.has(sessionId)) {
                const session = state.voiceCastingSessions.get(sessionId)!;
                Object.assign(updates, {
                  screenplayJsonPath: session.screenplayJsonPath,
                  screenplayData: session.screenplayData,
                  assignments: session.assignments,
                  castingMethod: session.castingMethod,
                  yamlContent: session.yamlContent,
                  voiceCache: session.voiceCache,
                });
              }
              
              return updates;
            },
            false,
            'voiceCasting/setCastingSessionId'
          );
        },

        setScreenplayJsonPath: (path) => {
          set(
            (state) => {
              const updates: Partial<VoiceCastingSlice> = {
                screenplayJsonPath: path,
              };
              
              // Update active session if exists
              if (state.activeSessionId && state.voiceCastingSessions.has(state.activeSessionId)) {
                const session = state.voiceCastingSessions.get(state.activeSessionId)!;
                const updatedSession = { ...session, screenplayJsonPath: path || session.screenplayJsonPath, lastUpdated: Date.now() };
                const newSessions = new Map(state.voiceCastingSessions);
                newSessions.set(state.activeSessionId, updatedSession);
                updates.voiceCastingSessions = newSessions;
              }
              
              return updates;
            },
            false,
            'voiceCasting/setScreenplayJsonPath'
          );
        },

        setScreenplayData: (data) => {
          set(
            (state) => {
              const updates: Partial<VoiceCastingSlice> = {
                screenplayData: data,
              };
              
              // Update active session if exists
              if (state.activeSessionId && state.voiceCastingSessions.has(state.activeSessionId)) {
                const session = state.voiceCastingSessions.get(state.activeSessionId)!;
                const updatedSession = { ...session, screenplayData: data, lastUpdated: Date.now() };
                const newSessions = new Map(state.voiceCastingSessions);
                newSessions.set(state.activeSessionId, updatedSession);
                updates.voiceCastingSessions = newSessions;
              }
              
              return updates;
            },
            false,
            'voiceCasting/setScreenplayData'
          );
        },

        setCharacterMetadata: (characterName, metadata) => {
          set(
            (state) => {
              const newAssignments = new Map(state.assignments);
              const existing = newAssignments.get(characterName) || {
                provider: '',
              };

              const updated: VoiceAssignment = {
                ...existing,
                ...metadata,
              };

              newAssignments.set(characterName, updated);
              
              // Update active session
              const updates: Partial<VoiceCastingSlice> = {
                assignments: newAssignments,
              };
              
              if (state.activeSessionId && state.voiceCastingSessions.has(state.activeSessionId)) {
                const session = state.voiceCastingSessions.get(state.activeSessionId)!;
                const updatedSession = { ...session, assignments: newAssignments, lastUpdated: Date.now() };
                const newSessions = new Map(state.voiceCastingSessions);
                newSessions.set(state.activeSessionId, updatedSession);
                updates.voiceCastingSessions = newSessions;
              }
              
              return updates;
            },
            false,
            'voiceCasting/setCharacterMetadata'
          );
        },

        setCharacterVoice: (characterName, voiceData) => {
          set(
            (state) => {
              const newAssignments = new Map(state.assignments);
              const existing = newAssignments.get(characterName);

              // Preserve existing metadata when updating voice
              const updated: VoiceAssignment = {
                ...voiceData,
                // Preserve metadata fields if they exist
                ...(existing?.role !== undefined && { role: existing.role }),
                ...(existing?.castingNotes !== undefined && {
                  castingNotes: existing.castingNotes,
                }),
                ...(existing?.additional_notes !== undefined && {
                  additional_notes: existing.additional_notes,
                }),
                ...(existing?.line_count !== undefined && {
                  line_count: existing.line_count,
                }),
                ...(existing?.total_characters !== undefined && {
                  total_characters: existing.total_characters,
                }),
                ...(existing?.longest_dialogue !== undefined && {
                  longest_dialogue: existing.longest_dialogue,
                }),
              };

              newAssignments.set(characterName, updated);
              
              // Update active session
              const updates: Partial<VoiceCastingSlice> = {
                assignments: newAssignments,
              };
              
              if (state.activeSessionId && state.voiceCastingSessions.has(state.activeSessionId)) {
                const session = state.voiceCastingSessions.get(state.activeSessionId)!;
                const updatedSession = { ...session, assignments: newAssignments, lastUpdated: Date.now() };
                const newSessions = new Map(state.voiceCastingSessions);
                newSessions.set(state.activeSessionId, updatedSession);
                updates.voiceCastingSessions = newSessions;
              }
              
              return updates;
            },
            false,
            'voiceCasting/setCharacterVoice'
          );
        },

        replaceCharacterAssignment: (characterName, assignment) => {
          set(
            (state) => {
              const newAssignments = new Map(state.assignments);
              newAssignments.set(characterName, assignment);
              
              // Update active session
              const updates: Partial<VoiceCastingSlice> = {
                assignments: newAssignments,
              };
              
              if (state.activeSessionId && state.voiceCastingSessions.has(state.activeSessionId)) {
                const session = state.voiceCastingSessions.get(state.activeSessionId)!;
                const updatedSession = { ...session, assignments: newAssignments, lastUpdated: Date.now() };
                const newSessions = new Map(state.voiceCastingSessions);
                newSessions.set(state.activeSessionId, updatedSession);
                updates.voiceCastingSessions = newSessions;
              }
              
              return updates;
            },
            false,
            'voiceCasting/replaceCharacterAssignment'
          );
        },

        removeCharacterAssignment: (characterName) => {
          set(
            (state) => {
              const newAssignments = new Map(state.assignments);
              newAssignments.delete(characterName);
              
              // Update active session
              const updates: Partial<VoiceCastingSlice> = {
                assignments: newAssignments,
              };
              
              if (state.activeSessionId && state.voiceCastingSessions.has(state.activeSessionId)) {
                const session = state.voiceCastingSessions.get(state.activeSessionId)!;
                const updatedSession = { ...session, assignments: newAssignments, lastUpdated: Date.now() };
                const newSessions = new Map(state.voiceCastingSessions);
                newSessions.set(state.activeSessionId, updatedSession);
                updates.voiceCastingSessions = newSessions;
              }
              
              return updates;
            },
            false,
            'voiceCasting/removeCharacterAssignment'
          );
        },

        removeVoiceFromAssignment: (characterName) => {
          set(
            (state) => {
              const newAssignments = new Map(state.assignments);
              const currentAssignment = newAssignments.get(characterName);

              if (currentAssignment) {
                // Create a new assignment that preserves character metadata but removes voice data
                const updatedAssignment: Partial<VoiceAssignment> = {
                  // Preserve character metadata only (only include if defined)
                  ...(currentAssignment.role !== undefined && {
                    role: currentAssignment.role,
                  }),
                  ...(currentAssignment.castingNotes !== undefined && {
                    castingNotes: currentAssignment.castingNotes,
                  }),
                  ...(currentAssignment.additional_notes !== undefined && {
                    additional_notes: currentAssignment.additional_notes,
                  }),
                  ...(currentAssignment.confidence !== undefined && {
                    confidence: currentAssignment.confidence,
                  }),
                  ...(currentAssignment.reasoning !== undefined && {
                    reasoning: currentAssignment.reasoning,
                  }),
                  ...(currentAssignment.line_count !== undefined && {
                    line_count: currentAssignment.line_count,
                  }),
                  ...(currentAssignment.total_characters !== undefined && {
                    total_characters: currentAssignment.total_characters,
                  }),
                  ...(currentAssignment.longest_dialogue !== undefined && {
                    longest_dialogue: currentAssignment.longest_dialogue,
                  }),
                };

                // Only keep the assignment if it has any metadata to preserve
                if (
                  updatedAssignment.role ||
                  updatedAssignment.castingNotes ||
                  updatedAssignment.additional_notes
                ) {
                  newAssignments.set(
                    characterName,
                    updatedAssignment as VoiceAssignment
                  );
                } else {
                  // If no metadata to preserve, remove the assignment completely
                  newAssignments.delete(characterName);
                }
              }

              // Update active session
              const updates: Partial<VoiceCastingSlice> = {
                assignments: newAssignments,
              };
              
              if (state.activeSessionId && state.voiceCastingSessions.has(state.activeSessionId)) {
                const session = state.voiceCastingSessions.get(state.activeSessionId)!;
                const updatedSession = { ...session, assignments: newAssignments, lastUpdated: Date.now() };
                const newSessions = new Map(state.voiceCastingSessions);
                newSessions.set(state.activeSessionId, updatedSession);
                updates.voiceCastingSessions = newSessions;
              }
              
              return updates;
            },
            false,
            'voiceCasting/removeVoiceFromAssignment'
          );
        },

        importAssignments: (assignments) => {
          set(
            (state) => {
              // Update active session
              const updates: Partial<VoiceCastingSlice> = {
                assignments,
              };
              
              if (state.activeSessionId && state.voiceCastingSessions.has(state.activeSessionId)) {
                const session = state.voiceCastingSessions.get(state.activeSessionId)!;
                const updatedSession = { ...session, assignments, lastUpdated: Date.now() };
                const newSessions = new Map(state.voiceCastingSessions);
                newSessions.set(state.activeSessionId, updatedSession);
                updates.voiceCastingSessions = newSessions;
              }
              
              return updates;
            },
            false,
            'voiceCasting/importAssignments'
          );
        },

        setYamlContent: (content) => {
          set(
            (state) => {
              // Update active session
              const updates: Partial<VoiceCastingSlice> = {
                yamlContent: content,
              };
              
              if (state.activeSessionId && state.voiceCastingSessions.has(state.activeSessionId)) {
                const session = state.voiceCastingSessions.get(state.activeSessionId)!;
                const updatedSession = { ...session, yamlContent: content, lastUpdated: Date.now() };
                const newSessions = new Map(state.voiceCastingSessions);
                newSessions.set(state.activeSessionId, updatedSession);
                updates.voiceCastingSessions = newSessions;
              }
              
              return updates;
            },
            false,
            'voiceCasting/setYamlContent'
          );
        },

        setCastingMethod: (method) => {
          set(
            (state) => {
              // Update active session
              const updates: Partial<VoiceCastingSlice> = {
                castingMethod: method,
              };
              
              if (state.activeSessionId && state.voiceCastingSessions.has(state.activeSessionId)) {
                const session = state.voiceCastingSessions.get(state.activeSessionId)!;
                const updatedSession = { ...session, castingMethod: method, lastUpdated: Date.now() };
                const newSessions = new Map(state.voiceCastingSessions);
                newSessions.set(state.activeSessionId, updatedSession);
                updates.voiceCastingSessions = newSessions;
              }
              
              return updates;
            },
            false,
            'voiceCasting/setCastingMethod'
          );
        },

        setVoiceCache: (cache) => {
          set(
            (state) => {
              // Update active session
              const updates: Partial<VoiceCastingSlice> = {
                voiceCache: cache,
              };
              
              if (state.activeSessionId && state.voiceCastingSessions.has(state.activeSessionId)) {
                const session = state.voiceCastingSessions.get(state.activeSessionId)!;
                const updatedSession = { ...session, voiceCache: cache, lastUpdated: Date.now() };
                const newSessions = new Map(state.voiceCastingSessions);
                newSessions.set(state.activeSessionId, updatedSession);
                updates.voiceCastingSessions = newSessions;
              }
              
              return updates;
            },
            false,
            'voiceCasting/setVoiceCache'
          );
        },

        addToVoiceCache: (provider, sts_id, voice) => {
          set(
            (state) => {
              const newCache = new Map(state.voiceCache);
              const cacheKey = `${provider}:${sts_id}`;
              newCache.set(cacheKey, voice);
              
              // Update active session
              const updates: Partial<VoiceCastingSlice> = {
                voiceCache: newCache,
              };
              
              if (state.activeSessionId && state.voiceCastingSessions.has(state.activeSessionId)) {
                const session = state.voiceCastingSessions.get(state.activeSessionId)!;
                const updatedSession = { ...session, voiceCache: newCache, lastUpdated: Date.now() };
                const newSessions = new Map(state.voiceCastingSessions);
                newSessions.set(state.activeSessionId, updatedSession);
                updates.voiceCastingSessions = newSessions;
              }
              
              return updates;
            },
            false,
            'voiceCasting/addToVoiceCache'
          );
        },

        resetCastingState: () => {
          set(
            {
              castingSessionId: undefined,
              screenplayJsonPath: undefined,
              screenplayData: undefined,
              assignments: new Map(),
              castingMethod: 'manual',
              yamlContent: undefined,
              voiceCache: new Map(),
              activeSessionId: undefined,
              // Note: We don't clear voiceCastingSessions to preserve other sessions
            },
            false,
            'voiceCasting/reset'
          );
        },
        
        // New multi-session actions
        setActiveSession: (sessionId) => {
          set(
            (state) => {
              const session = state.voiceCastingSessions.get(sessionId);
              if (!session) {
                console.warn(`[Voice Casting] Session ${sessionId} not found`);
                return {};
              }
              
              return {
                activeSessionId: sessionId,
                castingSessionId: sessionId,
                screenplayJsonPath: session.screenplayJsonPath,
                screenplayData: session.screenplayData,
                assignments: session.assignments,
                castingMethod: session.castingMethod,
                yamlContent: session.yamlContent,
                voiceCache: session.voiceCache,
              };
            },
            false,
            'voiceCasting/setActiveSession'
          );
        },
        
        createOrUpdateSession: (sessionData) => {
          set(
            (state) => {
              const sessionId = sessionData.sessionId || state.activeSessionId;
              if (!sessionId) {
                console.error('[Voice Casting] Cannot create/update session without sessionId');
                return {};
              }
              
              const existingSession = state.voiceCastingSessions.get(sessionId);
              const newSession: VoiceCastingSessionData = {
                sessionId,
                screenplayName: sessionData.screenplayName || existingSession?.screenplayName || '',
                screenplayJsonPath: sessionData.screenplayJsonPath || existingSession?.screenplayJsonPath || state.screenplayJsonPath || '',
                assignments: sessionData.assignments || existingSession?.assignments || state.assignments,
                castingMethod: sessionData.castingMethod || existingSession?.castingMethod || state.castingMethod,
                yamlContent: sessionData.yamlContent || existingSession?.yamlContent || state.yamlContent,
                voiceCache: sessionData.voiceCache || existingSession?.voiceCache || state.voiceCache,
                lastUpdated: Date.now(),
                screenplayData: sessionData.screenplayData || existingSession?.screenplayData || state.screenplayData,
              };
              
              const newSessions = new Map(state.voiceCastingSessions);
              newSessions.set(sessionId, newSession);
              
              return { voiceCastingSessions: newSessions };
            },
            false,
            'voiceCasting/createOrUpdateSession'
          );
        },
        
        getRecentSessions: (limit = 10) => {
          const state = get();
          const sessions = Array.from(state.voiceCastingSessions.values());
          
          // Sort by lastUpdated descending and limit
          return sessions
            .sort((a, b) => b.lastUpdated - a.lastUpdated)
            .slice(0, limit);
        },
        
        cleanOldSessions: () => {
          set(
            (state) => {
              const now = Date.now();
              const twelveHours = 12 * 60 * 60 * 1000;
              const maxSessions = 10;
              
              // Get all sessions sorted by lastUpdated
              const sessions = Array.from(state.voiceCastingSessions.entries())
                .sort((a, b) => b[1].lastUpdated - a[1].lastUpdated);
              
              const newSessions = new Map<string, VoiceCastingSessionData>();
              
              // Keep sessions that are either:
              // 1. Within the last 12 hours AND in the top 10 most recent
              // 2. Currently active
              sessions.forEach(([id, session], index) => {
                const age = now - session.lastUpdated;
                const isActive = id === state.activeSessionId;
                const isRecent = age < twelveHours;
                const isTopN = index < maxSessions;
                
                if (isActive || (isRecent && isTopN)) {
                  newSessions.set(id, session);
                }
              });
              
              console.log(`[Voice Casting] Cleaned sessions: kept ${newSessions.size} of ${state.voiceCastingSessions.size}`);
              
              return { voiceCastingSessions: newSessions };
            },
            false,
            'voiceCasting/cleanOldSessions'
          );
        },
      }),
      {
        name: 'sts-app-store', // localStorage key
        storage: createJSONStorage(() => createTTLStorage(12)), // 12-hour TTL
        // Selective persistence - only persist user preferences and voice-casting data
        partialize: (state) => ({
          // User preferences (existing)
          selectedProvider: state.selectedProvider,
          selectedVoice: state.selectedVoice,
          currentConfig: state.currentConfig,
          sidebarExpanded: state.sidebarExpanded,
          rightPanelExpanded: state.rightPanelExpanded,
          
          // Voice-casting sessions (new) - Convert Maps to Objects for serialization
          voiceCastingSessions: Object.fromEntries(
            Array.from(state.voiceCastingSessions.entries()).map(([id, session]) => [
              id,
              {
                ...session,
                assignments: Object.fromEntries(session.assignments),
                voiceCache: Object.fromEntries(session.voiceCache),
                screenplayData: session.screenplayData ? {
                  characters: Object.fromEntries(session.screenplayData.characters)
                } : undefined,
              }
            ])
          ),
          activeSessionId: state.activeSessionId,
          
          // text, error, viewportSize, activeModal are NOT persisted (ephemeral state)
        }),
        
        // Rehydration handler to convert Objects back to Maps
        onRehydrateStorage: () => {
          console.log('[Voice Casting] Starting hydration from persistent storage');
          
          return (state, error) => {
            if (error) {
              console.error('[Voice Casting] Hydration error:', error);
              return;
            }
            
            if (state) {
              try {
                // Convert persisted sessions back to Maps
                if (state.voiceCastingSessions && typeof state.voiceCastingSessions === 'object') {
                  const sessions = new Map<string, VoiceCastingSessionData>();
                  
                  Object.entries(state.voiceCastingSessions).forEach(([id, session]: [string, any]) => {
                    sessions.set(id, {
                      ...session,
                      assignments: new Map(Object.entries(session.assignments || {})),
                      voiceCache: new Map(Object.entries(session.voiceCache || {})),
                      screenplayData: session.screenplayData ? {
                        characters: new Map(Object.entries(session.screenplayData.characters || {}))
                      } : undefined,
                    });
                  });
                  
                  state.voiceCastingSessions = sessions;
                  
                  // Clean old sessions on startup
                  const now = Date.now();
                  const twelveHours = 12 * 60 * 60 * 1000;
                  const maxSessions = 10;
                  
                  const sortedSessions = Array.from(sessions.entries())
                    .sort((a, b) => b[1].lastUpdated - a[1].lastUpdated);
                  
                  const cleanedSessions = new Map<string, VoiceCastingSessionData>();
                  sortedSessions.forEach(([id, session], index) => {
                    const age = now - session.lastUpdated;
                    if (age < twelveHours && index < maxSessions) {
                      cleanedSessions.set(id, session);
                    }
                  });
                  
                  state.voiceCastingSessions = cleanedSessions;
                  console.log(`[Voice Casting] Restored ${cleanedSessions.size} sessions from storage`);
                  
                  // If we have an active session, load its data
                  if (state.activeSessionId && cleanedSessions.has(state.activeSessionId)) {
                    const activeSession = cleanedSessions.get(state.activeSessionId)!;
                    state.castingSessionId = state.activeSessionId;
                    state.screenplayJsonPath = activeSession.screenplayJsonPath;
                    state.screenplayData = activeSession.screenplayData;
                    state.assignments = activeSession.assignments;
                    state.castingMethod = activeSession.castingMethod;
                    state.yamlContent = activeSession.yamlContent;
                    state.voiceCache = activeSession.voiceCache;
                  } else {
                    // Clear active session if it no longer exists
                    state.activeSessionId = undefined;
                    state.castingSessionId = undefined;
                    state.screenplayJsonPath = undefined;
                    state.screenplayData = undefined;
                    state.assignments = new Map();
                    state.castingMethod = 'manual';
                    state.yamlContent = undefined;
                    state.voiceCache = new Map();
                  }
                }
              } catch (rehydrationError) {
                console.error('[Voice Casting] Error during rehydration:', rehydrationError);
                // Initialize with empty data on error
                state.voiceCastingSessions = new Map();
                state.activeSessionId = undefined;
                state.castingSessionId = undefined;
                state.screenplayJsonPath = undefined;
                state.screenplayData = undefined;
                state.assignments = new Map();
                state.castingMethod = 'manual';
                state.yamlContent = undefined;
                state.voiceCache = new Map();
              }
            }
          };
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
      // Multi-session data
      voiceCastingSessions: state.voiceCastingSessions,
      activeSessionId: state.activeSessionId,
      
      // Current session data
      castingSessionId: state.castingSessionId,
      screenplayJsonPath: state.screenplayJsonPath,
      screenplayData: state.screenplayData,
      assignments: state.assignments,
      castingMethod: state.castingMethod,
      yamlContent: state.yamlContent,
      voiceCache: state.voiceCache,
      
      // Actions
      setCastingSessionId: state.setCastingSessionId,
      setScreenplayJsonPath: state.setScreenplayJsonPath,
      setScreenplayData: state.setScreenplayData,
      setCharacterMetadata: state.setCharacterMetadata,
      setCharacterVoice: state.setCharacterVoice,
      replaceCharacterAssignment: state.replaceCharacterAssignment,
      removeCharacterAssignment: state.removeCharacterAssignment,
      removeVoiceFromAssignment: state.removeVoiceFromAssignment,
      importAssignments: state.importAssignments,
      setYamlContent: state.setYamlContent,
      setCastingMethod: state.setCastingMethod,
      setVoiceCache: state.setVoiceCache,
      addToVoiceCache: state.addToVoiceCache,
      resetCastingState: state.resetCastingState,
      
      // Multi-session actions
      setActiveSession: state.setActiveSession,
      createOrUpdateSession: state.createOrUpdateSession,
      getRecentSessions: state.getRecentSessions,
      cleanOldSessions: state.cleanOldSessions,
    }))
  );

// Helper function to clear persisted voice-casting data when starting a new session
// Note: This is now deprecated in favor of multi-session support
export const clearPersistedVoiceCastingData = () => {
  console.log('[Voice Casting] clearPersistedVoiceCastingData is deprecated - sessions are now preserved');
};

export default useAppStore;