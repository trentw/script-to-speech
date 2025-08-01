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
 * Download an audio file with enhanced reliability and cross-platform support
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

  // Check if running in Tauri desktop environment
  if (typeof window !== 'undefined' && window.__TAURI__) {
    try {
      console.log(
        '[Tauri Debug] Attempting Tauri download for:',
        url,
        'filename:',
        finalFilename
      );

      // Use completely dynamic string-based imports to bypass Vite static analysis
      const pluginDialog = '@tauri-apps/plugin-dialog';
      const apiPath = '@tauri-apps/api/path';
      const pluginUpload = '@tauri-apps/plugin-upload';

      const [tauriDialog, tauriPath, tauriUpload] = await Promise.all([
        new Function('return import(arguments[0])')(pluginDialog).catch(
          () => null
        ),
        new Function('return import(arguments[0])')(apiPath).catch(() => null),
        new Function('return import(arguments[0])')(pluginUpload).catch(
          () => null
        ),
      ]);

      console.log('[Tauri Debug] Plugins loaded:', {
        dialog: !!tauriDialog,
        path: !!tauriPath,
        upload: !!tauriUpload,
      });

      if (tauriDialog && tauriPath && tauriUpload) {
        // Get default download directory
        const downloadDir = await tauriPath.downloadDir();
        console.log('[Tauri Debug] Download directory:', downloadDir);

        // Let user choose download location using the save dialog
        const savePath = await tauriDialog.save({
          defaultPath: `${downloadDir}/${finalFilename}`,
          filters: [
            {
              name: 'Audio Files',
              extensions: ['mp3', 'wav', 'ogg'],
            },
          ],
        });

        console.log('[Tauri Debug] User selected save path:', savePath);

        if (savePath) {
          // Use correct Tauri upload plugin download API signature
          console.log('[Tauri Debug] Starting download...');
          await tauriUpload.download(
            url,
            savePath,
            (progress: number, total: number) => {
              console.log(
                `[Tauri Debug] Download progress: ${progress}/${total} bytes`
              );
            }
          );
          console.log('[Tauri Debug] Download completed successfully');
        } else {
          console.log('[Tauri Debug] User cancelled save dialog');
        }
        return;
      } else {
        console.warn(
          '[Tauri Debug] Some required Tauri plugins are not available'
        );
      }
    } catch (error) {
      console.error('[Tauri Debug] Tauri download failed:', error);
      // Continue to web fallback
    }
  }

  // Convert static URL to download endpoint URL if needed
  let downloadUrl = url;
  if (url.includes('/static/')) {
    // Convert /static/filename.mp3 to /api/files/filename/download
    const filename = url.split('/static/')[1];
    downloadUrl = url.replace(
      `/static/${filename}`,
      `/api/files/${filename}/download`
    );
  }

  try {
    // Primary method: fetch + blob + URL.createObjectURL (modern, reliable)
    const response = await fetch(downloadUrl);

    if (!response.ok) {
      throw new Error(
        `Download failed: ${response.status} ${response.statusText}`
      );
    }

    const blob = await response.blob();
    const downloadUrl_blob = URL.createObjectURL(blob);

    try {
      const link = document.createElement('a');
      link.href = downloadUrl_blob;
      link.download = finalFilename;

      // Temporarily add to DOM, click, then remove
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } finally {
      // Clean up the blob URL to prevent memory leaks
      URL.revokeObjectURL(downloadUrl_blob);
    }
  } catch (error) {
    console.error('Fetch + blob download failed, trying fallback:', error);

    try {
      // Fallback method: direct <a download> (less reliable for cross-origin)
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = finalFilename;

      document.body.appendChild(link);
      try {
        link.click();
      } finally {
        document.body.removeChild(link);
      }
    } catch (fallbackError) {
      console.error('All download methods failed:', fallbackError);
      // Last resort: open in new tab
      if (/^https?:\/\//i.test(downloadUrl)) {
        window.open(downloadUrl, '_blank');
      } else {
        throw new Error('Download failed and URL is not secure for fallback');
      }
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
