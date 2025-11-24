# Services

This directory contains singleton services that provide persistent functionality across the application.

## AudioService

The `AudioService` is a singleton class with an internal Zustand store that manages a persistent HTML5 Audio element. It provides a command-pattern API with separate React hooks for state management.

### Key Features

- **Singleton Pattern**: Only one audio instance across the entire application
- **Persistent State**: Audio continues playing even when components unmount
- **Internal Zustand Store**: Single source of truth for all audio state and metadata
- **Finite State Machine**: Clear state transitions (idle → loading → playing → paused → error)
- **Command Pattern**: Unidirectional data flow with debounced commands
- **React 18 Compatible**: Works correctly with React 18 strict mode
- **Security**: Validates URLs to only allow HTTP/HTTPS protocols
- **Performance Optimized**: Separate hooks prevent unnecessary re-renders

### Architecture

AudioService uses a **three-hook pattern** for optimal performance:

1. **`useAudioState()`** - Subscribe to playback state only
2. **`useAudioMetadata()`** - Subscribe to display metadata only
3. **`useAudioCommands()`** - Get stable command functions

This separation ensures components only re-render when their specific data changes.

### Usage

#### React Hooks (Recommended)

```typescript
import {
  useAudioState,
  useAudioMetadata,
  useAudioCommands
} from '@/services/AudioService';

function AudioPlayer() {
  // Subscribe to playback state
  const { playbackState, currentTime, duration, error, src } = useAudioState();

  // Subscribe to metadata
  const { primaryText, secondaryText, downloadFilename } = useAudioMetadata();

  // Get command functions (stable reference, doesn't cause re-renders)
  const { play, pause, seek, loadAndPlay, clear } = useAudioCommands();

  const isPlaying = playbackState === 'playing';
  const isReady = playbackState === 'idle' || playbackState === 'paused';
  const isLoading = playbackState === 'loading';

  return (
    <div>
      <h3>{primaryText}</h3>
      <p>{secondaryText}</p>

      <button onClick={play} disabled={!isReady}>
        {isPlaying ? 'Pause' : 'Play'}
      </button>

      <input
        type="range"
        min={0}
        max={duration}
        value={currentTime}
        onChange={(e) => seek(Number(e.target.value))}
      />

      {error && <p style={{ color: 'red' }}>{error}</p>}
    </div>
  );
}
```

#### Loading Audio with Metadata

```typescript
import { useAudioCommands } from '@/services/AudioService';

function VoicePreviewButton({ voiceId, voiceName, provider }: Props) {
  const { loadAndPlay } = useAudioCommands();

  const handlePlay = () => {
    loadAndPlay(
      `https://api.example.com/voices/${voiceId}/sample`,
      {
        primaryText: voiceName,
        secondaryText: `Provider: ${provider}`,
        downloadFilename: `${voiceId}-sample.mp3`
      }
    );
  };

  return <button onClick={handlePlay}>Play Sample</button>;
}
```

#### Conditional Rendering Based on State

```typescript
import { useAudioState } from '@/services/AudioService';

function GlobalAudioIndicator() {
  const { playbackState, primaryText } = useAudioState();

  if (playbackState === 'idle') return null;

  return (
    <div className="audio-indicator">
      {playbackState === 'loading' && <Spinner />}
      {playbackState === 'playing' && <PlayingAnimation />}
      {playbackState === 'paused' && <PauseIcon />}
      {playbackState === 'error' && <ErrorIcon />}
      <span>{primaryText}</span>
    </div>
  );
}
```

### Hook Reference

#### `useAudioState()`

Returns audio playback state. Components using this hook re-render when playback state changes.

**Returns:**

```typescript
{
  playbackState: 'idle' | 'loading' | 'playing' | 'paused' | 'error';
  currentTime: number; // Current position in seconds
  duration: number; // Total duration in seconds
  error: string | null; // Error message if any
  src: string | null; // Current audio source URL
}
```

#### `useAudioMetadata()`

Returns display metadata. Components using this hook re-render when metadata changes.

**Returns:**

```typescript
{
  primaryText: string; // Main display text (e.g., voice name)
  secondaryText: string; // Secondary text (e.g., provider name)
  downloadFilename: string; // Filename for downloads
}
```

#### `useAudioCommands()`

Returns stable command functions. This hook **never causes re-renders** since it returns the same object reference.

**Returns:**

```typescript
{
  play: () => Promise<void>;                    // Start playback
  pause: () => void;                            // Pause playback
  toggle: () => Promise<void>;                  // Toggle play/pause
  seek: (time: number) => void;                 // Seek to position
  load: (src: string) => void;                  // Load audio URL
  loadAndPlay: (                                // Load and auto-play with metadata
    src: string,
    metadata?: AudioMetadata
  ) => Promise<void>;
  loadWithMetadata: (                           // Load with metadata (no autoplay)
    src: string,
    metadata: AudioMetadata
  ) => void;
  setMetadata: (metadata: AudioMetadata) => void; // Update metadata only
  clear: () => void;                            // Stop and clear all state
}
```

**AudioMetadata Interface:**

```typescript
interface AudioMetadata {
  primaryText: string;
  secondaryText: string;
  downloadFilename?: string;
}
```

### Direct Service Usage (Advanced)

For non-React code or when you need direct access:

```typescript
import { audioService } from '@/services/AudioService';

// Get current state
const state = audioService.getState();

// Subscribe to changes
const unsubscribe = audioService.subscribe((state) => {
  console.log('Audio state changed:', state);
});

// Control playback
await audioService.play();
audioService.pause();
audioService.seek(30);
audioService.clear();

// Clean up
unsubscribe();
```

### State Machine

The service implements a finite state machine:

```
idle ──load──> loading ──success──> idle/playing
                     └──error──> error ──clear──> idle
playing ──pause──> paused ──play──> playing
        └──ended──> idle
```

**State Transitions:**

- **idle**: No audio loaded, ready to load new audio
- **loading**: Audio is being fetched and buffered
- **playing**: Audio is currently playing
- **paused**: Audio is paused, ready to resume
- **error**: An error occurred, must clear or load new audio

### Performance Optimization

The three-hook pattern prevents unnecessary re-renders:

```typescript
// ❌ BAD: This component re-renders on every time update
function BadExample() {
  const state = useAudioState(); // Re-renders when currentTime changes
  return <button>Fixed Text</button>;
}

// ✅ GOOD: This component only re-renders when commands change (never)
function GoodExample() {
  const { play } = useAudioCommands(); // Stable reference, no re-renders
  return <button onClick={play}>Play</button>;
}

// ✅ GOOD: Only subscribes to metadata, not playback state
function MetadataDisplay() {
  const { primaryText, secondaryText } = useAudioMetadata();
  return <div>{primaryText} - {secondaryText}</div>;
}
```

### Best Practices

1. **Use the appropriate hook** for your needs:
   - Need playback state? → `useAudioState()`
   - Need metadata? → `useAudioMetadata()`
   - Need controls? → `useAudioCommands()`

2. **Call `clear()`** when the user navigates away or audio is no longer needed

3. **Handle the error state** by checking `playbackState === 'error'` or `error !== null`

4. **Use `loadAndPlay()` for one-shot sounds** like voice previews

5. **Don't destructure unnecessarily** - only get the fields you actually use:

   ```typescript
   // ❌ BAD: Causes re-renders even if you don't use currentTime
   const { playbackState, currentTime } = useAudioState();
   return <div>{playbackState}</div>;

   // ✅ GOOD: Only subscribe to what you use
   const { playbackState } = useAudioState();
   return <div>{playbackState}</div>;
   ```

### Testing

The service includes comprehensive tests and can be reset between tests:

```typescript
import { AudioService } from '@/services/AudioService';

beforeEach(() => {
  AudioService.destroy(); // Clean slate for each test
});

it('should play audio', async () => {
  const service = AudioService.getInstance();
  service.load('https://example.com/audio.mp3');
  await service.play();

  expect(service.getState().playbackState).toBe('playing');
});
```

### React 18 Strict Mode

The singleton pattern is implemented to be safe with React 18's strict mode, which may call constructors multiple times during development. The service ensures only one instance is created regardless of how many times `getInstance()` is called.
