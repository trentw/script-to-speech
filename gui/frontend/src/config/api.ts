/**
 * API Configuration for both development and production environments
 */

/**
 * Get the API base URL based on environment
 * - Development (browser): http://127.0.0.1:8000/api
 * - Production (Tauri): http://127.0.0.1:8000/api
 *
 * Both environments use the same local backend server
 */
export function getApiBaseUrl(): string {
  // Both dev and production use the same local backend
  return 'http://127.0.0.1:8000/api';
}

/**
 * Get the full API base URL with protocol
 */
export const API_BASE_URL = getApiBaseUrl();

/**
 * Check if running in Tauri environment
 */
export function isTauriEnvironment(): boolean {
  return '__TAURI_INTERNALS__' in window;
}
