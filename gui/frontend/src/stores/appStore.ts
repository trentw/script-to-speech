import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { devtools } from 'zustand/middleware'
import { useShallow } from 'zustand/react/shallow'
import type { VoiceEntry } from '../types'

// Configuration slice - handles TTS provider/voice settings
interface ConfigurationSlice {
  selectedProvider: string | undefined
  selectedVoice: VoiceEntry | undefined
  currentConfig: Record<string, any>
  
  // Actions
  setSelectedProvider: (provider: string | undefined) => void
  setSelectedVoice: (voice: VoiceEntry | undefined) => void
  setCurrentConfig: (config: Record<string, any>) => void
  setConfiguration: (provider: string, voice: VoiceEntry | undefined, config: Record<string, any>) => void
  resetConfiguration: () => void
}

// User Input slice - handles text input for TTS generation
interface UserInputSlice {
  text: string
  
  // Actions
  setText: (text: string) => void
  clearText: () => void
}

// UI slice - handles UI state like errors, loading indicators
interface UISlice {
  error: string | undefined
  
  // Actions
  setError: (error: string | undefined) => void
  clearError: () => void
}

// Central Audio slice - manages the central audio player
interface CentralAudioSlice {
  audioUrl: string | undefined
  primaryText: string | undefined
  secondaryText: string | undefined
  downloadFilename: string | undefined
  loading: boolean
  autoplay: boolean
  
  // Actions
  setAudioData: (audioUrl: string, primaryText: string, secondaryText?: string, downloadFilename?: string, autoplay?: boolean) => void
  clearAudio: () => void
  setLoading: (loading: boolean) => void
}

// Combined store type
type AppStore = ConfigurationSlice & UserInputSlice & UISlice & CentralAudioSlice

// Create the store with domain slices
const useAppStore = create<AppStore>()(
  devtools(
    persist(
      (set) => ({
        // Configuration slice implementation
        selectedProvider: undefined,
        selectedVoice: undefined,
        currentConfig: {},
        
        setSelectedProvider: (provider) => {
          set({ selectedProvider: provider }, false, 'configuration/setSelectedProvider')
        },
        
        setSelectedVoice: (voice) => {
          set({ selectedVoice: voice }, false, 'configuration/setSelectedVoice')
        },
        
        setCurrentConfig: (config) => {
          set({ currentConfig: config }, false, 'configuration/setCurrentConfig')
        },
        
        setConfiguration: (provider, voice, config) => {
          set({ 
            selectedProvider: provider,
            selectedVoice: voice,
            currentConfig: config
          }, false, 'configuration/setConfiguration')
        },
        
        resetConfiguration: () => {
          set({ 
            selectedProvider: undefined,
            selectedVoice: undefined,
            currentConfig: {}
          }, false, 'configuration/reset')
        },
        
        // User Input slice implementation
        text: '',
        
        setText: (text) => {
          set({ text }, false, 'userInput/setText')
        },
        
        clearText: () => {
          set({ text: '' }, false, 'userInput/clearText')
        },
        
        // UI slice implementation
        error: undefined,
        
        setError: (error) => {
          set({ error }, false, 'ui/setError')
        },
        
        clearError: () => {
          set({ error: undefined }, false, 'ui/clearError')
        },
        
        // Central Audio slice implementation
        audioUrl: undefined,
        primaryText: undefined,
        secondaryText: undefined,
        downloadFilename: undefined,
        loading: false,
        autoplay: false,
        
        setAudioData: (audioUrl, primaryText, secondaryText, downloadFilename, autoplay = false) => {
          set({ 
            audioUrl,
            primaryText,
            secondaryText,
            downloadFilename,
            loading: false,
            autoplay
          }, false, 'centralAudio/setAudioData')
        },
        
        clearAudio: () => {
          set({ 
            audioUrl: undefined,
            primaryText: undefined,
            secondaryText: undefined,
            downloadFilename: undefined,
            loading: false,
            autoplay: false
          }, false, 'centralAudio/clearAudio')
        },
        
        setLoading: (loading) => {
          set({ loading }, false, 'centralAudio/setLoading')
        },
      }),
      {
        name: 'sts-app-store', // localStorage key
        storage: createJSONStorage(() => localStorage),
        // Selective persistence - only persist user preferences
        partialize: (state) => ({
          selectedProvider: state.selectedProvider,
          selectedVoice: state.selectedVoice,
          currentConfig: state.currentConfig,
          // text, error are NOT persisted (ephemeral state)
        }),
      }
    ),
    {
      name: 'STS App Store', // DevTools name
    }
  )
)

// Optimized selectors using useShallow to prevent infinite re-renders
export const useConfiguration = () => useAppStore(
  useShallow((state) => ({
    selectedProvider: state.selectedProvider,
    selectedVoice: state.selectedVoice,
    currentConfig: state.currentConfig,
    setSelectedProvider: state.setSelectedProvider,
    setSelectedVoice: state.setSelectedVoice,
    setCurrentConfig: state.setCurrentConfig,
    setConfiguration: state.setConfiguration,
    resetConfiguration: state.resetConfiguration,
  }))
)

export const useUserInput = () => useAppStore(
  useShallow((state) => ({
    text: state.text,
    setText: state.setText,
    clearText: state.clearText,
  }))
)

export const useUIState = () => useAppStore(
  useShallow((state) => ({
    error: state.error,
    setError: state.setError,
    clearError: state.clearError,
  }))
)

export const useCentralAudio = () => useAppStore(
  useShallow((state) => ({
    audioUrl: state.audioUrl,
    primaryText: state.primaryText,
    secondaryText: state.secondaryText,
    downloadFilename: state.downloadFilename,
    loading: state.loading,
    autoplay: state.autoplay,
    setAudioData: state.setAudioData,
    clearAudio: state.clearAudio,
    setLoading: state.setLoading,
  }))
)

export default useAppStore