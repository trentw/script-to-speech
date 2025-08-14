import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';

// UI-only store for interface state (no server state)
interface UIStore {
  // Voice Casting UI State
  voiceCasting: {
    selectedTab: 'casting' | 'library' | 'notes';
    expandedCharacters: Set<string>;
    searchQuery: string;
    filterProvider: string | null;
    sortBy: 'name' | 'lines' | 'assigned';
    sortDirection: 'asc' | 'desc';
    showOnlyUnassigned: boolean;
  };

  // Layout & Modal State
  layout: {
    sidebarExpanded: boolean;
    rightPanelExpanded: boolean;
    activeModal: 'settings' | 'history' | 'export' | null;
  };

  // Actions - Voice Casting UI
  setSelectedTab: (tab: 'casting' | 'library' | 'notes') => void;
  toggleCharacterExpanded: (characterId: string) => void;
  setSearchQuery: (query: string) => void;
  setFilterProvider: (provider: string | null) => void;
  setSortBy: (sortBy: 'name' | 'lines' | 'assigned') => void;
  toggleSortDirection: () => void;
  toggleShowOnlyUnassigned: () => void;
  clearAllExpanded: () => void;
  expandAllCharacters: (characterIds: string[]) => void;

  // Actions - Layout
  setSidebarExpanded: (expanded: boolean) => void;
  toggleSidebar: () => void;
  setRightPanelExpanded: (expanded: boolean) => void;
  toggleRightPanel: () => void;
  setActiveModal: (modal: 'settings' | 'history' | 'export' | null) => void;
  closeModal: () => void;

  // Reset UI state
  resetUIState: () => void;
}

const initialState = {
  voiceCasting: {
    selectedTab: 'casting' as const,
    expandedCharacters: new Set<string>(),
    searchQuery: '',
    filterProvider: null,
    sortBy: 'name' as const,
    sortDirection: 'asc' as const,
    showOnlyUnassigned: false,
  },
  layout: {
    sidebarExpanded: true,
    rightPanelExpanded: false,
    activeModal: null,
  },
};

const useUIStore = create<UIStore>()(
  devtools(
    immer((set) => ({
      ...initialState,

      // Voice Casting UI Actions
      setSelectedTab: (tab) =>
        set((state) => {
          state.voiceCasting.selectedTab = tab;
        }),

      toggleCharacterExpanded: (characterId) =>
        set((state) => {
          if (state.voiceCasting.expandedCharacters.has(characterId)) {
            state.voiceCasting.expandedCharacters.delete(characterId);
          } else {
            state.voiceCasting.expandedCharacters.add(characterId);
          }
        }),

      setSearchQuery: (query) =>
        set((state) => {
          state.voiceCasting.searchQuery = query;
        }),

      setFilterProvider: (provider) =>
        set((state) => {
          state.voiceCasting.filterProvider = provider;
        }),

      setSortBy: (sortBy) =>
        set((state) => {
          state.voiceCasting.sortBy = sortBy;
        }),

      toggleSortDirection: () =>
        set((state) => {
          state.voiceCasting.sortDirection =
            state.voiceCasting.sortDirection === 'asc' ? 'desc' : 'asc';
        }),

      toggleShowOnlyUnassigned: () =>
        set((state) => {
          state.voiceCasting.showOnlyUnassigned = !state.voiceCasting.showOnlyUnassigned;
        }),

      clearAllExpanded: () =>
        set((state) => {
          state.voiceCasting.expandedCharacters.clear();
        }),

      expandAllCharacters: (characterIds) =>
        set((state) => {
          state.voiceCasting.expandedCharacters = new Set(characterIds);
        }),

      // Layout Actions
      setSidebarExpanded: (expanded) =>
        set((state) => {
          state.layout.sidebarExpanded = expanded;
        }),

      toggleSidebar: () =>
        set((state) => {
          state.layout.sidebarExpanded = !state.layout.sidebarExpanded;
        }),

      setRightPanelExpanded: (expanded) =>
        set((state) => {
          state.layout.rightPanelExpanded = expanded;
        }),

      toggleRightPanel: () =>
        set((state) => {
          state.layout.rightPanelExpanded = !state.layout.rightPanelExpanded;
        }),

      setActiveModal: (modal) =>
        set((state) => {
          state.layout.activeModal = modal;
        }),

      closeModal: () =>
        set((state) => {
          state.layout.activeModal = null;
        }),

      // Reset
      resetUIState: () =>
        set(() => ({
          ...initialState,
          voiceCasting: {
            ...initialState.voiceCasting,
            expandedCharacters: new Set<string>(),
          },
        })),
    })),
    {
      name: 'ui-store',
    }
  )
);

export default useUIStore;

// Selector hooks for specific UI slices
export const useVoiceCastingUI = () =>
  useUIStore((state) => ({
    ...state.voiceCasting,
    setSelectedTab: state.setSelectedTab,
    toggleCharacterExpanded: state.toggleCharacterExpanded,
    setSearchQuery: state.setSearchQuery,
    setFilterProvider: state.setFilterProvider,
    setSortBy: state.setSortBy,
    toggleSortDirection: state.toggleSortDirection,
    toggleShowOnlyUnassigned: state.toggleShowOnlyUnassigned,
    clearAllExpanded: state.clearAllExpanded,
    expandAllCharacters: state.expandAllCharacters,
  }));

export const useLayoutUI = () =>
  useUIStore((state) => ({
    ...state.layout,
    setSidebarExpanded: state.setSidebarExpanded,
    toggleSidebar: state.toggleSidebar,
    setRightPanelExpanded: state.setRightPanelExpanded,
    toggleRightPanel: state.toggleRightPanel,
    setActiveModal: state.setActiveModal,
    closeModal: state.closeModal,
  }));