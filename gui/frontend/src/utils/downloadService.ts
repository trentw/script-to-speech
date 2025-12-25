import { isTauri } from '@tauri-apps/api/core';

/**
 * Centralized download service that handles both Tauri and web downloads
 * Automatically detects the environment and uses the appropriate method
 */

interface DownloadOptions {
  /** Show native file dialog in Tauri (default: true) */
  showDialog?: boolean;
  /** Default filename for save dialog */
  defaultPath?: string;
  /** Progress callback for large downloads */
  onProgress?: (progress: number, total: number) => void;
}

/**
 * Download a file from a URL or Blob
 * @param source - URL string or Blob object to download
 * @param filename - Default filename for the download
 * @param options - Additional download options
 */
export async function downloadFile(
  source: string | Blob,
  filename: string,
  options: DownloadOptions = {}
): Promise<void> {
  const { showDialog = true, defaultPath, onProgress } = options;

  // Detect Tauri environment using official API
  if (isTauri()) {
    return downloadInTauri(
      source,
      defaultPath || filename,
      showDialog,
      onProgress
    );
  } else {
    return downloadInBrowser(source, filename);
  }
}

/**
 * Download file in Tauri environment with native file dialog
 */
async function downloadInTauri(
  source: string | Blob,
  defaultPath: string,
  showDialog: boolean,
  onProgress?: (progress: number, total: number) => void
): Promise<void> {
  try {
    // Dynamic imports for Tauri-specific modules
    const [uploadModule, dialogModule, fsModule] = await Promise.all([
      import('@tauri-apps/plugin-upload'),
      import('@tauri-apps/plugin-dialog'),
      import('@tauri-apps/plugin-fs'),
    ]);

    const { download } = uploadModule;
    const { save } = dialogModule;
    const { writeBinaryFile } = fsModule;

    // Get download directory if needed
    let downloadPath: string | null = defaultPath;

    if (showDialog) {
      // Extract file extension from default path
      const ext = defaultPath.split('.').pop() || 'txt';

      // Show native save dialog
      downloadPath = await save({
        defaultPath,
        filters: [
          {
            name: getFilterName(ext),
            extensions: [ext],
          },
        ],
      });

      // User cancelled
      if (!downloadPath) {
        return;
      }
    }

    // Handle different source types
    if (typeof source === 'string') {
      // Download from URL using Tauri's download plugin
      await download(source, downloadPath, onProgress);
    } else {
      // Convert Blob to Uint8Array and write directly
      const arrayBuffer = await source.arrayBuffer();
      await writeBinaryFile(downloadPath, new Uint8Array(arrayBuffer));
    }
  } catch (error) {
    // If Tauri modules fail to load or download fails, fall back to browser method
    console.error(
      'Tauri download failed, falling back to browser method:',
      error
    );
    return downloadInBrowser(source, defaultPath);
  }
}

/**
 * Download file in browser using blob download
 */
async function downloadInBrowser(
  source: string | Blob,
  filename: string
): Promise<void> {
  let blob: Blob;

  try {
    if (typeof source === 'string') {
      // Fetch the URL and convert to blob
      const response = await fetch(source);
      if (!response.ok) {
        throw new Error(
          `Failed to fetch: ${response.status} ${response.statusText}`
        );
      }
      blob = await response.blob();
    } else {
      // Already a blob
      blob = source;
    }

    // Create download link
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.style.display = 'none';

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    // Clean up
    setTimeout(() => URL.revokeObjectURL(url), 100);
  } catch (error) {
    // Last resort: open URL in new tab (for URLs only)
    if (typeof source === 'string') {
      const link = document.createElement('a');
      link.href = source;
      link.download = filename;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } else {
      throw error;
    }
  }
}

/**
 * Helper function to get filter name for file dialog
 */
function getFilterName(extension: string): string {
  const filterMap: Record<string, string> = {
    mp3: 'Audio Files',
    wav: 'Audio Files',
    m4a: 'Audio Files',
    json: 'JSON Files',
    yaml: 'YAML Files',
    yml: 'YAML Files',
    txt: 'Text Files',
    log: 'Log Files',
    pdf: 'PDF Files',
    xml: 'XML Files',
  };

  return filterMap[extension.toLowerCase()] || 'All Files';
}

/**
 * Convenience function for downloading text content
 */
export async function downloadText(
  content: string,
  filename: string,
  mimeType: string = 'text/plain'
): Promise<void> {
  const blob = new Blob([content], { type: mimeType });
  return downloadFile(blob, filename);
}

/**
 * Convenience function for downloading JSON
 */
export async function downloadJSON(
  data: unknown,
  filename: string
): Promise<void> {
  const content = JSON.stringify(data, null, 2);
  return downloadText(content, filename, 'application/json');
}

/**
 * Convenience function for downloading audio from URL
 */
export async function downloadAudio(
  url: string,
  filename?: string
): Promise<void> {
  // Extract filename from URL if not provided
  if (!filename) {
    const urlParts = url.split('/');
    filename = urlParts[urlParts.length - 1] || 'audio.mp3';
  }

  return downloadFile(url, filename, {
    showDialog: true,
    defaultPath: filename,
  });
}
