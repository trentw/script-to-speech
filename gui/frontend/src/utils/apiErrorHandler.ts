/**
 * Shared error handler for API responses
 * Handles common error patterns like version conflicts
 */
export function handleApiError(response: {
  error?: string;
  status?: number;
}): Error {
  // Handle version conflicts (409 status) specifically
  if (response.status === 409) {
    return new Error(
      'The session has been updated by another user. Please refresh and try again.'
    );
  }

  // Return generic error with provided message or default
  return new Error(response.error || 'An error occurred');
}
