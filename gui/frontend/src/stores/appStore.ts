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
  activeModal: 'settings' | 'history' | null;

  // Actions
  setViewportSize: (size: 'mobile' | 'tablet' | 'desktop') => void;
  setSidebarExpanded: (expanded: boolean) => void;
  toggleSidebar: () => void;
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

// Project mode types using discriminated union for better type safety
import type { ProjectMetaStore as ProjectMeta } from '../types/project';

// True discriminated union - state shape changes with mode
// In project mode, project can be null (empty project state)
type ProjectState =
  | { mode: 'manual'; recentProjects: string[] }
  | { mode: 'project'; project: ProjectMeta | null; recentProjects: string[] };

// Project slice - handles project mode state and recent projects
interface ProjectSlice {
  // State is now a discriminated union
  projectState: ProjectState;

  // Actions
  setProject: (project: ProjectMeta | null) => void;
  setMode: (mode: 'manual' | 'project') => void;
  addRecentProject: (path: string) => void;
  clearRecentProjects: () => void;
  resetProjectState: () => void;
}

// Combined store type
type AppStore = ConfigurationSlice &
  UserInputSlice &
  UISlice &
  LayoutSlice &
  ScreenplaySlice &
  ProjectSlice;

// Create the store with domain slices
const useAppStore = create<AppStore>()(
  devtools(
    persist(
      immer((set) => ({
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
            'configuration/resetConfiguration'
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
        activeModal: null,

        setViewportSize: (size) => {
          set(
            (draft) => {
              draft.viewportSize = size;
              // Auto-collapse sidebar on mobile
              if (size === 'mobile') {
                draft.sidebarExpanded = false;
              }
            },
            false,
            'layout/setViewportSize'
          );
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
            (draft) => {
              draft.sidebarExpanded = !draft.sidebarExpanded;
            },
            false,
            'layout/toggleSidebar'
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
            'screenplay/resetScreenplayState'
          );
        },

        // Project slice implementation
        projectState: { mode: 'manual', recentProjects: [] } as ProjectState,

        setProject: (project) => {
          set(
            (draft) => {
              if (project) {
                // Switch to project mode, preserving recent projects
                draft.projectState = {
                  mode: 'project',
                  project,
                  recentProjects: draft.projectState.recentProjects,
                };
              } else {
                // Switch to manual mode, preserving recent projects
                draft.projectState = {
                  mode: 'manual',
                  recentProjects: draft.projectState.recentProjects,
                };
              }
            },
            false,
            'project/setProject'
          );
        },

        setMode: (mode) => {
          set(
            (draft) => {
              if (mode === 'manual') {
                // Switch to manual mode, preserving recent projects
                draft.projectState = {
                  mode: 'manual',
                  recentProjects: draft.projectState.recentProjects,
                };
              } else if (mode === 'project') {
                // Switch to project mode without a project, preserving recent projects
                draft.projectState = {
                  mode: 'project',
                  project: null,
                  recentProjects: draft.projectState.recentProjects,
                };
              }
            },
            false,
            'project/setMode'
          );
        },

        addRecentProject: (path) => {
          set(
            (draft) => {
              // LRU: Move to front if exists, add to front if new
              const currentRecent = draft.projectState.recentProjects;
              const newRecent = [
                path,
                ...currentRecent.filter((p) => p !== path),
              ].slice(0, 10); // Keep max 10 recent projects

              // Update recentProjects while preserving mode
              if (draft.projectState.mode === 'project') {
                draft.projectState = {
                  ...draft.projectState,
                  recentProjects: newRecent,
                };
              } else {
                draft.projectState = {
                  mode: 'manual',
                  recentProjects: newRecent,
                };
              }
            },
            false,
            'project/addRecentProject'
          );
        },

        clearRecentProjects: () => {
          set(
            (draft) => {
              if (draft.projectState.mode === 'project') {
                draft.projectState = {
                  ...draft.projectState,
                  recentProjects: [],
                };
              } else {
                draft.projectState = {
                  mode: 'manual',
                  recentProjects: [],
                };
              }
            },
            false,
            'project/clearRecentProjects'
          );
        },

        // Reset project state - useful for testing and cleanup
        resetProjectState: () => {
          set(
            (draft) => {
              draft.projectState = { mode: 'manual', recentProjects: [] };
            },
            false,
            'project/resetProjectState'
          );
        },
      })),
      {
        name: 'app-store',
        storage: createSuperJSONStorage(),
        partialize: (state) => ({
          // Persist user preferences
          selectedProvider: state.selectedProvider,
          selectedVoice: state.selectedVoice,
          currentConfig: state.currentConfig,

          // Persist layout preferences
          sidebarExpanded: state.sidebarExpanded,

          // Persist project mode state (entire discriminated union)
          projectState: state.projectState,
        }),
      }
    )
  )
);

// Export typed selector hooks for each domain
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
      activeModal: state.activeModal,
      setViewportSize: state.setViewportSize,
      setSidebarExpanded: state.setSidebarExpanded,
      toggleSidebar: state.toggleSidebar,
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

// Project mode selector hook with full type safety
export const useProject = () =>
  useAppStore(
    useShallow((state) => ({
      // Spread the discriminated union state
      ...state.projectState,
      // Include actions
      setProject: state.setProject,
      setMode: state.setMode,
      addRecentProject: state.addRecentProject,
      clearRecentProjects: state.clearRecentProjects,
      resetProjectState: state.resetProjectState,
    }))
  );

// Derived selector: check if a project is currently loaded
export const useHasProject = (): boolean => {
  return useAppStore((state) => {
    const { projectState } = state;
    return projectState.mode === 'project' && projectState.project !== null;
  });
};

// Export types for external use
export type { ProjectState };
export type { ProjectMetaStore as ProjectMeta } from '../types/project';

// Export the store for debugging
export default useAppStore;
