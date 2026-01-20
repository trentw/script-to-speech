/**
 * Centralized route constants for the application
 */

export const ROUTES = {
  HOME: '/',
  TTS: '/tts',
  SCREENPLAY: {
    ROOT: '/screenplay',
    TASK: '/screenplay/$taskId',
  },
  PROJECT: {
    ROOT: '/project',
    WELCOME: '/project/welcome',
    OVERVIEW: '/project/',
    SCREENPLAY: '/project/screenplay',
    VOICES: '/project/voices',
    TEST: '/project/test',
    PROCESSING: '/project/processing',
    GENERATE: '/project/generate',
    REVIEW: '/project/review',
  },
  VOICE_CASTING: {
    ROOT: '/voice-casting',
    SESSION: '/voice-casting/$sessionId',
  },
} as const;

/**
 * Create a screenplay task route with the given task ID
 */
export function createScreenplayTaskRoute(taskId: string): string {
  return ROUTES.SCREENPLAY.TASK.replace('$taskId', taskId);
}

/**
 * Create a voice casting session route with the given session ID
 */
export function createVoiceCastingRoute(sessionId: string): string {
  return ROUTES.VOICE_CASTING.SESSION.replace('$sessionId', sessionId);
}
