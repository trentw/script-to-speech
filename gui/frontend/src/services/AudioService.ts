/**
 * AudioService - Command-pattern singleton with Internal Zustand Store
 *
 * This service implements the expert-recommended "AudioService with Internal Zustand Store" pattern
 * to create a single source of truth for ALL audio-related state and metadata.
 *
 * Key features:
 * - Single source of truth for audio state AND metadata
 * - Internal Zustand store for React integration and atomic updates
 * - Command pattern with unidirectional data flow
 * - Finite state machine: idle | loading | playing | paused | error
 * - Debounced commands to prevent rapid bursts
 * - Idempotent state changes
 * - No dual state management conflicts
 */

import { createStore } from 'zustand/vanilla';

// Finite state enum for clear state management
export type AudioPlaybackState =
  | 'idle'
  | 'loading'
  | 'playing'
  | 'paused'
  | 'error';

// Complete audio state including both playback and metadata
export interface AudioServiceState {
  // Audio playback state
  playbackState: AudioPlaybackState;
  currentTime: number;
  duration: number;
  error: string | null;
  src: string | null;

  // Metadata (moved from global Zustand store)
  primaryText: string;
  secondaryText: string;
  downloadFilename: string;

  // Monotonic counter incremented each time audio finishes naturally
  // (HTML 'ended' event). Consumers detect end-of-audio via subscribeEnded().
  endedCount: number;

  // Opaque token identifying which controller loaded the current source.
  // Distinct chunks can share one cached audio file (same URL), so URL
  // equality cannot tell "my clip" from "someone else's clip"; the token can.
  // Null for loads that don't claim ownership (row buttons, previews).
  ownerToken: string | null;
}

// Metadata interface for command parameters
export interface AudioMetadata {
  primaryText: string;
  secondaryText: string;
  downloadFilename?: string;
}

// Create internal Zustand store for complete audio state
const createAudioStore = () =>
  createStore<AudioServiceState>((_set) => ({
    // Audio playback state
    playbackState: 'idle' as AudioPlaybackState,
    currentTime: 0,
    duration: 0,
    error: null,
    src: null,

    // Metadata
    primaryText: '',
    secondaryText: '',
    downloadFilename: '',

    endedCount: 0,

    ownerToken: null,
  }));

class AudioService {
  private static instance: AudioService | null = null;
  private audio: HTMLAudioElement;
  private playPromise: Promise<void> | null = null;
  // Every source replacement or explicit stop advances this token. Async
  // load-and-play operations verify it before starting audio, so a pending load
  // cannot outlive a user's Stop action or a newer source selection.
  private playbackRequestId: number = 0;
  private lastCommandTime: number = 0;
  private readonly commandDebounceMs: number = 50; // Prevent rapid command bursts

  // Internal Zustand store - single source of truth for ALL audio state
  private store = createAudioStore();

  // Subscribe function for React components
  public subscribe = this.store.subscribe;
  public getState = this.store.getState;

  private constructor() {
    this.audio = new Audio();
    this.audio.preload = 'metadata';
    this.audio.loop = false;
    this.audio.volume = 1;
    this.setupHTMLAudioListeners();

    // NOTE: Memory Management Trade-off
    // The singleton pattern means this instance and its event listeners
    // persist for the application's lifetime. This is a minor memory leak
    // but acceptable for a global audio service. The alternative would be
    // multiple audio instances with complex coordination logic.
  }

  /**
   * Get the singleton instance of AudioService
   * Thread-safe implementation for React 18 strict mode
   */
  public static getInstance(): AudioService {
    if (!AudioService.instance) {
      AudioService.instance = new AudioService();
    }
    return AudioService.instance;
  }

  /**
   * Command guard - prevents rapid command bursts and ensures idempotent operations
   */
  private guardCommand(): boolean {
    const now = Date.now();
    if (now - this.lastCommandTime < this.commandDebounceMs) {
      return false; // Command rejected - too rapid
    }
    this.lastCommandTime = now;
    return true;
  }

  /**
   * Atomic state update using internal Zustand store
   */
  private updateState(updates: Partial<AudioServiceState>): void {
    this.store.setState(updates);
  }

  /**
   * Setup HTML5 Audio event listeners - READ-ONLY sources of truth
   * These listeners only update state, never trigger commands
   */
  private setupHTMLAudioListeners(): void {
    this.audio.addEventListener('loadedmetadata', this.onLoadedMetadata);
    this.audio.addEventListener('timeupdate', this.onTimeUpdate);
    this.audio.addEventListener('play', this.onPlay);
    this.audio.addEventListener('pause', this.onPause);
    this.audio.addEventListener('ended', this.onEnded);
    this.audio.addEventListener('error', this.onError);
    this.audio.addEventListener('loadstart', this.onLoadStart);
    this.audio.addEventListener('canplay', this.onCanPlay);
  }

  private onLoadedMetadata = (): void => {
    const currentState = this.store.getState();
    // Always record the real duration/position: a Stop during the load window
    // forces 'idle' before metadata arrives, and skipping the write here would
    // leave duration at 0 (breaking the transport display and seek clamping).
    this.updateState({
      duration: this.audio.duration,
      currentTime: this.audio.currentTime,
      ...(currentState.playbackState === 'loading' && {
        playbackState: 'idle' as AudioPlaybackState,
      }),
    });
  };

  private onTimeUpdate = (): void => {
    this.updateState({
      currentTime: this.audio.currentTime,
      duration: this.audio.duration,
    });
  };

  private onPlay = (): void => {
    // HTML audio started playing - update state to reflect reality
    this.updateState({ playbackState: 'playing' });
  };

  private onPause = (): void => {
    // HTML audio paused - update state to reflect reality
    const currentState = this.store.getState();
    if (currentState.playbackState === 'playing') {
      this.updateState({ playbackState: 'paused' });
    }
  };

  private onEnded = (): void => {
    // Audio finished - reset to idle state
    this.updateState({
      playbackState: 'idle',
      currentTime: 0,
      endedCount: this.store.getState().endedCount + 1,
    });
  };

  private onError = (): void => {
    const error = this.audio.error;
    let message = 'Unknown audio error';

    if (error) {
      switch (error.code) {
        case error.MEDIA_ERR_ABORTED:
          message = 'The playback was aborted by the user.';
          break;
        case error.MEDIA_ERR_NETWORK:
          message = 'A network error caused the audio download to fail.';
          break;
        case error.MEDIA_ERR_DECODE:
          message =
            'The audio playback was aborted due to a corruption problem.';
          break;
        case error.MEDIA_ERR_SRC_NOT_SUPPORTED:
          message =
            'The audio could not be loaded, either because the server or network failed or because the format is not supported.';
          break;
        default:
          message = 'An unknown error occurred.';
          break;
      }
    }

    const errorMsg = `Audio error (${error?.code || 'unknown'}): ${message}`;

    console.error('Audio error:', errorMsg, this.audio.error);

    this.updateState({
      playbackState: 'error',
      error: errorMsg,
    });
  };

  private onLoadStart = (): void => {
    // Audio started loading - transition to loading state
    this.updateState({
      playbackState: 'loading',
      error: null, // Clear previous errors
    });
  };

  private onCanPlay = (): void => {
    // Audio can play but stay in loading until metadata loads
    // onLoadedMetadata will transition to idle
  };

  /**
   * COMMAND: Load new audio source
   * Validates URL and initiates loading
   */
  public load(src: string): void {
    if (!this.guardCommand()) return;

    this.playbackRequestId += 1;

    // Validate URL for security
    if (src && !/^https?:\/\//i.test(src)) {
      this.updateState({
        playbackState: 'error',
        error: 'Invalid audio URL: only HTTP/HTTPS protocols are allowed',
      });
      return;
    }

    // Stop any current playback
    this.audio.pause();

    // Reset state for new audio
    this.updateState({
      playbackState: 'loading',
      error: null,
      currentTime: 0,
      duration: 0,
      src,
      ownerToken: null,
    });

    // Load new source (will trigger onLoadStart -> onLoadedMetadata)
    this.audio.src = src;
    this.audio.load();
  }

  /**
   * INTERNAL: Play audio without command guard
   * Used internally by atomic operations like loadAndPlay() to avoid debounce conflicts
   * Only plays if in idle or paused state
   */
  private async _play(expectedRequestId?: number): Promise<void> {
    if (
      expectedRequestId !== undefined &&
      expectedRequestId !== this.playbackRequestId
    ) {
      return;
    }
    const currentState = this.store.getState();
    // State guard - only play from idle or paused states
    if (
      currentState.playbackState !== 'idle' &&
      currentState.playbackState !== 'paused'
    ) {
      return;
    }

    let currentPlayPromise: Promise<void> | null = null;
    try {
      // Cancel any previous play promise to avoid race conditions
      if (this.playPromise) {
        try {
          await this.playPromise;
        } catch {
          // Previous play was cancelled, which is fine
        }
      }

      if (
        expectedRequestId !== undefined &&
        expectedRequestId !== this.playbackRequestId
      ) {
        return;
      }

      this.updateState({ error: null });
      currentPlayPromise = this.audio.play();
      this.playPromise = currentPlayPromise;
      await currentPlayPromise;

      // A Stop can arrive after play() is requested but before the browser
      // settles its promise. Enforce that terminal intent even in that narrow
      // window instead of allowing late playback to escape cancellation.
      if (
        expectedRequestId !== undefined &&
        expectedRequestId !== this.playbackRequestId
      ) {
        this.audio.pause();
      }

      // State will be updated by onPlay event handler
    } catch (error) {
      // Browsers may reject play() when a Stop/new source interrupts it. That
      // is an expected cancellation, not a playback failure to surface.
      if (
        expectedRequestId !== undefined &&
        expectedRequestId !== this.playbackRequestId
      ) {
        return;
      }
      console.error('Error playing audio:', error);
      const errorMessage =
        error instanceof Error ? error.message : 'Playback failed';
      this.updateState({
        playbackState: 'error',
        error: errorMessage,
      });
    } finally {
      if (this.playPromise === currentPlayPromise) {
        this.playPromise = null;
      }
    }
  }

  /**
   * COMMAND: Play audio
   * Public method with command guard for external calls (user interactions)
   * Only plays if in idle or paused state
   */
  public async play(): Promise<void> {
    if (!this.guardCommand()) return;
    await this._play();
  }

  /**
   * COMMAND: Pause audio
   * Only pauses if currently playing
   */
  public pause(): void {
    if (!this.guardCommand()) return;

    this._pause();
  }

  /** Pause without applying the public command debounce a second time. */
  private _pause(): void {
    const currentState = this.store.getState();
    // State guard - only pause if playing
    if (currentState.playbackState !== 'playing') {
      return;
    }

    this.audio.pause();
    // State will be updated by onPause event handler
  }

  /**
   * Cancel pending auto-play and pause current playback immediately.
   *
   * Unlike the public pause command, this is deliberately not debounced: Stop
   * is a terminal user intent and must win even while metadata is still loading.
   * The source remains loaded so the footer can resume it explicitly later.
   */
  public stopPlayback(): void {
    this.playbackRequestId += 1;
    if (this.store.getState().playbackState === 'loading') {
      // Release loading UI and any waitForState('idle') caller immediately;
      // its request token is now stale, so it cannot proceed to play.
      this.updateState({ playbackState: 'idle' });
    }
    this._pause();
  }

  /**
   * COMMAND: Seek to specific time
   * Works in idle, playing, or paused states
   */
  public seek(time: number): void {
    if (!this.guardCommand()) return;

    const currentState = this.store.getState();
    // State guard - can seek in idle, playing, or paused states
    if (
      currentState.playbackState === 'loading' ||
      currentState.playbackState === 'error'
    ) {
      return;
    }

    const clampedTime = Math.max(0, Math.min(time, currentState.duration || 0));
    this.audio.currentTime = clampedTime;
    this.updateState({ currentTime: clampedTime });
  }

  /**
   * COMMAND: Toggle play/pause
   * Uses internal _play() to avoid potential guard conflicts in rapid toggle scenarios
   */
  public async toggle(): Promise<void> {
    if (!this.guardCommand()) return;

    const currentState = this.store.getState();
    if (currentState.playbackState === 'playing') {
      this._pause();
    } else if (
      currentState.playbackState === 'idle' ||
      currentState.playbackState === 'paused'
    ) {
      await this._play();
    }
  }

  /**
   * COMMAND: Clear current audio and reset state
   */
  public clear(): void {
    if (!this.guardCommand()) return;

    this.playbackRequestId += 1;

    const currentState = this.store.getState();
    // Only clear if there's actually audio loaded or in an error state
    if (currentState.src || currentState.playbackState === 'error') {
      this.audio.pause();
      this.audio.removeAttribute('src');
      this.audio.load(); // Reset the media element properly

      this.updateState({
        playbackState: 'idle',
        currentTime: 0,
        duration: 0,
        error: null,
        src: null,
        ownerToken: null,
        // Keep metadata - don't clear display text
      });
    }
  }

  /**
   * COMMAND: Load and play audio with metadata (explicit command pattern)
   * Always loads then plays - no conditional behavior
   * This is the preferred method that atomically updates both audio and metadata
   * Uses internal _play() to avoid command guard conflicts within atomic operation
   */
  public async loadAndPlay(
    src: string,
    metadata?: AudioMetadata,
    ownerToken?: string
  ): Promise<void> {
    // Source replacement is already serialized by playbackRequestId. Do not
    // silently debounce it: callers need every accepted selection to either
    // become current or be explicitly superseded.
    const requestId = ++this.playbackRequestId;

    // Atomic update - set both audio source and metadata in one operation
    this.updateState({
      src,
      playbackState: 'loading',
      error: null,
      currentTime: 0,
      duration: 0,
      ownerToken: ownerToken ?? null,
      // Update metadata if provided
      ...(metadata && {
        primaryText: metadata.primaryText,
        secondaryText: metadata.secondaryText,
        downloadFilename: metadata.downloadFilename || '',
      }),
    });

    // Load the audio
    this.audio.pause();
    this.audio.src = src;
    this.audio.load();

    // Wait for loading to complete, then play using internal method
    // Use _play() instead of play() to avoid command guard debounce conflict
    await this.waitForState('idle');
    await this._play(requestId);
  }

  /**
   * COMMAND: Load audio with metadata (without playing)
   */
  public loadWithMetadata(src: string, metadata: AudioMetadata): void {
    if (!this.guardCommand()) return;

    this.playbackRequestId += 1;

    // Validate URL for security
    if (src && !/^https?:\/\//i.test(src)) {
      this.updateState({
        playbackState: 'error',
        error: 'Invalid audio URL: only HTTP/HTTPS protocols are allowed',
      });
      return;
    }

    // Stop any current playback
    this.audio.pause();

    // Atomic update - set both audio source and metadata
    this.updateState({
      src,
      playbackState: 'loading',
      error: null,
      currentTime: 0,
      duration: 0,
      ownerToken: null,
      primaryText: metadata.primaryText,
      secondaryText: metadata.secondaryText,
      downloadFilename: metadata.downloadFilename || '',
    });

    // Load new source (will trigger onLoadStart -> onLoadedMetadata)
    this.audio.src = src;
    this.audio.load();
  }

  /**
   * COMMAND: Update metadata without affecting audio playback
   */
  public setMetadata(metadata: AudioMetadata): void {
    this.updateState({
      primaryText: metadata.primaryText,
      secondaryText: metadata.secondaryText,
      downloadFilename: metadata.downloadFilename || '',
    });
  }

  /**
   * Helper: Wait for specific state (for command sequencing)
   */
  private waitForState(
    targetState: AudioPlaybackState,
    timeoutMs: number = 15000
  ): Promise<void> {
    return new Promise((resolve, reject) => {
      const currentState = this.store.getState();
      if (currentState.playbackState === targetState) {
        resolve();
        return;
      }

      const timeout = setTimeout(() => {
        unsubscribe();
        reject(new Error(`Timeout waiting for state: ${targetState}`));
      }, timeoutMs);

      const unsubscribe = this.store.subscribe((state) => {
        if (state.playbackState === targetState) {
          clearTimeout(timeout);
          unsubscribe();
          resolve();
        } else if (state.playbackState === 'error') {
          clearTimeout(timeout);
          unsubscribe();
          reject(new Error(state.error || 'Audio error'));
        }
      });
    });
  }

  /**
   * Subscribe to natural end-of-audio events (the HTML 'ended' event).
   * Fires the callback exactly once per ended event; never fires at
   * subscribe time (late subscribers don't replay past events). Only
   * natural endings count — clear()/loadAndPlay() never trigger it.
   * Returns an unsubscribe function.
   */
  public subscribeEnded(callback: () => void): () => void {
    let lastCount = this.store.getState().endedCount;
    return this.store.subscribe((state) => {
      if (state.endedCount !== lastCount) {
        lastCount = state.endedCount;
        callback();
      }
    });
  }

  /**
   * Get current audio source URL
   */
  public getCurrentSrc(): string | null {
    return this.store.getState().src;
  }

  /**
   * Check if audio is currently playing
   */
  public isCurrentlyPlaying(): boolean {
    return this.store.getState().playbackState === 'playing';
  }

  /**
   * Check if audio is ready for playback
   */
  public isAudioReady(): boolean {
    const state = this.store.getState().playbackState;
    return state === 'idle' || state === 'paused';
  }

  /**
   * Check if audio is loading
   */
  public isLoading(): boolean {
    return this.store.getState().playbackState === 'loading';
  }

  /**
   * Destroy the singleton instance
   * For testing purposes only
   */
  public static destroy(): void {
    if (AudioService.instance) {
      const instance = AudioService.instance;

      // Remove all HTML audio event listeners
      instance.audio.removeEventListener(
        'loadedmetadata',
        instance.onLoadedMetadata
      );
      instance.audio.removeEventListener('timeupdate', instance.onTimeUpdate);
      instance.audio.removeEventListener('play', instance.onPlay);
      instance.audio.removeEventListener('pause', instance.onPause);
      instance.audio.removeEventListener('ended', instance.onEnded);
      instance.audio.removeEventListener('error', instance.onError);
      instance.audio.removeEventListener('loadstart', instance.onLoadStart);
      instance.audio.removeEventListener('canplay', instance.onCanPlay);

      // Event listeners are already removed above

      // Pause and clear audio
      instance.audio.pause();
      instance.audio.src = '';

      AudioService.instance = null;
    }
  }
}

// Export singleton instance
export const audioService = AudioService.getInstance();

// Export React hooks for accessing the internal store
import { useCallback, useMemo, useSyncExternalStore } from 'react';

// Separate cache variables for each selector to prevent cross-contamination
let cachedAudioState: AudioStateResult | null = null;
let lastAudioStateSnapshot: string | null = null;

let cachedAudioMetadata: AudioMetadataResult | null = null;
let lastMetadataSnapshot: string | null = null;

let cachedAudioPlayback: AudioPlaybackResult | null = null;
let lastPlaybackSnapshot: string | null = null;

// Type definitions for selector results
type AudioStateResult = {
  playbackState: AudioPlaybackState;
  currentTime: number;
  duration: number;
  error: string | null;
  src: string | null;
};

type AudioMetadataResult = {
  primaryText: string;
  secondaryText: string;
  downloadFilename: string;
};

// Playback status without currentTime/duration - for consumers (e.g. per-row
// play/pause buttons) that only care whether *this* clip is the active one and
// its play state. Excluding currentTime avoids re-rendering on every
// 'timeupdate' tick (~4x/sec), which matters when many buttons are mounted.
type AudioPlaybackResult = {
  playbackState: AudioPlaybackState;
  src: string | null;
};

// Stable selectors defined outside hooks
const audioStateSelector = (state: AudioServiceState): AudioStateResult => ({
  playbackState: state.playbackState,
  currentTime: state.currentTime,
  duration: state.duration,
  error: state.error,
  src: state.src,
});

const audioMetadataSelector = (
  state: AudioServiceState
): AudioMetadataResult => ({
  primaryText: state.primaryText,
  secondaryText: state.secondaryText,
  downloadFilename: state.downloadFilename,
});

const audioPlaybackSelector = (
  state: AudioServiceState
): AudioPlaybackResult => ({
  playbackState: state.playbackState,
  src: state.src,
});

// Generic hook for subscribing to AudioService internal store with proper caching
function useAudioServiceStore<T>(selector: (state: AudioServiceState) => T): T {
  const service = AudioService.getInstance();

  const getSnapshot = useCallback(() => {
    const currentState = service.getState();

    // Handle audio state selector with lightweight key (only relevant fields)
    if (selector === audioStateSelector) {
      const stateSnapshot = `${currentState.playbackState}|${currentState.currentTime}|${currentState.duration}|${currentState.error}|${currentState.src}`;
      if (lastAudioStateSnapshot === stateSnapshot && cachedAudioState) {
        return cachedAudioState as T; // Return same reference to prevent re-renders
      }
      const result = selector(currentState) as AudioStateResult;
      cachedAudioState = result;
      lastAudioStateSnapshot = stateSnapshot;
      return result as T;
    }

    // Handle metadata selector with its own lightweight key (only metadata fields)
    if (selector === audioMetadataSelector) {
      const stateSnapshot = `${currentState.primaryText}|${currentState.secondaryText}|${currentState.downloadFilename}`;
      if (lastMetadataSnapshot === stateSnapshot && cachedAudioMetadata) {
        return cachedAudioMetadata as T; // Return same reference to prevent re-renders
      }
      const result = selector(currentState) as AudioMetadataResult;
      cachedAudioMetadata = result;
      lastMetadataSnapshot = stateSnapshot;
      return result as T;
    }

    // Handle playback selector (play state + src, no currentTime) so per-row
    // buttons don't re-render on every timeupdate
    if (selector === audioPlaybackSelector) {
      const stateSnapshot = `${currentState.playbackState}|${currentState.src}`;
      if (lastPlaybackSnapshot === stateSnapshot && cachedAudioPlayback) {
        return cachedAudioPlayback as T; // Same reference to prevent re-renders
      }
      const result = selector(currentState) as AudioPlaybackResult;
      cachedAudioPlayback = result;
      lastPlaybackSnapshot = stateSnapshot;
      return result as T;
    }

    // For unknown selectors, call directly (no caching)
    return selector(currentState);
  }, [service, selector]);

  return useSyncExternalStore(
    service.subscribe,
    getSnapshot,
    getSnapshot // server snapshot (same as client for SSR)
  );
}

// Convenience hooks for common state selections
export function useAudioState(): AudioStateResult {
  return useAudioServiceStore(audioStateSelector);
}

export function useAudioMetadata(): AudioMetadataResult {
  return useAudioServiceStore(audioMetadataSelector);
}

/**
 * Subscribe to play state + current src only (no currentTime/duration).
 * For per-row play/pause buttons that just need to know whether this clip is
 * the active one and whether it's playing - avoids a re-render on every
 * 'timeupdate' tick.
 */
export function useAudioPlaybackStatus(): AudioPlaybackResult {
  return useAudioServiceStore(audioPlaybackSelector);
}

export function useAudioCommands() {
  return useMemo(
    () => ({
      play: () => audioService.play(),
      pause: () => audioService.pause(),
      toggle: () => audioService.toggle(),
      seek: (time: number) => audioService.seek(time),
      load: (src: string) => audioService.load(src),
      loadAndPlay: (
        src: string,
        metadata?: AudioMetadata,
        ownerToken?: string
      ) => audioService.loadAndPlay(src, metadata, ownerToken),
      loadWithMetadata: (src: string, metadata: AudioMetadata) =>
        audioService.loadWithMetadata(src, metadata),
      setMetadata: (metadata: AudioMetadata) =>
        audioService.setMetadata(metadata),
      clear: () => audioService.clear(),
    }),
    []
  ); // Empty dependency array since audioService is a stable singleton
}

// Also export the class for testing
export { AudioService };
