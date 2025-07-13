import type { TaskStatusResponse } from '../types';

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
 * Download an audio file with security validation
 */
export const downloadAudio = (url: string, filename?: string): void => {
  // Validate URL to prevent security issues
  if (!/^https?:\/\//i.test(url)) {
    throw new Error('Invalid download URL: only HTTP/HTTPS protocols are allowed');
  }

  try {
    const link = document.createElement('a');
    link.href = url;
    link.download = filename || `audio-${Date.now()}.mp3`;
    
    // Temporarily add to DOM, click, then remove
    document.body.appendChild(link);
    try {
      link.click();
    } finally {
      document.body.removeChild(link);
    }
  } catch (error) {
    console.error('Error downloading audio:', error);
    // Secure fallback: only open validated URLs
    if (/^https?:\/\//i.test(url)) {
      window.open(url, '_blank');
    } else {
      throw new Error('Download failed and URL is not secure for fallback');
    }
  }
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