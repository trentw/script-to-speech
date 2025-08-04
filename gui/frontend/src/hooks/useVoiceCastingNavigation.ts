import { useNavigate } from '@tanstack/react-router';

/**
 * Hook providing navigation helpers for voice casting routes
 */
export function useVoiceCastingNavigation() {
  const navigate = useNavigate();

  const navigateToIndex = () => {
    navigate({ to: '/voice-casting' });
  };

  const navigateToSession = (sessionId: string) => {
    navigate({ to: '/voice-casting/$sessionId', params: { sessionId } });
  };

  const navigateToAssign = (sessionId: string, characterName: string) => {
    navigate({
      to: '/voice-casting/$sessionId/assign/$characterName',
      params: { sessionId, characterName },
    });
  };

  const navigateToPreview = (sessionId: string) => {
    navigate({
      to: '/voice-casting/$sessionId/preview',
      params: { sessionId },
    });
  };

  const navigateToImport = (sessionId: string) => {
    navigate({
      to: '/voice-casting/$sessionId/import',
      params: { sessionId },
    });
  };

  const navigateToNotes = (sessionId: string) => {
    navigate({ to: '/voice-casting/$sessionId/notes', params: { sessionId } });
  };

  const navigateToLibrary = (sessionId: string) => {
    navigate({
      to: '/voice-casting/$sessionId/library',
      params: { sessionId },
    });
  };

  return {
    navigateToIndex,
    navigateToSession,
    navigateToAssign,
    navigateToPreview,
    navigateToImport,
    navigateToNotes,
    navigateToLibrary,
  };
}
