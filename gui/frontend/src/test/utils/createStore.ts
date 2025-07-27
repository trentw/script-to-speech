import { create } from 'zustand';

import type { AppStore } from '@/stores/appStore';

export function createStore(initialState?: Partial<AppStore>) {
  return create<AppStore>()((set) => ({
    // Configuration slice defaults
    selectedProvider: undefined,
    selectedVoice: undefined,
    currentConfig: {},

    // User Input slice defaults
    text: '',

    // UI slice defaults
    error: undefined,


    // Layout slice defaults
    viewportSize: 'desktop',
    sidebarExpanded: true,
    rightPanelExpanded: true,
    activeModal: null,

    // Screenplay slice defaults
    currentTaskId: undefined,
    selectedScreenplay: undefined,
    viewMode: 'upload',

    // Apply initial state overrides
    ...initialState,

    // Configuration slice actions
    setSelectedProvider: (provider) => set({ selectedProvider: provider }),
    setSelectedVoice: (voice) => set({ selectedVoice: voice }),
    setCurrentConfig: (config) => set({ currentConfig: config }),
    setConfiguration: (provider, voice, config) =>
      set({
        selectedProvider: provider,
        selectedVoice: voice,
        currentConfig: config,
      }),
    resetConfiguration: () =>
      set({
        selectedProvider: undefined,
        selectedVoice: undefined,
        currentConfig: {},
      }),

    // User Input slice actions
    setText: (text) => set({ text }),
    clearText: () => set({ text: '' }),

    // UI slice actions
    setError: (error) => set({ error }),
    clearError: () => set({ error: undefined }),


    // Layout slice actions
    setViewportSize: (size) => set({ viewportSize: size }),
    setSidebarExpanded: (expanded) => set({ sidebarExpanded: expanded }),
    toggleSidebar: () =>
      set((state) => ({ sidebarExpanded: !state.sidebarExpanded })),
    setRightPanelExpanded: (expanded) => set({ rightPanelExpanded: expanded }),
    toggleRightPanel: () =>
      set((state) => ({ rightPanelExpanded: !state.rightPanelExpanded })),
    setActiveModal: (modal) => set({ activeModal: modal }),
    closeModal: () => set({ activeModal: null }),

    // Screenplay slice actions
    setCurrentTaskId: (taskId) => set({ currentTaskId: taskId }),
    setSelectedScreenplay: (screenplay) =>
      set({ selectedScreenplay: screenplay }),
    setViewMode: (mode) => set({ viewMode: mode }),
    resetScreenplayState: () =>
      set({
        currentTaskId: undefined,
        selectedScreenplay: undefined,
        viewMode: 'upload',
      }),
  }));
}
