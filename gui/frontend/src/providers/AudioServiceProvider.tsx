/**
 * AudioServiceProvider - React Context Provider for AudioService integration
 * 
 * This provider creates and manages the AudioService singleton instance.
 * Since AudioService now has its own internal Zustand store, this provider
 * is primarily for ensuring the service is initialized at app startup.
 * 
 * Key features:
 * - Handles React 18 strict mode double initialization
 * - Provides AudioService instance to child components
 * - AudioService manages its own state (no external synchronization needed)
 */

import React, { createContext, useContext, useRef } from 'react';

import { AudioService, audioService } from '../services/AudioService';

interface AudioServiceContextValue {
  audioService: AudioService;
}

const AudioServiceContext = createContext<AudioServiceContextValue | null>(null);

interface AudioServiceProviderProps {
  children: React.ReactNode;
}

export function AudioServiceProvider({ children }: AudioServiceProviderProps) {
  // Initialize AudioService singleton immediately to avoid null context value
  // Use ref to ensure singleton behavior in React 18 strict mode
  const audioServiceRef = useRef<AudioService>(audioService);

  const contextValue: AudioServiceContextValue = {
    audioService: audioServiceRef.current,
  };

  return (
    <AudioServiceContext.Provider value={contextValue}>
      {children}
    </AudioServiceContext.Provider>
  );
}

// Context hooks removed - AudioService is accessed directly via singleton instance

export default AudioServiceProvider;