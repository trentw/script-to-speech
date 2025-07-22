import { act, renderHook, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { server } from '@/test/setup'
import { TEST_VOICES } from '@/test/utils/test-data'

import { useVoiceLibrary } from '../useVoiceLibrary'

const mockApiService = {
  getProviderVoices: vi.fn(),
}

// Mock the apiService module
vi.mock('../../services/api', () => ({
  apiService: {
    getProviderVoices: (provider: string) => mockApiService.getProviderVoices(provider),
  },
}))

describe('useVoiceLibrary Hook', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Successful Data Fetching', () => {
    it('should load voice library when provider is set and connected', async () => {
      // Arrange
      mockApiService.getProviderVoices.mockResolvedValue({
        data: TEST_VOICES,
        error: null,
      })

      // Act
      const { result } = renderHook(() =>
        useVoiceLibrary('connected', 'elevenlabs')
      )

      // Assert - initial state
      expect(result.current.voiceLibrary).toEqual({})

      // Wait for effect to run
      await waitFor(() => {
        expect(mockApiService.getProviderVoices).toHaveBeenCalledWith('elevenlabs')
      })

      // Assert - after successful fetch
      await waitFor(() => {
        expect(result.current.voiceLibrary.elevenlabs).toEqual(TEST_VOICES)
      })
    })

    it('should not fetch when provider is not provided', async () => {
      // Act
      const { result } = renderHook(() => useVoiceLibrary('connected', undefined))

      // Assert
      await waitFor(() => {
        expect(result.current.voiceLibrary).toEqual({})
      })
      expect(mockApiService.getProviderVoices).not.toHaveBeenCalled()
    })

    it('should not fetch when connection status is not connected', async () => {
      // Act - checking status
      const { result: checkingResult } = renderHook(() =>
        useVoiceLibrary('checking', 'elevenlabs')
      )

      // Act - disconnected status
      const { result: disconnectedResult } = renderHook(() =>
        useVoiceLibrary('disconnected', 'elevenlabs')
      )

      // Assert
      await waitFor(() => {
        expect(checkingResult.current.voiceLibrary).toEqual({})
        expect(disconnectedResult.current.voiceLibrary).toEqual({})
      })
      expect(mockApiService.getProviderVoices).not.toHaveBeenCalled()
    })

    it('should not refetch if voice library is already loaded', async () => {
      // Arrange
      mockApiService.getProviderVoices.mockResolvedValue({
        data: TEST_VOICES,
        error: null,
      })

      // Act - initial render
      const { result, rerender } = renderHook(
        ({ status, provider }) => useVoiceLibrary(status, provider),
        {
          initialProps: {
            status: 'connected' as const,
            provider: 'elevenlabs',
          },
        }
      )

      // Wait for initial fetch
      await waitFor(() => {
        expect(result.current.voiceLibrary.elevenlabs).toEqual(TEST_VOICES)
      })
      expect(mockApiService.getProviderVoices).toHaveBeenCalledTimes(1)

      // Act - rerender with same provider
      rerender({ status: 'connected', provider: 'elevenlabs' })

      // Assert - should not fetch again
      await waitFor(() => {
        expect(mockApiService.getProviderVoices).toHaveBeenCalledTimes(1)
      })
    })

    it('should support manual loading of voice library', async () => {
      // Arrange
      mockApiService.getProviderVoices.mockResolvedValue({
        data: TEST_VOICES,
        error: null,
      })

      // Act
      const { result } = renderHook(() => useVoiceLibrary('connected'))

      // Manually load voice library
      await act(async () => {
        await result.current.loadVoiceLibrary('openai')
      })

      // Assert
      expect(mockApiService.getProviderVoices).toHaveBeenCalledWith('openai')
      expect(result.current.voiceLibrary.openai).toEqual(TEST_VOICES)
    })

    it('should handle multiple providers', async () => {
      // Arrange
      const openaiVoices = [
        { voice_id: 'alloy', name: 'Alloy', provider: 'openai' },
      ]
      const elevenLabsVoices = TEST_VOICES

      mockApiService.getProviderVoices
        .mockResolvedValueOnce({ data: openaiVoices, error: null })
        .mockResolvedValueOnce({ data: elevenLabsVoices, error: null })

      // Act
      const { result } = renderHook(() => useVoiceLibrary('connected'))

      // Load multiple providers
      await act(async () => {
        await result.current.loadVoiceLibrary('openai')
        await result.current.loadVoiceLibrary('elevenlabs')
      })

      // Assert
      expect(result.current.voiceLibrary).toEqual({
        openai: openaiVoices,
        elevenlabs: elevenLabsVoices,
      })
    })
  })

  describe('Error Handling', () => {
    it('should handle API errors gracefully', async () => {
      // Arrange
      mockApiService.getProviderVoices.mockResolvedValue({
        data: null,
        error: 'Failed to fetch voices',
      })

      // Act
      const { result } = renderHook(() =>
        useVoiceLibrary('connected', 'elevenlabs')
      )

      // Assert
      await waitFor(() => {
        expect(mockApiService.getProviderVoices).toHaveBeenCalled()
      })

      // Voice library should remain empty on error
      expect(result.current.voiceLibrary).toEqual({})
    })

    it('should handle API exceptions', async () => {
      // Arrange
      mockApiService.getProviderVoices.mockRejectedValue(
        new Error('Network error')
      )

      // Act
      const { result } = renderHook(() =>
        useVoiceLibrary('connected', 'elevenlabs')
      )

      // Assert - should not throw
      await waitFor(() => {
        expect(mockApiService.getProviderVoices).toHaveBeenCalled()
      })

      expect(result.current.voiceLibrary).toEqual({})
      
      // Clear the rejected promise to avoid unhandled rejection
      await vi.waitFor(() => {
        // Wait for any pending promises to settle
        return true
      })
    })
  })

  describe('Provider Changes', () => {
    it('should fetch new provider when provider changes', async () => {
      // Arrange
      const openaiVoices = [
        { voice_id: 'alloy', name: 'Alloy', provider: 'openai' },
      ]
      const elevenLabsVoices = TEST_VOICES

      mockApiService.getProviderVoices
        .mockResolvedValueOnce({ data: openaiVoices, error: null })
        .mockResolvedValueOnce({ data: elevenLabsVoices, error: null })

      // Act - initial provider
      const { result, rerender } = renderHook(
        ({ status, provider }) => useVoiceLibrary(status, provider),
        {
          initialProps: {
            status: 'connected' as const,
            provider: 'openai',
          },
        }
      )

      // Wait for initial fetch
      await waitFor(() => {
        expect(result.current.voiceLibrary.openai).toEqual(openaiVoices)
      })

      // Act - change provider
      rerender({ status: 'connected', provider: 'elevenlabs' })

      // Assert - should fetch new provider
      await waitFor(() => {
        expect(result.current.voiceLibrary.elevenlabs).toEqual(elevenLabsVoices)
      })

      expect(mockApiService.getProviderVoices).toHaveBeenCalledTimes(2)
      expect(mockApiService.getProviderVoices).toHaveBeenNthCalledWith(1, 'openai')
      expect(mockApiService.getProviderVoices).toHaveBeenNthCalledWith(2, 'elevenlabs')
    })
  })

  describe('Dependency Array Behavior', () => {
    it('should not cause infinite loops with stable callback', async () => {
      // Arrange
      mockApiService.getProviderVoices.mockResolvedValue({
        data: TEST_VOICES,
        error: null,
      })

      let renderCount = 0

      // Act
      const { result } = renderHook(() => {
        renderCount++
        return useVoiceLibrary('connected', 'elevenlabs')
      })

      // Wait for effect to complete
      await waitFor(() => {
        expect(result.current.voiceLibrary.elevenlabs).toEqual(TEST_VOICES)
      })

      // Assert - should only render twice (initial + after state update)
      expect(renderCount).toBeLessThanOrEqual(3)
    })
  })
})