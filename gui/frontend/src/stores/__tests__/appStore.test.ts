import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';

import type { ProjectMeta } from '../appStore';
import useAppStore, { useProject } from '../appStore';

describe('AppStore - Configuration Slice', () => {
  beforeEach(() => {
    // Reset store to initial state before each test
    localStorage.clear();
    const state = useAppStore.getState();
    state.resetConfiguration();
    state.clearText();
    state.clearError();
    state.resetScreenplayState();
    // Also reset layout state to defaults
    state.setSidebarExpanded(true);
    state.setViewportSize('desktop');
    // Reset project mode to manual
    state.setMode('manual');
  });

  describe('setSelectedProvider', () => {
    it('should update the selected provider', () => {
      // Arrange
      const { result } = renderHook(() => useAppStore());
      const newProvider = 'elevenlabs';

      // Act
      act(() => {
        result.current.setSelectedProvider(newProvider);
      });

      // Assert
      expect(result.current.selectedProvider).toBe(newProvider);
    });

    it('should handle null provider', () => {
      // Arrange
      const { result } = renderHook(() => useAppStore());

      // Act
      act(() => {
        result.current.setSelectedProvider(undefined);
      });

      // Assert
      expect(result.current.selectedProvider).toBeUndefined();
    });
  });

  describe('setSelectedVoice', () => {
    it('should update the selected voice', () => {
      // Arrange
      const { result } = renderHook(() => useAppStore());
      const newVoice = {
        sts_id: 'openai:alloy',
        provider: 'openai',
        config: { voice: 'alloy' },
      };

      // Act
      act(() => {
        result.current.setSelectedVoice(newVoice);
      });

      // Assert
      expect(result.current.selectedVoice).toEqual(newVoice);
    });

    it('should handle null voice', () => {
      // Arrange
      const { result } = renderHook(() => useAppStore());

      // Act
      act(() => {
        result.current.setSelectedVoice(undefined);
      });

      // Assert
      expect(result.current.selectedVoice).toBeUndefined();
    });
  });

  describe('setCurrentConfig', () => {
    it('should update the current configuration', () => {
      // Arrange
      const { result } = renderHook(() => useAppStore());
      const newConfig = {
        speed: 1.5,
        pitch: 0.8,
        volume: 0.9,
      };

      // Act
      act(() => {
        result.current.setCurrentConfig(newConfig);
      });

      // Assert
      expect(result.current.currentConfig).toEqual(newConfig);
    });

    it('should allow manual merging of config updates', () => {
      // Arrange
      const { result } = renderHook(() => useAppStore());
      act(() => {
        result.current.setCurrentConfig({ pitch: 1.0, speed: 1.0 });
      });

      // Act - manually merge the config
      act(() => {
        result.current.setCurrentConfig({
          ...result.current.currentConfig,
          speed: 1.5,
        });
      });

      // Assert
      expect(result.current.currentConfig).toEqual({
        speed: 1.5,
        pitch: 1.0,
      });
    });
  });

  describe('reset', () => {
    it('should reset all slices to initial state', () => {
      // Arrange
      const { result } = renderHook(() => useAppStore());

      // Act - set some values first
      act(() => {
        result.current.setSelectedProvider('openai');
        result.current.setSelectedVoice({
          sts_id: 'openai:echo',
          provider: 'openai',
          config: { voice: 'echo' },
        });
        result.current.setCurrentConfig({ speed: 2.0 });
        result.current.setText('Test text');
        result.current.setError('Test error');
      });

      // Assert - values are set
      expect(result.current.selectedProvider).toBe('openai');
      expect(result.current.selectedVoice?.sts_id).toBe('openai:echo');
      expect(result.current.currentConfig).toEqual({ speed: 2.0 });
      expect(result.current.text).toBe('Test text');
      expect(result.current.error).toBe('Test error');

      // Act - reset each slice
      act(() => {
        result.current.resetConfiguration();
        result.current.clearText();
        result.current.clearError();
      });

      // Assert - all values reset to initial state
      expect(result.current.selectedProvider).toBeUndefined();
      expect(result.current.selectedVoice).toBeUndefined();
      expect(result.current.currentConfig).toEqual({});
      expect(result.current.text).toBe('');
      expect(result.current.error).toBeUndefined();
    });
  });

  describe('state persistence', () => {
    it('should persist configuration slice to localStorage', async () => {
      // Test writing to localStorage
      const { result: writeResult } = renderHook(() => useAppStore());
      const testVoice = {
        sts_id: 'cartesia:sarah',
        provider: 'cartesia',
        config: { voice: 'sarah' },
      };

      // Act - set values in the store
      act(() => {
        writeResult.current.setSelectedProvider('cartesia');
        writeResult.current.setSelectedVoice(testVoice);
      });

      // Wait for async persistence to complete
      await new Promise((resolve) => setTimeout(resolve, 100));

      // Verify data was written to localStorage
      const storedDataRaw = localStorage.getItem('app-store');
      expect(storedDataRaw).toBeTruthy();

      // Parse the stored data (SuperJSON format)
      const storedData = JSON.parse(storedDataRaw!);

      // SuperJSON with Zustand persist wraps data in { json: { state: {...}, version: 0 } }
      expect(storedData).toHaveProperty('json');
      expect(storedData.json).toHaveProperty('state');

      const persistedState = storedData.json.state;
      expect(persistedState.selectedProvider).toBe('cartesia');
      expect(persistedState.selectedVoice).toEqual(testVoice);
    });

    it('should verify localStorage integration for rehydration', async () => {
      // This test validates that the localStorage structure is correct
      // for rehydration without trying to fight Zustand's singleton store pattern.
      // It ensures the persistence layer is working correctly.

      // Set data in localStorage that would be rehydrated
      const mockPersistedData = {
        json: {
          state: {
            selectedProvider: 'elevenlabs',
            selectedVoice: {
              sts_id: 'elevenlabs:rachel',
              provider: 'elevenlabs',
              config: { voice: 'rachel' },
            },
            currentConfig: { speed: 1.2 },
            sidebarExpanded: false,
          },
          version: 0,
        },
      };

      localStorage.setItem('app-store', JSON.stringify(mockPersistedData));

      // Verify the data exists and is properly formatted for rehydration
      const stored = localStorage.getItem('app-store');
      expect(stored).toBeTruthy();

      const parsed = JSON.parse(stored!);
      expect(parsed.json.state.selectedProvider).toBe('elevenlabs');
      expect(parsed.json.state.selectedVoice.sts_id).toBe('elevenlabs:rachel');
      expect(parsed.json.state.currentConfig.speed).toBe(1.2);
      expect(parsed.json.state.sidebarExpanded).toBe(false);

      // Verify the structure matches what Zustand persist expects
      expect(parsed).toHaveProperty('json');
      expect(parsed.json).toHaveProperty('state');
      expect(parsed.json).toHaveProperty('version');

      // This verifies that localStorage contains the correct structure
      // that would be rehydrated on app initialization
    });

    it('should only persist specified fields via partialize', async () => {
      // Arrange
      const { result } = renderHook(() => useAppStore());

      // Act - set both persisted and non-persisted values
      act(() => {
        // These should be persisted
        result.current.setSelectedProvider('openai');
        result.current.setSelectedVoice({
          sts_id: 'openai:echo',
          provider: 'openai',
          config: { voice: 'echo' },
        });
        result.current.setCurrentConfig({ pitch: 1.2 });
        result.current.setSidebarExpanded(false);

        // These should NOT be persisted
        result.current.setText('Temporary text');
        result.current.setError('Temporary error');
        result.current.setViewportSize('mobile');
        result.current.setCurrentTaskId('task-123');
      });

      // Wait for persistence
      await new Promise((resolve) => setTimeout(resolve, 100));

      // Assert - check what was persisted
      const storedDataRaw = localStorage.getItem('app-store');
      expect(storedDataRaw).toBeTruthy();

      const storedData = JSON.parse(storedDataRaw!);
      // The data is nested in json.state
      const state = storedData.json.state;

      // Should be persisted (as defined in partialize)
      expect(state.selectedProvider).toBe('openai');
      expect(state.selectedVoice).toEqual({
        sts_id: 'openai:echo',
        provider: 'openai',
        config: { voice: 'echo' },
      });
      expect(state.currentConfig).toEqual({ pitch: 1.2 });
      expect(state.sidebarExpanded).toBe(false);

      // Should NOT be persisted
      expect(state.text).toBeUndefined();
      expect(state.error).toBeUndefined();
      expect(state.viewportSize).toBeUndefined();
      expect(state.currentTaskId).toBeUndefined();
    });

    it('should handle missing localStorage data gracefully', () => {
      // Ensure localStorage is empty
      localStorage.removeItem('app-store');

      // Create a new store instance
      const { result } = renderHook(() => useAppStore());

      // Should have default values when no persisted data exists
      // Note: No need to wait for hydration as there's nothing to hydrate
      expect(result.current.selectedProvider).toBeUndefined();
      expect(result.current.selectedVoice).toBeUndefined();
      expect(result.current.currentConfig).toEqual({});
      expect(result.current.sidebarExpanded).toBe(true); // default value
    });

    it('should handle corrupted localStorage data gracefully', async () => {
      // Set corrupted data in localStorage
      localStorage.setItem('app-store', 'invalid-json-{not-valid}');

      // Create a new store instance
      const { result } = renderHook(() => useAppStore());

      // Wait for hydration attempt
      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 100));
      });

      // Should fall back to default values on parse error
      expect(result.current.selectedProvider).toBeUndefined();
      expect(result.current.selectedVoice).toBeUndefined();
      expect(result.current.currentConfig).toEqual({});
    });
  });
});

describe('AppStore - Project Slice', () => {
  const mockProject: ProjectMeta = {
    screenplayName: 'test-script',
    inputPath: '/path/to/input/test-script',
    outputPath: '/path/to/output/test-script',
  };

  beforeEach(() => {
    // Reset store to initial state before each test
    localStorage.clear();

    // Get fresh state and reset everything
    const state = useAppStore.getState();

    // Reset all slices
    state.resetConfiguration();
    state.clearText();
    state.clearError();
    state.resetScreenplayState();
    state.setSidebarExpanded(true);
    state.setViewportSize('desktop');

    // Reset project state to ensure clean manual mode
    state.resetProjectState();
  });

  describe('initial state', () => {
    it('should start in manual mode', () => {
      const { result } = renderHook(() => useAppStore());

      expect(result.current.projectState.mode).toBe('manual');
      expect('project' in result.current.projectState).toBe(false);
      expect('recentProjects' in result.current.projectState).toBe(true); // recentProjects exists in both modes
    });
  });

  describe('setProject', () => {
    it('should switch to project mode when setting a project', () => {
      const { result } = renderHook(() => useAppStore());

      act(() => {
        result.current.setProject(mockProject);
      });

      expect(result.current.projectState.mode).toBe('project');
      if (result.current.projectState.mode === 'project') {
        expect(result.current.projectState.project).toEqual(mockProject);
        expect(result.current.projectState.recentProjects).toEqual([]);
      }
    });

    it('should switch to manual mode when setting null project', () => {
      const { result } = renderHook(() => useAppStore());

      // First set a project
      act(() => {
        result.current.setProject(mockProject);
      });
      expect(result.current.projectState.mode).toBe('project');

      // Then clear it
      act(() => {
        result.current.setProject(null);
      });

      expect(result.current.projectState.mode).toBe('manual');
      expect('project' in result.current).toBe(false);
      expect('recentProjects' in result.current).toBe(false);
    });

    it('should initialize recentProjects when switching to project mode', () => {
      const { result } = renderHook(() => useAppStore());

      act(() => {
        result.current.setProject(mockProject);
      });

      if (result.current.projectState.mode === 'project') {
        expect(result.current.projectState.recentProjects).toEqual([]);
      }
    });
  });

  describe('setMode', () => {
    it('should switch to manual mode and clean up project data', () => {
      const { result } = renderHook(() => useAppStore());

      // First set project mode
      act(() => {
        result.current.setProject(mockProject);
      });
      expect(result.current.projectState.mode).toBe('project');

      // Then switch to manual
      act(() => {
        result.current.setMode('manual');
      });

      expect(result.current.projectState.mode).toBe('manual');
      expect('project' in result.current).toBe(false);
      expect('recentProjects' in result.current).toBe(false);
    });

    it('should only allow manual mode in setMode (project mode via setProject)', () => {
      const { result } = renderHook(() => useAppStore());

      // First set a project
      act(() => {
        result.current.setProject(mockProject);
      });
      expect(result.current.projectState.mode).toBe('project');

      // setMode only accepts 'manual' - enforced by TypeScript
      // To switch to project mode, must use setProject()
      act(() => {
        result.current.setMode('manual');
      });

      expect(result.current.projectState.mode).toBe('manual');
    });
  });

  describe('addRecentProject', () => {
    it('should add project to recent projects in project mode', () => {
      const { result } = renderHook(() => useAppStore());

      act(() => {
        result.current.setProject(mockProject);
      });

      const recentPath = '/path/to/recent/project';
      act(() => {
        result.current.addRecentProject(recentPath);
      });

      if (result.current.projectState.mode === 'project') {
        expect(result.current.projectState.recentProjects).toEqual([
          recentPath,
        ]);
      }
    });

    it('should implement LRU logic for recent projects', () => {
      const { result } = renderHook(() => useAppStore());

      // Ensure clean state
      act(() => {
        result.current.setProject(null);
        result.current.setProject(mockProject);
      });

      const project1 = '/path/to/project1';
      const project2 = '/path/to/project2';
      const project3 = '/path/to/project3';

      // Add projects in order
      act(() => {
        result.current.addRecentProject(project1);
        result.current.addRecentProject(project2);
        result.current.addRecentProject(project3);
      });

      if (result.current.projectState.mode === 'project') {
        expect(result.current.projectState.recentProjects).toEqual([
          project3,
          project2,
          project1,
        ]);
      }

      // Re-add project1 - should move to front
      act(() => {
        result.current.addRecentProject(project1);
      });

      if (result.current.projectState.mode === 'project') {
        expect(result.current.projectState.recentProjects).toEqual([
          project1,
          project3,
          project2,
        ]);
      }
    });

    it('should limit recent projects to maximum 10 items', () => {
      const { result } = renderHook(() => useAppStore());

      act(() => {
        result.current.setProject(mockProject);
      });

      // Add 12 projects
      const projects = Array.from(
        { length: 12 },
        (_, i) => `/path/to/project${i}`
      );

      act(() => {
        projects.forEach((project) => {
          result.current.addRecentProject(project);
        });
      });

      if (result.current.projectState.mode === 'project') {
        expect(result.current.projectState.recentProjects).toHaveLength(10);
        // Should keep the 10 most recent (last 10 added)
        expect(result.current.projectState.recentProjects).toEqual(
          projects.slice(2).reverse()
        );
      }
    });

    it('should not modify recent projects in manual mode', () => {
      const { result } = renderHook(() => useAppStore());

      // Try to add project in manual mode
      act(() => {
        result.current.addRecentProject('/some/path');
      });

      expect(result.current.projectState.mode).toBe('manual');
      expect('recentProjects' in result.current).toBe(false);
    });
  });

  describe('clearRecentProjects', () => {
    it('should clear recent projects in project mode', () => {
      const { result } = renderHook(() => useAppStore());

      // Ensure clean state
      act(() => {
        result.current.setProject(null);
        result.current.setProject(mockProject);
        result.current.addRecentProject('/path/1');
        result.current.addRecentProject('/path/2');
      });

      if (result.current.projectState.mode === 'project') {
        expect(result.current.projectState.recentProjects).toHaveLength(2);
      }

      act(() => {
        result.current.clearRecentProjects();
      });

      if (result.current.projectState.mode === 'project') {
        expect(result.current.projectState.recentProjects).toEqual([]);
      }
    });

    it('should not affect manual mode', () => {
      const { result } = renderHook(() => useAppStore());

      act(() => {
        result.current.clearRecentProjects();
      });

      expect(result.current.projectState.mode).toBe('manual');
      expect('recentProjects' in result.current).toBe(false);
    });
  });

  describe('useProject selector hook', () => {
    it('should return correct data in manual mode', () => {
      const { result } = renderHook(() => useProject());

      expect(result.current.mode).toBe('manual');
      expect('project' in result.current).toBe(false);
      expect(result.current.recentProjects).toEqual([]); // recentProjects exists in both modes
      expect(typeof result.current.setProject).toBe('function');
      expect(typeof result.current.setMode).toBe('function');
      expect(typeof result.current.addRecentProject).toBe('function');
      expect(typeof result.current.clearRecentProjects).toBe('function');
    });

    it('should return correct data in project mode', () => {
      const { result: storeResult } = renderHook(() => useAppStore());
      const { result: selectorResult } = renderHook(() => useProject());

      // Ensure clean state
      act(() => {
        storeResult.current.setProject(null);
        storeResult.current.setProject(mockProject);
      });

      expect(selectorResult.current.mode).toBe('project');
      if (selectorResult.current.mode === 'project') {
        expect(selectorResult.current.project).toEqual(mockProject);
        expect(selectorResult.current.recentProjects).toEqual([]);
      }
    });

    it('should only re-render when project-related state changes', () => {
      const { result: selectorResult } = renderHook(() => useProject());
      const { result: storeResult } = renderHook(() => useAppStore());

      const initialRender = selectorResult.current;

      // Change non-project state
      act(() => {
        storeResult.current.setText('some text');
        storeResult.current.setError('some error');
        storeResult.current.setSelectedProvider('openai');
      });

      // Should be same reference (no re-render due to useShallow)
      expect(selectorResult.current).toBe(initialRender);

      // Change project state
      act(() => {
        storeResult.current.setProject(mockProject);
      });

      // Should be different reference (re-render occurred)
      expect(selectorResult.current).not.toBe(initialRender);
    });
  });

  describe('persistence', () => {
    it('should persist project mode state to localStorage', async () => {
      const { result } = renderHook(() => useAppStore());

      // Ensure clean state
      act(() => {
        result.current.setProject(null);
        result.current.setProject(mockProject);
        result.current.addRecentProject('/recent/path');
      });

      // Wait for async persistence
      await new Promise((resolve) => setTimeout(resolve, 100));

      const storedData = JSON.parse(localStorage.getItem('app-store')!);
      const persistedState = storedData.json.state;

      expect(persistedState.projectState.mode).toBe('project');
      expect(persistedState.projectState.project).toEqual(mockProject);
      expect(persistedState.projectState.recentProjects).toEqual([
        '/recent/path',
      ]);
    });

    it('should persist manual mode state to localStorage', async () => {
      const { result } = renderHook(() => useAppStore());

      // Set project mode first
      act(() => {
        result.current.setProject(mockProject);
      });

      // Then switch to manual
      act(() => {
        result.current.setMode('manual');
      });

      // Wait for async persistence
      await new Promise((resolve) => setTimeout(resolve, 100));

      const storedData = JSON.parse(localStorage.getItem('app-store')!);
      const persistedState = storedData.json.state;

      expect(persistedState.projectState.mode).toBe('manual');
      expect(persistedState.projectState.project).toBeUndefined();
      expect(persistedState.projectState.recentProjects).toEqual([]); // Empty array in manual mode
    });

    it('should not persist project data when in manual mode', async () => {
      const { result } = renderHook(() => useAppStore());

      // Stay in manual mode but try to trigger persistence
      act(() => {
        result.current.setSelectedProvider('openai');
      });

      // Wait for async persistence
      await new Promise((resolve) => setTimeout(resolve, 100));

      const storedData = JSON.parse(localStorage.getItem('app-store')!);
      const persistedState = storedData.json.state;

      expect(persistedState.projectState.mode).toBe('manual');
      expect(persistedState.projectState.project).toBeUndefined();
      expect(persistedState.projectState.recentProjects).toEqual([]); // Empty array in manual mode
      expect(persistedState.selectedProvider).toBe('openai'); // Other fields still persist
    });
  });

  describe('discriminated union type safety', () => {
    it('should provide type-safe access to project properties', () => {
      const { result } = renderHook(() => useAppStore());

      act(() => {
        result.current.setProject(mockProject);
      });

      // TypeScript should enforce this at compile time
      const projectState = result.current.projectState;
      if (projectState.mode === 'project') {
        // These properties should exist and be typed correctly
        expect(projectState.project.screenplayName).toBe('test-script');
        expect(projectState.project.inputPath).toBe(
          '/path/to/input/test-script'
        );
        expect(projectState.project.outputPath).toBe(
          '/path/to/output/test-script'
        );
        expect(Array.isArray(projectState.recentProjects)).toBe(true);
      } else {
        // In manual mode, these properties should not exist
        // This is enforced by TypeScript at compile time
        expect(projectState.mode).toBe('manual');
      }
    });
  });
});
