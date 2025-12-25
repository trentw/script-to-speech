/**
 * Audio command types for the event-driven audio system
 */

export type AudioSource = 'generation' | 'history' | 'preview' | 'manual';

export type AudioCommandType = 'play' | 'stop' | 'pause' | 'clear';

export interface AudioPayload {
  url: string;
  primaryText: string;
  secondaryText?: string;
  downloadFilename?: string;
  autoplay?: boolean;
  source: AudioSource;
}

export interface AudioCommand {
  type: AudioCommandType;
  payload?: AudioPayload;
  timestamp?: number;
}

export interface AudioEventHandlers {
  onPlay?: (payload: AudioPayload) => void;
  onStop?: () => void;
  onPause?: () => void;
  onClear?: () => void;
}
