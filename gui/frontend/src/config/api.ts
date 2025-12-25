/**
 * API Configuration for both development and production environments
 */

import { BACKEND_URL } from '@/config';

/**
 * Get the API base URL based on environment
 * - Development (browser): http://127.0.0.1:8000/api
 * - Production (Tauri): http://127.0.0.1:58735/api
 *
 * Port is auto-detected based on mode (dev=8000, prod=58735)
 */
export function getApiBaseUrl(): string {
  return `${BACKEND_URL}/api`;
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
