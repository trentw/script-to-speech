import '@testing-library/jest-dom';
import 'vitest-axe/extend-expect';

import { cleanup } from '@testing-library/react';
import { setupServer } from 'msw/node';
import { afterAll, afterEach, beforeAll, vi } from 'vitest';

import { handlers } from './mocks/handlers';

// Set React 19 act environment flag
// @ts-expect-error - React 19 internal flag
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

// MSW server setup with handlers
export const server = setupServer(...handlers);

// Enable MSW API mocking
beforeAll(() => {
  server.listen({ onUnhandledRequest: 'error' });
});

// Reset handlers between tests
afterEach(() => {
  server.resetHandlers();
  cleanup(); // Clean up React Testing Library
});

// Clean up after all tests
afterAll(() => {
  server.close();
});

// Mock ResizeObserver for Radix UI components
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));

// Enhanced Audio/HTMLMediaElement mock with timing support
class MockAudio extends EventTarget {
  _currentTime = 0;
  _duration = 120; // Default 2 minutes
  paused = true;
  ended = false;
  error = null;
  src = '';
  volume = 1;
  muted = false;
  playbackRate = 1;

  constructor(src?: string) {
    super();
    if (src) this.src = src;
  }

  get currentTime() {
    return this._currentTime;
  }

  set currentTime(value: number) {
    this._currentTime = Math.max(0, Math.min(value, this._duration));
    this.dispatchEvent(new Event('timeupdate'));
  }

  get duration() {
    return this._duration;
  }

  play = vi.fn().mockImplementation(() => {
    this.paused = false;
    this.ended = false;
    // Immediately fire loadedmetadata so duration is available
    this.dispatchEvent(new Event('loadedmetadata'));
    return Promise.resolve();
  });

  pause = vi.fn().mockImplementation(() => {
    this.paused = true;
  });

  load = vi.fn();

  // Helper method for tests to simulate time progression
  advanceTime(seconds: number) {
    if (!this.paused && !this.ended) {
      this.currentTime = Math.min(this.currentTime + seconds, this.duration);

      if (this.currentTime >= this.duration) {
        this.ended = true;
        this.paused = true;
        this.dispatchEvent(new Event('ended'));
      }
    }
  }

  // Helper to set current time directly
  setCurrentTime(time: number) {
    this.currentTime = time;
  }
}

// Extend global types for test utilities
declare global {
  var MockAudio: typeof MockAudio;
  var getAudioMockInstance: (element: HTMLAudioElement) => MockAudio | undefined;
}

// Make MockAudio available globally for tests
global.MockAudio = MockAudio;

// Set global Audio to use our mock
global.Audio = MockAudio as unknown as typeof Audio;

// Store references to instances for test access
const audioInstances = new WeakMap<HTMLAudioElement, MockAudio>();

// Mock HTMLMediaElement prototype for <audio> elements
const _originalPlay = HTMLMediaElement.prototype.play;
const _originalPause = HTMLMediaElement.prototype.pause;

// Create a proper mock for play method
HTMLMediaElement.prototype.play = vi.fn().mockImplementation(function (
  this: HTMLAudioElement
) {
  // Get or create mock instance
  let mockInstance = audioInstances.get(this);
  if (!mockInstance) {
    mockInstance = new MockAudio();
    audioInstances.set(this, mockInstance);
  }

  // Fire loadedmetadata immediately so duration is available
  setTimeout(() => {
    this.dispatchEvent(new Event('loadedmetadata'));
  }, 0);

  return mockInstance.play();
});

HTMLMediaElement.prototype.pause = vi.fn().mockImplementation(function (
  this: HTMLAudioElement
) {
  let mockInstance = audioInstances.get(this);
  if (!mockInstance) {
    mockInstance = new MockAudio();
    audioInstances.set(this, mockInstance);
  }
  return mockInstance.pause();
});

// Mock properties with getters/setters
Object.defineProperty(HTMLMediaElement.prototype, 'duration', {
  configurable: true,
  get() {
    const mockInstance = audioInstances.get(this as HTMLAudioElement);
    return mockInstance ? mockInstance.duration : 120;
  },
});

Object.defineProperty(HTMLMediaElement.prototype, 'currentTime', {
  configurable: true,
  get() {
    const mockInstance = audioInstances.get(this as HTMLAudioElement);
    return mockInstance ? mockInstance.currentTime : 0;
  },
  set(value: number) {
    let mockInstance = audioInstances.get(this as HTMLAudioElement);
    if (!mockInstance) {
      mockInstance = new MockAudio();
      audioInstances.set(this as HTMLAudioElement, mockInstance);
    }
    mockInstance.currentTime = value;
  },
});

Object.defineProperty(HTMLMediaElement.prototype, 'paused', {
  configurable: true,
  get() {
    const mockInstance = audioInstances.get(this as HTMLAudioElement);
    return mockInstance ? mockInstance.paused : true;
  },
});

Object.defineProperty(HTMLMediaElement.prototype, 'ended', {
  configurable: true,
  get() {
    const mockInstance = audioInstances.get(this as HTMLAudioElement);
    return mockInstance ? mockInstance.ended : false;
  },
});

// Make mock instances accessible to tests
global.getAudioMockInstance = (element: HTMLAudioElement) => {
  return audioInstances.get(element);
};

// Mock window.matchMedia for responsive components
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(), // deprecated
    removeListener: vi.fn(), // deprecated
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Mock Element.prototype.scrollIntoView for Radix UI components
Element.prototype.scrollIntoView = vi.fn();

// Mock Element.prototype.hasPointerCapture for Radix UI Select
Element.prototype.hasPointerCapture = vi.fn().mockReturnValue(false);
Element.prototype.setPointerCapture = vi.fn();
Element.prototype.releasePointerCapture = vi.fn();

// Mock IntersectionObserver for lazy loading components
global.IntersectionObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
  root: null,
  rootMargin: '',
  thresholds: [],
  takeRecords: () => [],
}));

// Suppress console errors during tests (optional, can be removed if you want to see errors)
const originalError = console.error;
beforeAll(() => {
  console.error = (...args: unknown[]) => {
    // Filter out known React 18/19 act warnings
    if (
      typeof args[0] === 'string' &&
      args[0].includes('Warning: ReactDOMTestUtils.act is deprecated')
    ) {
      return;
    }
    originalError.call(console, ...args);
  };
});

afterAll(() => {
  console.error = originalError;
});
