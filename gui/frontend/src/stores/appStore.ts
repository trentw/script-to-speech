import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';
import { devtools } from 'zustand/middleware';
import { useShallow } from 'zustand/react/shallow';

import type { ScreenplayResult, VoiceEntry } from '../types';

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
  sts_id: string;  // Changed from voiceId
  provider: string;
  voiceEntry?: VoiceEntry;
  confidence?: number;
  reasoning?: string;
  castingNotes?: string;
  role?: string;
  additional_notes?: string[];  // New field for arbitrary comments
  // Parsed metadata (not stored in YAML)
  line_count?: number;
  total_characters?: number;
  longest_dialogue?: number;
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

// Central Audio slice - manages the central audio player
interface CentralAudioSlice {
  audioUrl: string | undefined;
  primaryText: string | undefined;
  secondaryText: string | undefined;
  downloadFilename: string | undefined;
  loading: boolean;
  autoplay: boolean;

  // Actions
  setAudioData: (
    audioUrl: string,
    primaryText: string,
    secondaryText?: string,
    downloadFilename?: string,
    autoplay?: boolean
  ) => void;
  clearAudio: () => void;
  setLoading: (loading: boolean) => void;
  disableAutoplay: () => void;
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
  castingSessionId: string | undefined;
  screenplayJsonPath: string | undefined;
  screenplayData: { characters: Map<string, CharacterInfo> } | undefined;
  assignments: Map<string, VoiceAssignment>;
  castingMethod: 'manual' | 'llm-assisted';
  yamlContent: string | undefined;

  // Actions
  setCastingSessionId: (sessionId: string | undefined) => void;
  setScreenplayJsonPath: (path: string | undefined) => void;
  setScreenplayData: (data: { characters: Map<string, CharacterInfo> } | undefined) => void;
  setCharacterAssignment: (characterName: string, assignment: VoiceAssignment) => void;
  importAssignments: (assignments: Map<string, VoiceAssignment>) => void;
  setYamlContent: (content: string | undefined) => void;
  setCastingMethod: (method: 'manual' | 'llm-assisted') => void;
  resetCastingState: () => void;
}

// Combined store type
type AppStore = ConfigurationSlice &
  UserInputSlice &
  UISlice &
  CentralAudioSlice &
  LayoutSlice &
  ScreenplaySlice &
  VoiceCastingSlice;

// Create the store with domain slices
const useAppStore = create<AppStore>()(
  devtools(
    persist(
      (set) => ({
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

        // Central Audio slice implementation
        audioUrl: undefined,
        primaryText: undefined,
        secondaryText: undefined,
        downloadFilename: undefined,
        loading: false,
        autoplay: false,

        setAudioData: (
          audioUrl,
          primaryText,
          secondaryText,
          downloadFilename,
          autoplay = false
        ) => {
          set(
            {
              audioUrl,
              primaryText,
              secondaryText,
              downloadFilename,
              loading: false,
              autoplay,
            },
            false,
            'centralAudio/setAudioData'
          );
        },

        clearAudio: () => {
          set(
            {
              audioUrl: undefined,
              primaryText: undefined,
              secondaryText: undefined,
              downloadFilename: undefined,
              loading: false,
              autoplay: false,
            },
            false,
            'centralAudio/clearAudio'
          );
        },

        setLoading: (loading) => {
          set({ loading }, false, 'centralAudio/setLoading');
        },

        disableAutoplay: () => {
          set({ autoplay: false }, false, 'centralAudio/disableAutoplay');
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

        // Voice Casting slice implementation
        castingSessionId: undefined,
        screenplayJsonPath: undefined,
        screenplayData: undefined,
        assignments: new Map(),
        castingMethod: 'manual',
        yamlContent: undefined,

        setCastingSessionId: (sessionId) => {
          set({ castingSessionId: sessionId }, false, 'voiceCasting/setCastingSessionId');
        },

        setScreenplayJsonPath: (path) => {
          set({ screenplayJsonPath: path }, false, 'voiceCasting/setScreenplayJsonPath');
        },

        setScreenplayData: (data) => {
          set(
            { screenplayData: data },
            false,
            'voiceCasting/setScreenplayData'
          );
        },

        setCharacterAssignment: (characterName, assignment) => {
          set(
            (state) => {
              const newAssignments = new Map(state.assignments);
              newAssignments.set(characterName, assignment);
              return { assignments: newAssignments };
            },
            false,
            'voiceCasting/setCharacterAssignment'
          );
        },

        importAssignments: (assignments) => {
          set(
            { assignments },
            false,
            'voiceCasting/importAssignments'
          );
        },

        setYamlContent: (content) => {
          set(
            { yamlContent: content },
            false,
            'voiceCasting/setYamlContent'
          );
        },

        setCastingMethod: (method) => {
          set(
            { castingMethod: method },
            false,
            'voiceCasting/setCastingMethod'
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
            },
            false,
            'voiceCasting/reset'
          );
        },
      }),
      {
        name: 'sts-app-store', // localStorage key
        storage: createJSONStorage(() => localStorage),
        // Selective persistence - only persist user preferences
        partialize: (state) => ({
          selectedProvider: state.selectedProvider,
          selectedVoice: state.selectedVoice,
          currentConfig: state.currentConfig,
          sidebarExpanded: state.sidebarExpanded,
          rightPanelExpanded: state.rightPanelExpanded,
          // text, error, viewportSize, activeModal are NOT persisted (ephemeral state)
        }),
      }
    ),
    {
      name: 'STS App Store', // DevTools name
    }
  )
);

// Optimized selectors using useShallow to prevent infinite re-renders
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

export const useCentralAudio = () =>
  useAppStore(
    useShallow((state) => ({
      audioUrl: state.audioUrl,
      primaryText: state.primaryText,
      secondaryText: state.secondaryText,
      downloadFilename: state.downloadFilename,
      loading: state.loading,
      autoplay: state.autoplay,
      setAudioData: state.setAudioData,
      clearAudio: state.clearAudio,
      disableAutoplay: state.disableAutoplay,
      setLoading: state.setLoading,
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
      castingSessionId: state.castingSessionId,
      screenplayJsonPath: state.screenplayJsonPath,
      screenplayData: state.screenplayData,
      assignments: state.assignments,
      castingMethod: state.castingMethod,
      yamlContent: state.yamlContent,
      setCastingSessionId: state.setCastingSessionId,
      setScreenplayJsonPath: state.setScreenplayJsonPath,
      setScreenplayData: state.setScreenplayData,
      setCharacterAssignment: state.setCharacterAssignment,
      importAssignments: state.importAssignments,
      setYamlContent: state.setYamlContent,
      setCastingMethod: state.setCastingMethod,
      resetCastingState: state.resetCastingState,
    }))
  );

export default useAppStore;
