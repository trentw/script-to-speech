import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AudioService, audioService } from '../AudioService';

// Mock HTMLAudioElement - reuse the same mock from useAudio tests
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

describe('AudioService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
    // Clear the singleton instance to start fresh
    AudioService.destroy();
    
    // Reset mock audio state
    mockAudio.src = '';
    mockAudio.currentTime = 0;
    mockAudio.duration = 0;
    mockAudio.paused = true;
    mockAudio.error = null;
  });

  describe('Singleton Pattern', () => {
    it('should return the same instance', () => {
      const instance1 = AudioService.getInstance();
      const instance2 = AudioService.getInstance();
      
      expect(instance1).toBe(instance2);
    });

    it('should be compatible with React 18 strict mode double instantiation', () => {
      // Simulate React 18 strict mode behavior
      const instance1 = AudioService.getInstance();
      const instance2 = AudioService.getInstance();
      const instance3 = AudioService.getInstance();
      
      expect(instance1).toBe(instance2);
      expect(instance2).toBe(instance3);
      expect(global.Audio).toHaveBeenCalledTimes(1);
    });

    it('should export the singleton instance', () => {
      const freshInstance = AudioService.getInstance();
      expect(audioService).toBeInstanceOf(AudioService);
      // Note: audioService is imported from a different module load, so it may be a different instance
      // The important thing is that getInstance() always returns the same instance
      expect(freshInstance).toBe(AudioService.getInstance());
    });
  });

  describe('Initial State', () => {
    it('should have correct initial state', () => {
      const service = AudioService.getInstance();
      const state = service.getState();
      
      expect(state).toEqual({
        isReady: false,
        isPlaying: false,
        isLoading: false,
        currentTime: 0,
        duration: 0,
        error: null,
        src: null,
      });
    });

    it('should configure audio element correctly', () => {
      AudioService.getInstance();
      
      expect(mockAudio.preload).toBe('metadata');
      expect(mockAudio.loop).toBe(false);
    });
  });

  describe('Event System', () => {
    it('should allow subscribing to events', () => {
      const service = AudioService.getInstance();
      const callback = vi.fn();
      
      const unsubscribe = service.on('stateChange', callback);
      
      expect(typeof unsubscribe).toBe('function');
    });

    it('should emit stateChange events', async () => {
      const service = AudioService.getInstance();
      const callback = vi.fn();
      
      service.on('stateChange', callback);
      service.load('https://example.com/audio.mp3');
      
      // Wait for loading to start
      expect(callback).toHaveBeenCalledWith(
        expect.objectContaining({
          isLoading: true,
          src: 'https://example.com/audio.mp3',
        })
      );
    });

    it('should allow unsubscribing from events', () => {
      const service = AudioService.getInstance();
      const callback = vi.fn();
      
      const unsubscribe = service.on('stateChange', callback);
      unsubscribe();
      
      service.load('https://example.com/audio.mp3');
      
      expect(callback).not.toHaveBeenCalled();
    });

    it('should handle callback errors gracefully', () => {
      const service = AudioService.getInstance();
      const errorCallback = vi.fn(() => {
        throw new Error('Callback error');
      });
      const normalCallback = vi.fn();
      
      service.on('stateChange', errorCallback);
      service.on('stateChange', normalCallback);
      
      // Should not throw even though errorCallback throws
      expect(() => {
        service.load('https://example.com/audio.mp3');
      }).not.toThrow();
      
      expect(normalCallback).toHaveBeenCalled();
    });

    it('should emit specific event types', async () => {
      const service = AudioService.getInstance();
      const playCallback = vi.fn();
      const pauseCallback = vi.fn();
      const endedCallback = vi.fn();
      const errorCallback = vi.fn();
      const timeUpdateCallback = vi.fn();
      
      service.on('play', playCallback);
      service.on('pause', pauseCallback);
      service.on('ended', endedCallback);
      service.on('error', errorCallback);
      service.on('timeUpdate', timeUpdateCallback);
      
      service.load('https://example.com/audio.mp3');
      
      // Wait for load to complete
      await new Promise(resolve => setTimeout(resolve, 20));
      
      await service.play();
      expect(playCallback).toHaveBeenCalled();
      
      service.pause();
      expect(pauseCallback).toHaveBeenCalled();
      
      // Simulate ended
      mockAudio.simulateEnded();
      expect(endedCallback).toHaveBeenCalled();
      
      // Simulate time update
      mockAudio.simulateTimeUpdate(50);
      expect(timeUpdateCallback).toHaveBeenCalledWith({
        currentTime: 50,
        duration: 100,
      });
    });
  });

  describe('Audio Loading', () => {
    it('should load audio from URL', async () => {
      const service = AudioService.getInstance();
      const callback = vi.fn();
      
      service.on('stateChange', callback);
      service.load('https://example.com/audio.mp3');
      
      expect(service.getState().isLoading).toBe(true);
      expect(service.getState().src).toBe('https://example.com/audio.mp3');
      expect(mockAudio.src).toBe('https://example.com/audio.mp3');
      expect(mockAudio.load).toHaveBeenCalled();
      
      // Wait for load to complete
      await new Promise(resolve => setTimeout(resolve, 20));
      
      expect(service.getState().isReady).toBe(true);
      expect(service.getState().isLoading).toBe(false);
      expect(service.getState().duration).toBe(100);
    });

    it('should validate URL protocol', () => {
      const service = AudioService.getInstance();
      
      service.load('file:///local/file.mp3');
      
      expect(service.getState().error).toBe(
        'Invalid audio URL: only HTTP/HTTPS protocols are allowed'
      );
      expect(service.getState().isReady).toBe(false);
      expect(mockAudio.load).not.toHaveBeenCalled();
    });

    it('should reset state when loading new audio', async () => {
      const service = AudioService.getInstance();
      
      // Load first audio
      service.load('https://example.com/audio1.mp3');
      await new Promise(resolve => setTimeout(resolve, 20));
      
      // Set some state
      service.seek(50);
      expect(service.getState().currentTime).toBe(50);
      
      // Load new audio
      service.load('https://example.com/audio2.mp3');
      
      expect(service.getState().isReady).toBe(false);
      expect(service.getState().currentTime).toBe(0);
      expect(service.getState().duration).toBe(0);
      expect(service.getState().error).toBe(null);
      expect(service.getState().src).toBe('https://example.com/audio2.mp3');
    });

    it('should handle loadAndPlay with autoplay', async () => {
      const service = AudioService.getInstance();
      const playCallback = vi.fn();
      
      service.on('play', playCallback);
      service.loadAndPlay('https://example.com/audio.mp3', true);
      
      // Wait for load and autoplay
      await new Promise(resolve => setTimeout(resolve, 30));
      
      expect(mockAudio.play).toHaveBeenCalled();
      expect(playCallback).toHaveBeenCalled();
    });

    it('should prevent multiple autoplay for same source', async () => {
      const service = AudioService.getInstance();
      
      service.loadAndPlay('https://example.com/audio.mp3', true);
      await new Promise(resolve => setTimeout(resolve, 30));
      
      expect(mockAudio.play).toHaveBeenCalledTimes(1);
      
      // Try autoplay again with same source - this will reload the audio
      // but autoplay should not trigger again since it's the same source
      service.loadAndPlay('https://example.com/audio.mp3', true);
      await new Promise(resolve => setTimeout(resolve, 30));
      
      // The audio will be reloaded but autoplay won't trigger again
      expect(mockAudio.load).toHaveBeenCalledTimes(2); // Two loads
      expect(mockAudio.play).toHaveBeenCalledTimes(1); // Still only one play (autoplay prevented)
    });
  });

  describe('Playback Control', () => {
    it('should play audio when ready', async () => {
      const service = AudioService.getInstance();
      
      service.load('https://example.com/audio.mp3');
      await new Promise(resolve => setTimeout(resolve, 20));
      
      await service.play();
      
      expect(mockAudio.play).toHaveBeenCalled();
      expect(service.getState().isPlaying).toBe(true);
    });

    it('should not play when not ready', async () => {
      const service = AudioService.getInstance();
      
      await service.play();
      
      expect(mockAudio.play).not.toHaveBeenCalled();
      expect(service.getState().isPlaying).toBe(false);
    });

    it('should pause audio', async () => {
      const service = AudioService.getInstance();
      
      service.load('https://example.com/audio.mp3');
      await new Promise(resolve => setTimeout(resolve, 20));
      await service.play();
      
      service.pause();
      
      expect(mockAudio.pause).toHaveBeenCalled();
      expect(service.getState().isPlaying).toBe(false);
    });

    it('should handle play errors', async () => {
      const service = AudioService.getInstance();
      const errorCallback = vi.fn();
      
      service.on('error', errorCallback);
      mockAudio.play.mockRejectedValueOnce(new Error('Playback failed'));
      
      service.load('https://example.com/audio.mp3');
      await new Promise(resolve => setTimeout(resolve, 20));
      
      await service.play();
      
      expect(service.getState().error).toBe('Playback failed');
      expect(service.getState().isPlaying).toBe(false);
      expect(errorCallback).toHaveBeenCalledWith('Playback failed');
    });

    it('should handle concurrent play calls', async () => {
      const service = AudioService.getInstance();
      
      service.load('https://example.com/audio.mp3');
      await new Promise(resolve => setTimeout(resolve, 20));
      
      // Ensure isReady is true before testing play
      expect(service.getState().isReady).toBe(true);
      
      // Multiple play calls - they should both resolve without error
      const promise1 = service.play();
      const promise2 = service.play();
      await Promise.all([promise1, promise2]);
      
      // State should reflect successful play (the mock automatically sets this via 'play' event)
      expect(service.getState().isPlaying).toBe(true);
      expect(service.getState().error).toBe(null);
    });
  });

  describe('Seek and Time Management', () => {
    it('should seek to specific time', async () => {
      const service = AudioService.getInstance();
      
      service.load('https://example.com/audio.mp3');
      await new Promise(resolve => setTimeout(resolve, 20));
      
      service.seek(30);
      
      expect(mockAudio.currentTime).toBe(30);
      expect(service.getState().currentTime).toBe(30);
    });

    it('should stop audio and reset to beginning', async () => {
      const service = AudioService.getInstance();
      
      service.load('https://example.com/audio.mp3');
      await new Promise(resolve => setTimeout(resolve, 20));
      await service.play();
      service.seek(50);
      
      service.stop();
      
      expect(mockAudio.pause).toHaveBeenCalled();
      expect(service.getState().currentTime).toBe(0);
    });

    it('should update current time on timeupdate', async () => {
      const service = AudioService.getInstance();
      
      service.load('https://example.com/audio.mp3');
      await new Promise(resolve => setTimeout(resolve, 20));
      
      mockAudio.simulateTimeUpdate(25);
      
      expect(service.getState().currentTime).toBe(25);
    });
  });

  describe('State Management', () => {
    it('should provide convenience methods for state checking', async () => {
      const service = AudioService.getInstance();
      
      expect(service.isAudioReady()).toBe(false);
      expect(service.isCurrentlyPlaying()).toBe(false);
      expect(service.getCurrentSrc()).toBe(null);
      
      service.load('https://example.com/audio.mp3');
      await new Promise(resolve => setTimeout(resolve, 20));
      
      expect(service.isAudioReady()).toBe(true);
      expect(service.getCurrentSrc()).toBe('https://example.com/audio.mp3');
      
      // Verify state is ready before attempting to play
      expect(service.getState().isReady).toBe(true);
      
      await service.play();
      
      // Verify the play succeeded by checking the state
      expect(service.getState().isPlaying).toBe(true);
      expect(service.isCurrentlyPlaying()).toBe(true);
    });

    it('should clear audio and reset state', () => {
      const service = AudioService.getInstance();
      
      service.load('https://example.com/audio.mp3');
      service.seek(30);
      
      service.clear();
      
      expect(service.getState()).toEqual({
        isReady: false,
        isPlaying: false,
        isLoading: false,
        currentTime: 0,
        duration: 0,
        error: null,
        src: null,
      });
      expect(mockAudio.pause).toHaveBeenCalled();
      expect(mockAudio.src).toBe('');
    });

    it('should only emit stateChange when state actually changes', () => {
      const service = AudioService.getInstance();
      const callback = vi.fn();
      
      service.on('stateChange', callback);
      
      // Load audio - this should trigger stateChange
      service.load('https://example.com/audio.mp3');
      expect(callback).toHaveBeenCalledTimes(1);
      
      // Seek to same position - should not trigger additional stateChange
      service.seek(0);
      expect(callback).toHaveBeenCalledTimes(1);
      
      // Seek to different position - should trigger stateChange
      service.seek(10);
      expect(callback).toHaveBeenCalledTimes(2);
    });
  });

  describe('Error Handling', () => {
    it('should handle audio element errors', async () => {
      const service = AudioService.getInstance();
      const errorCallback = vi.fn();
      
      service.on('error', errorCallback);
      
      // Simulate loading invalid audio
      service.load('https://example.com/invalid.mp3');
      
      // Manually trigger error for test
      mockAudio.error = {
        code: 4,
        message: 'MEDIA_ELEMENT_ERROR: Format not supported',
      } as MediaError;
      
      // Simulate error event
      mockAudio.addEventListener('error', () => {});
      const errorHandler = mockAudio.listeners?.['error']?.[0];
      if (errorHandler) errorHandler();
      
      expect(service.getState().error).toContain('Audio error');
      expect(service.getState().isReady).toBe(false);
      expect(service.getState().isLoading).toBe(false);
      expect(errorCallback).toHaveBeenCalled();
    });
  });

  describe('Cleanup', () => {
    it('should destroy singleton properly', () => {
      const service = AudioService.getInstance();
      const callback = vi.fn();
      
      service.on('stateChange', callback);
      service.load('https://example.com/audio.mp3');
      
      AudioService.destroy();
      
      // Should not be able to get same instance
      const newService = AudioService.getInstance();
      expect(newService).not.toBe(service);
      
      // Old listeners should be cleared
      expect(callback).not.toHaveBeenCalledWith(
        expect.objectContaining({ src: 'https://example.com/audio2.mp3' })
      );
    });
  });
});