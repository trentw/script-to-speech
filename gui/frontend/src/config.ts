/**
 * Centralized configuration for frontend
 */

// Backend port configuration
export const DEV_PORT = 8000;
export const PROD_PORT = 58735;

// Determine current mode
// In Vite, import.meta.env.DEV is true during `npm run dev`
// In Tauri desktop app, import.meta.env.PROD is true
const IS_DEV_MODE = import.meta.env.DEV;

// Backend URL construction
export const BACKEND_PORT = IS_DEV_MODE ? DEV_PORT : PROD_PORT;
export const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}`;

// Log configuration (only in dev mode)
if (IS_DEV_MODE) {
  console.log(`[Config] Running in DEV mode, backend at ${BACKEND_URL}`);
} else {
  console.log(`[Config] Running in PROD mode, backend at ${BACKEND_URL}`);
}
