import type { TaskStatusResponse } from '../types';
import { downloadFile } from './downloadService';

/**
 * Extract audio URLs from a task, handling both new and legacy formats
 */
export const getAudioUrls = (task: TaskStatusResponse): string[] => {
  // New format: audio_urls array
  if (task.audio_urls && task.audio_urls.length > 0) {
    return task.audio_urls;
  }

  // Legacy format: result.files array
  if (task.result && task.result.files && task.result.files.length > 0) {
    return task.result.files;
  }

  return [];
};

/**
 * Play an audio URL using modern HTML5 Audio API best practices
 */
export const playAudioUrl = async (url: string): Promise<void> => {
  // Validate URL to prevent security issues
  if (!/^https?:\/\//i.test(url)) {
    throw new Error('Invalid audio URL: only HTTP/HTTPS protocols are allowed');
  }

  const audio = new Audio(url);

  // Wait for metadata to be loaded before attempting playback
  await new Promise<void>((resolve, reject) => {
    const timeoutId = setTimeout(() => {
      cleanup();
      reject(new Error('Audio loading timeout'));
    }, 10000); // 10 second timeout

    const cleanup = () => {
      clearTimeout(timeoutId);
      audio.removeEventListener('loadedmetadata', onLoaded);
      audio.removeEventListener('error', onError);
    };

    const onLoaded = () => {
      cleanup();
      resolve();
    };

    const onError = () => {
      cleanup();
      reject(new Error(`Failed to load audio: ${url}`));
    };

    audio.addEventListener('loadedmetadata', onLoaded);
    audio.addEventListener('error', onError);
  });

  // Play audio directly - modern browsers support this pattern
  await audio.play();
};

/**
 * Download an audio file using the centralized download service
 */
export const downloadAudio = async (
  url: string,
  filename?: string
): Promise<void> => {
  // Validate URL to prevent security issues
  if (!/^https?:\/\//i.test(url)) {
    throw new Error(
      'Invalid download URL: only HTTP/HTTPS protocols are allowed'
    );
  }

  const finalFilename = filename || `audio-${Date.now()}.mp3`;

  // Convert static URL to download endpoint URL if needed
  let downloadUrl = url;
  if (url.includes('/static/')) {
    // Convert /static/filename.mp3 to /api/files/filename/download
    const staticFilename = url.split('/static/')[1];
    downloadUrl = url.replace(
      `/static/${staticFilename}`,
      `/api/files/${staticFilename}/download`
    );
  }

  // Use the centralized download service
  return downloadFile(downloadUrl, finalFilename, {
    showDialog: true,
    defaultPath: finalFilename,
  });
};

/**
 * Check if a task has any audio files available
 */
export const hasAudioFiles = (task: TaskStatusResponse): boolean => {
  return getAudioUrls(task).length > 0;
};

/**
 * Get a descriptive filename for an audio file based on task data
 */
export const getAudioFilename = (
  task: TaskStatusResponse,
  index: number = 0,
  extension: string = 'mp3'
): string => {
  const provider = task.request?.provider || task.result?.provider || 'unknown';
  const voiceId = task.request?.sts_id || task.result?.voice_id || 'voice';
  const taskId = task.task_id.slice(0, 8);

  return `${provider}-${voiceId}-${taskId}-${index}.${extension}`;
};

/**
 * Normalizes audio URLs for consistent comparison
 * Strips query parameters and handles blob URLs to ensure
 * the same audio file is recognized regardless of cache-busting params
 */
export function normalizeAudioUrl(url: string | null | undefined): string {
  if (!url) return '';

  try {
    // Handle blob URLs - they should be compared as-is
    if (url.startsWith('blob:')) {
      return url;
    }

    // Parse URL and remove query parameters
    const urlObj = new URL(url);
    urlObj.search = ''; // Remove all query params

    return urlObj.toString();
  } catch {
    // If URL parsing fails, return the original
    // This handles relative URLs or malformed strings
    const questionIndex = url.indexOf('?');
    return questionIndex > -1 ? url.slice(0, questionIndex) : url;
  }
}
