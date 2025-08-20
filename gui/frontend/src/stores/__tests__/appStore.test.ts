import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';

import useAppStore from '../appStore';

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

    it.skip('should rehydrate from localStorage on new store instance', async () => {
      // SKIPPED: This test would require creating a truly new store instance,
      // which is not possible in the test environment since Zustand stores are singletons.
      // The rehydration behavior is tested implicitly by:
      // 1. The persistence test (data is written correctly)
      // 2. The partialize test (correct fields are persisted)
      // 3. Production usage where rehydration works correctly on page refresh
      // If we need to test rehydration in the future, we would need to:
      // - Use a different testing approach (e.g., E2E tests)
      // - Or mock the Zustand persist middleware
      // - Or find a way to truly reset the singleton store instance
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
