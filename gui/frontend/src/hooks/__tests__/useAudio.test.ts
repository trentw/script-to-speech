import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useAudio } from '../useAudio';

// Mock HTMLAudioElement
class MockAudioElement {
  src: string = '';
  preload: string = 'none';
  loop: boolean = false;
  currentTime: number = 0;
  duration: number = 0;
  paused: boolean = true;
  error: MediaError | null = null;

  // Event listeners
  private listeners: Record<string, ((...args: unknown[]) => void)[]> = {};

  addEventListener(event: string, handler: (...args: unknown[]) => void) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(handler);
  }

  removeEventListener(event: string, handler: (...args: unknown[]) => void) {
    if (this.listeners[event]) {
      this.listeners[event] = this.listeners[event].filter(
        (h) => h !== handler
      );
    }
  }

  private emit(event: string) {
    if (this.listeners[event]) {
      this.listeners[event].forEach((handler) => handler());
    }
  }

  play = vi.fn().mockImplementation(() => {
    this.paused = false;
    this.emit('play');
    return Promise.resolve();
  });

  pause = vi.fn().mockImplementation(() => {
    this.paused = true;
    this.emit('pause');
  });

  load = vi.fn().mockImplementation(() => {
    this.emit('loadstart');
    // Simulate async loading
    setTimeout(() => {
      if (this.src && this.src.startsWith('http')) {
        this.duration = 100; // Mock duration
        this.emit('loadedmetadata');
        this.emit('canplay');
      } else if (this.src) {
        // Invalid URL
        this.error = {
          code: 4,
          message: 'MEDIA_ELEMENT_ERROR: Format not supported',
        } as MediaError;
        this.emit('error');
      }
    }, 10);
  });

  // Simulate time update
  simulateTimeUpdate(time: number) {
    this.currentTime = time;
    this.emit('timeupdate');
  }

  // Simulate end
  simulateEnded() {
    this.paused = true;
    this.currentTime = 0;
    this.emit('ended');
  }
}

// Replace global Audio constructor
const mockAudio = new MockAudioElement();
global.Audio = vi.fn(() => mockAudio) as unknown as typeof Audio;

describe('useAudio Hook', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset mock audio state
    mockAudio.src = '';
    mockAudio.currentTime = 0;
    mockAudio.duration = 0;
    mockAudio.paused = true;
    mockAudio.error = null;
  });

  describe('Initialization', () => {
    it('should initialize with default values', () => {
      // Act
      const { result } = renderHook(() => useAudio());

      // Assert
      expect(result.current.isReady).toBe(false);
      expect(result.current.isPlaying).toBe(false);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.currentTime).toBe(0);
      expect(result.current.duration).toBe(0);
      expect(result.current.error).toBe(null);
    });

    it('should create audio element only once', () => {
      // Act
      const { rerender } = renderHook(() => useAudio());

      // Rerender multiple times
      rerender();
      rerender();
      rerender();

      // Assert
      expect(global.Audio).toHaveBeenCalledTimes(1);
    });

    it('should set preload and loop attributes', () => {
      // Act
      renderHook(() => useAudio());

      // Assert
      expect(mockAudio.preload).toBe('metadata');
      expect(mockAudio.loop).toBe(false);
    });
  });

  describe('Loading Audio', () => {
    it('should load audio from URL', async () => {
      // Act
      const { result } = renderHook(() =>
        useAudio({ src: 'https://example.com/audio.mp3' })
      );

      // Assert - loading state
      expect(result.current.isLoading).toBe(true);
      expect(result.current.isReady).toBe(false);

      // Wait for load to complete
      await waitFor(() => {
        expect(result.current.isReady).toBe(true);
      });

      // Assert - ready state
      expect(result.current.isLoading).toBe(false);
      expect(result.current.duration).toBe(100);
      expect(result.current.error).toBe(null);
      expect(mockAudio.src).toBe('https://example.com/audio.mp3');
    });

    it('should handle load method', async () => {
      // Act
      const { result } = renderHook(() => useAudio());

      act(() => {
        result.current.load('https://example.com/new-audio.mp3');
      });

      // Assert
      expect(result.current.isLoading).toBe(true);
      expect(mockAudio.load).toHaveBeenCalled();

      await waitFor(() => {
        expect(result.current.isReady).toBe(true);
      });

      expect(mockAudio.src).toBe('https://example.com/new-audio.mp3');
    });

    it('should validate URL protocol', () => {
      // Act
      const { result } = renderHook(() => useAudio());

      act(() => {
        result.current.load('file:///local/file.mp3');
      });

      // Assert
      expect(result.current.error).toBe(
        'Invalid audio URL: only HTTP/HTTPS protocols are allowed'
      );
      expect(result.current.isReady).toBe(false);
      expect(mockAudio.load).not.toHaveBeenCalled();
    });

    it('should clear state when loading new audio', async () => {
      // Arrange - load first audio
      const { result } = renderHook(() =>
        useAudio({ src: 'https://example.com/audio1.mp3' })
      );

      await waitFor(() => {
        expect(result.current.isReady).toBe(true);
      });

      // Set some state
      act(() => {
        mockAudio.simulateTimeUpdate(50);
      });

      expect(result.current.currentTime).toBe(50);

      // Act - load new audio
      act(() => {
        result.current.load('https://example.com/audio2.mp3');
      });

      // Assert - state should be reset
      expect(result.current.isReady).toBe(false);
      expect(result.current.currentTime).toBe(0);
      expect(result.current.duration).toBe(0);
      expect(result.current.error).toBe(null);
    });

    it('should handle empty src', () => {
      // Act
      const { result, rerender } = renderHook(({ src }) => useAudio({ src }), {
        initialProps: { src: 'https://example.com/audio.mp3' },
      });

      // Change to empty src
      rerender({ src: undefined });

      // Assert
      expect(result.current.isReady).toBe(false);
      expect(result.current.error).toBe(null);
      expect(mockAudio.pause).toHaveBeenCalled();
    });
  });

  describe('Playback Control', () => {
    it('should play audio when ready', async () => {
      // Arrange
      const { result } = renderHook(() =>
        useAudio({ src: 'https://example.com/audio.mp3' })
      );

      await waitFor(() => {
        expect(result.current.isReady).toBe(true);
      });

      // Act
      await act(async () => {
        await result.current.play();
      });

      // Assert
      expect(mockAudio.play).toHaveBeenCalled();
      expect(result.current.isPlaying).toBe(true);
    });

    it('should not play when not ready', async () => {
      // Act
      const { result } = renderHook(() => useAudio());

      await act(async () => {
        await result.current.play();
      });

      // Assert
      expect(mockAudio.play).not.toHaveBeenCalled();
      expect(result.current.isPlaying).toBe(false);
    });

    it('should pause audio', async () => {
      // Arrange
      const { result } = renderHook(() =>
        useAudio({ src: 'https://example.com/audio.mp3' })
      );

      await waitFor(() => {
        expect(result.current.isReady).toBe(true);
      });

      await act(async () => {
        await result.current.play();
      });

      // Act
      act(() => {
        result.current.pause();
      });

      // Assert
      expect(mockAudio.pause).toHaveBeenCalled();
      expect(result.current.isPlaying).toBe(false);
    });

    it('should handle play errors', async () => {
      // Arrange
      mockAudio.play.mockRejectedValueOnce(new Error('Playback failed'));

      const { result } = renderHook(() =>
        useAudio({ src: 'https://example.com/audio.mp3' })
      );

      await waitFor(() => {
        expect(result.current.isReady).toBe(true);
      });

      // Act
      await act(async () => {
        await result.current.play();
      });

      // Assert
      expect(result.current.error).toBe('Playback failed');
      expect(result.current.isPlaying).toBe(false);
    });

    it('should handle autoplay', async () => {
      // Act
      const { result } = renderHook(() =>
        useAudio({ src: 'https://example.com/audio.mp3', autoplay: true })
      );

      // Wait for ready and autoplay
      await waitFor(() => {
        expect(result.current.isPlaying).toBe(true);
      });

      // Assert
      expect(mockAudio.play).toHaveBeenCalled();
    });

    it('should autoplay only once per src', async () => {
      // Arrange
      const { result, rerender } = renderHook(
        ({ src, autoplay }) => useAudio({ src, autoplay }),
        {
          initialProps: {
            src: 'https://example.com/audio.mp3',
            autoplay: true,
          },
        }
      );

      await waitFor(() => {
        expect(result.current.isPlaying).toBe(true);
      });

      expect(mockAudio.play).toHaveBeenCalledTimes(1);

      // Rerender with same src
      rerender({ src: 'https://example.com/audio.mp3', autoplay: true });

      // Should not play again
      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 50));
      });

      expect(mockAudio.play).toHaveBeenCalledTimes(1);
    });
  });

  describe('Seek Functionality', () => {
    it('should seek to specific time', async () => {
      // Arrange
      const { result } = renderHook(() =>
        useAudio({ src: 'https://example.com/audio.mp3' })
      );

      await waitFor(() => {
        expect(result.current.isReady).toBe(true);
      });

      // Act
      act(() => {
        result.current.seek(30);
      });

      // Assert
      expect(mockAudio.currentTime).toBe(30);
      expect(result.current.currentTime).toBe(30);
    });
  });

  describe('Event Handling', () => {
    it('should update current time on timeupdate', async () => {
      // Arrange
      const { result } = renderHook(() =>
        useAudio({ src: 'https://example.com/audio.mp3' })
      );

      await waitFor(() => {
        expect(result.current.isReady).toBe(true);
      });

      // Act
      act(() => {
        mockAudio.simulateTimeUpdate(25);
      });

      // Assert
      expect(result.current.currentTime).toBe(25);
    });

    it('should handle ended event', async () => {
      // Arrange
      const { result } = renderHook(() =>
        useAudio({ src: 'https://example.com/audio.mp3' })
      );

      await waitFor(() => {
        expect(result.current.isReady).toBe(true);
      });

      await act(async () => {
        await result.current.play();
      });

      // Act
      act(() => {
        mockAudio.simulateEnded();
      });

      // Assert
      expect(result.current.isPlaying).toBe(false);
      expect(result.current.currentTime).toBe(0);
    });

    it('should handle error event', async () => {
      // Act
      const { result } = renderHook(() => useAudio());

      act(() => {
        result.current.load('invalid-url');
      });

      // Wait for error
      await waitFor(() => {
        expect(result.current.error).toBeTruthy();
      });

      // Assert - hook validates URL before loading
      expect(result.current.error).toBe(
        'Invalid audio URL: only HTTP/HTTPS protocols are allowed'
      );
      expect(result.current.isReady).toBe(false);
      expect(result.current.isLoading).toBe(false);
    });
  });

  describe('Cleanup', () => {
    it('should remove event listeners on unmount', async () => {
      // Arrange
      const removeEventListenerSpy = vi.spyOn(mockAudio, 'removeEventListener');

      // Act
      const { unmount } = renderHook(() =>
        useAudio({ src: 'https://example.com/audio.mp3' })
      );

      await waitFor(() => {
        expect(mockAudio.load).toHaveBeenCalled();
      });

      unmount();

      // Assert
      expect(mockAudio.pause).toHaveBeenCalled();
      expect(removeEventListenerSpy).toHaveBeenCalledWith(
        'loadedmetadata',
        expect.any(Function)
      );
      expect(removeEventListenerSpy).toHaveBeenCalledWith(
        'timeupdate',
        expect.any(Function)
      );
      expect(removeEventListenerSpy).toHaveBeenCalledWith(
        'play',
        expect.any(Function)
      );
      expect(removeEventListenerSpy).toHaveBeenCalledWith(
        'pause',
        expect.any(Function)
      );
      expect(removeEventListenerSpy).toHaveBeenCalledWith(
        'ended',
        expect.any(Function)
      );
      expect(removeEventListenerSpy).toHaveBeenCalledWith(
        'error',
        expect.any(Function)
      );
      expect(removeEventListenerSpy).toHaveBeenCalledWith(
        'loadstart',
        expect.any(Function)
      );
      expect(removeEventListenerSpy).toHaveBeenCalledWith(
        'canplay',
        expect.any(Function)
      );
    });

    it('should pause audio on unmount', async () => {
      // Arrange
      const { result, unmount } = renderHook(() =>
        useAudio({ src: 'https://example.com/audio.mp3' })
      );

      await waitFor(() => {
        expect(result.current.isReady).toBe(true);
      });

      await act(async () => {
        await result.current.play();
      });

      // Act
      unmount();

      // Assert
      expect(mockAudio.pause).toHaveBeenCalled();
    });
  });

  describe('Edge Cases', () => {
    it('should handle rapid src changes', async () => {
      // Act
      const { result } = renderHook(() => useAudio());

      // Rapidly change sources
      act(() => {
        result.current.load('https://example.com/audio1.mp3');
        result.current.load('https://example.com/audio2.mp3');
        result.current.load('https://example.com/audio3.mp3');
      });

      // Assert - should load last one
      expect(mockAudio.src).toBe('https://example.com/audio3.mp3');
      expect(mockAudio.load).toHaveBeenCalledTimes(3);
    });

    it('should handle concurrent play calls', async () => {
      // Arrange
      const playPromise = Promise.resolve();
      mockAudio.play.mockReturnValue(playPromise);

      const { result } = renderHook(() =>
        useAudio({ src: 'https://example.com/audio.mp3' })
      );

      await waitFor(() => {
        expect(result.current.isReady).toBe(true);
      });

      // Act - multiple play calls
      await act(async () => {
        const promise1 = result.current.play();
        const promise2 = result.current.play();
        await Promise.all([promise1, promise2]);
      });

      // Assert - should handle gracefully
      expect(result.current.isPlaying).toBe(true);
      expect(result.current.error).toBe(null);
    });
  });
});
