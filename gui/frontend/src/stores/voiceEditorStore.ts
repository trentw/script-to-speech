import { create } from 'zustand';

import type { LLMRunImportResponse } from '../types/voice-editor';

interface VoiceEditorState {
  // Selection
  selectedProvider: string | null;
  selectedStsId: string | null;

  // Dirty tracking (set by View, read by Panel for navigation guard)
  isDirty: boolean;

  // LLM run data (ephemeral, not persisted)
  llmRunData: LLMRunImportResponse | null;
  llmRunDir: string | null;

  // UI state shared between Panel and View
  showLoadRunDialog: boolean;

  // Actions
  setSelectedProvider: (provider: string | null) => void;
  setSelectedStsId: (stsId: string | null) => void;
  setIsDirty: (dirty: boolean) => void;
  setLLMRunData: (
    data: LLMRunImportResponse | null,
    dir: string | null
  ) => void;
  clearLLMRun: () => void;
  setShowLoadRunDialog: (show: boolean) => void;
}

export const useVoiceEditorStore = create<VoiceEditorState>()((set) => ({
  selectedProvider: null,
  selectedStsId: null,
  isDirty: false,
  llmRunData: null,
  llmRunDir: null,
  showLoadRunDialog: false,

  setSelectedProvider: (provider) =>
    set({ selectedProvider: provider, selectedStsId: null }),
  setSelectedStsId: (stsId) => set({ selectedStsId: stsId }),
  setIsDirty: (dirty) => set({ isDirty: dirty }),
  setLLMRunData: (data, dir) => set({ llmRunData: data, llmRunDir: dir }),
  clearLLMRun: () => set({ llmRunData: null, llmRunDir: null }),
  setShowLoadRunDialog: (show) => set({ showLoadRunDialog: show }),
}));
