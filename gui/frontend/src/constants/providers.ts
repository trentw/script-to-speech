/**
 * Provider constants and utilities
 * Maps provider identifiers to their API key environment variable names
 */

// Map of provider identifiers to their API key environment variable names
export const PROVIDER_API_KEY_MAP: Record<string, string> = {
  openai: 'OPENAI_API_KEY',
  elevenlabs: 'ELEVEN_API_KEY',
  cartesia: 'CARTESIA_API_KEY',
  minimax: 'MINIMAX_API_KEY',
  zonos: 'ZONOS_API_KEY',
};

// Some providers require multiple keys (e.g., Minimax needs API key and Group ID)
export const PROVIDER_REQUIRED_KEYS: Record<string, string[]> = {
  openai: ['OPENAI_API_KEY'],
  elevenlabs: ['ELEVEN_API_KEY'],
  cartesia: ['CARTESIA_API_KEY'],
  minimax: ['MINIMAX_API_KEY', 'MINIMAX_GROUP_ID'],
  zonos: ['ZONOS_API_KEY'],
};

/**
 * Get the API key environment variable name for a provider
 * @param providerId - The provider identifier (e.g., 'openai', 'elevenlabs')
 * @returns The environment variable name (e.g., 'OPENAI_API_KEY')
 */
export function getProviderApiKeyName(providerId: string): string {
  return PROVIDER_API_KEY_MAP[providerId.toLowerCase()] || '';
}

/**
 * Get all required API key environment variable names for a provider
 * @param providerId - The provider identifier
 * @returns Array of environment variable names required for this provider
 */
export function getProviderRequiredKeys(providerId: string): string[] {
  return PROVIDER_REQUIRED_KEYS[providerId.toLowerCase()] || [];
}

/**
 * Check if a provider has all required API keys configured
 * @param providerId - The provider identifier
 * @param apiKeyStatus - Record of API key statuses from backend validation
 * @returns True if all required keys are configured
 */
export function isProviderConfigured(
  providerId: string,
  apiKeyStatus: Record<string, boolean>
): boolean {
  const requiredKeys = getProviderRequiredKeys(providerId);
  if (requiredKeys.length === 0) return true; // No keys required (e.g., dummy providers)

  return requiredKeys.every((key) => apiKeyStatus[key] === true);
}
