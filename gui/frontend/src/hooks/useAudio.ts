import { useCallback, useEffect, useRef, useState } from 'react';

export interface UseAudioOptions {
  src?: string;
  autoplay?: boolean;
}

export interface UseAudioReturn {
  isReady: boolean;
  isPlaying: boolean;
  isLoading: boolean;
  currentTime: number;
  duration: number;
  error: string | null;
  play: () => Promise<void>;
  pause: () => void;
  seek: (time: number) => void;
  load: (src: string) => void;
}

/**
 * Modern audio hook based on HTML5 Audio API best practices
 * Follows the pattern recommended by Zen research for React audio management
 */
export function useAudio({
  src,
  autoplay = false,
}: UseAudioOptions = {}): UseAudioReturn {
  const audioRef = useRef<HTMLAudioElement | undefined>(undefined);
  const playPromiseRef = useRef<Promise<void> | null>(null);
  const autoplayTriggeredRef = useRef<string | null>(null);

  // Audio states
  const [isReady, setIsReady] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [error, setError] = useState<string | null>(null);

  // Create audio element once
  if (!audioRef.current) {
    audioRef.current = new Audio();
    audioRef.current.preload = 'metadata';
    audioRef.current.loop = false; // Ensure audio doesn't loop
  }

  // Action functions
  const play = useCallback(async () => {
    const audio = audioRef.current;
    if (!audio || !isReady) return;

    try {
      // Cancel any previous play promise to avoid race conditions
      if (playPromiseRef.current) {
        try {
          await playPromiseRef.current;
        } catch {
          // Previous play was cancelled, which is fine
        }
      }

      setError(null);
      playPromiseRef.current = audio.play();
      await playPromiseRef.current;
      setIsPlaying(true);
    } catch (error) {
      console.error('Error playing audio:', error);
      setError(error instanceof Error ? error.message : 'Playback failed');
      setIsPlaying(false);
    }
  }, [isReady]);

  const pause = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;

    audio.pause();
    setIsPlaying(false);
  }, []);

  const seek = useCallback((time: number) => {
    const audio = audioRef.current;
    if (!audio) return;

    audio.currentTime = time;
    setCurrentTime(time);
  }, []);

  const load = useCallback((newSrc: string) => {
    const audio = audioRef.current;
    if (!audio) return;

    // Validate URL for security
    if (newSrc && !/^https?:\/\//i.test(newSrc)) {
      setError('Invalid audio URL: only HTTP/HTTPS protocols are allowed');
      return;
    }

    setIsReady(false);
    setIsLoading(true);
    setError(null);
    setCurrentTime(0);
    setDuration(0);

    // Cancel any ongoing playback
    audio.pause();
    setIsPlaying(false);

    // Reset autoplay tracking for new source
    autoplayTriggeredRef.current = null;

    // Load new source
    audio.src = newSrc;
    audio.load();
  }, []);

  // Set up event listeners once
  useEffect(() => {
    const audio = audioRef.current!;

    const onLoadedMetadata = () => {
      setDuration(audio.duration);
      setIsReady(true);
      setIsLoading(false);
    };

    const onTimeUpdate = () => {
      setCurrentTime(audio.currentTime);
    };

    const onPlay = () => {
      setIsPlaying(true);
    };

    const onPause = () => {
      setIsPlaying(false);
    };

    const onEnded = () => {
      setIsPlaying(false);
      setCurrentTime(0);
    };

    const onError = () => {
      const errorMsg = audio.error
        ? `Audio error (${audio.error.code}): ${audio.error.message}`
        : 'Unknown audio error';
      console.error('Audio error:', errorMsg);
      setError(errorMsg);
      setIsLoading(false);
      setIsReady(false);
    };

    const onLoadStart = () => {
      setIsLoading(true);
    };

    const onCanPlay = () => {
      setIsLoading(false);
    };

    // Attach event listeners
    audio.addEventListener('loadedmetadata', onLoadedMetadata);
    audio.addEventListener('timeupdate', onTimeUpdate);
    audio.addEventListener('play', onPlay);
    audio.addEventListener('pause', onPause);
    audio.addEventListener('ended', onEnded);
    audio.addEventListener('error', onError);
    audio.addEventListener('loadstart', onLoadStart);
    audio.addEventListener('canplay', onCanPlay);

    // Cleanup function - only remove listeners, keep audio data
    return () => {
      audio.pause();
      audio.removeEventListener('loadedmetadata', onLoadedMetadata);
      audio.removeEventListener('timeupdate', onTimeUpdate);
      audio.removeEventListener('play', onPlay);
      audio.removeEventListener('pause', onPause);
      audio.removeEventListener('ended', onEnded);
      audio.removeEventListener('error', onError);
      audio.removeEventListener('loadstart', onLoadStart);
      audio.removeEventListener('canplay', onCanPlay);
    };
  }, []);

  // Load initial source when provided
  useEffect(() => {
    if (src) {
      load(src);
    } else if (audioRef.current) {
      // Clear audio when no src provided
      setIsReady(false);
      setError(null);
      setCurrentTime(0);
      setDuration(0);
      audioRef.current.pause();
      setIsPlaying(false);
    }
  }, [src, load]);

  // Handle autoplay separately to avoid reload loops
  useEffect(() => {
    if (src && autoplay && isReady && autoplayTriggeredRef.current !== src) {
      // Only autoplay once per src
      autoplayTriggeredRef.current = src;
      play();
    }
  }, [src, autoplay, isReady, play]);

  return {
    isReady,
    isPlaying,
    isLoading,
    currentTime,
    duration,
    error,
    play,
    pause,
    seek,
    load,
  };
}
