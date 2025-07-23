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
    state.clearAudio();
    state.resetScreenplayState();
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
    it('should persist configuration slice to localStorage', () => {
      // Arrange
      const { result } = renderHook(() => useAppStore());
      const testVoice = {
        sts_id: 'cartesia:sarah',
        provider: 'cartesia',
        config: { voice: 'sarah' },
      };

      // Act
      act(() => {
        result.current.setSelectedProvider('cartesia');
        result.current.setSelectedVoice(testVoice);
      });

      // Assert - check localStorage with correct key
      const storedState = JSON.parse(
        localStorage.getItem('sts-app-store') || '{}'
      );
      expect(storedState.state.selectedProvider).toBe('cartesia');
      expect(storedState.state.selectedVoice).toEqual(testVoice);
    });

    it('should not persist UI and user input slices', () => {
      // Arrange
      const { result } = renderHook(() => useAppStore());

      // Act
      act(() => {
        result.current.setText('Temporary text');
        result.current.setError('Temporary error');
      });

      // Assert - check localStorage doesn't contain these values with correct key
      const storedState = JSON.parse(
        localStorage.getItem('sts-app-store') || '{}'
      );
      expect(storedState.state?.text).toBeUndefined();
      expect(storedState.state?.error).toBeUndefined();
    });
  });
});
