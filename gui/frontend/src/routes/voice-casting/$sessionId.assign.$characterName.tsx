import { useQuery } from '@tanstack/react-query';
import { createFileRoute } from '@tanstack/react-router';
import { Loader2 } from 'lucide-react';
import { useMemo } from 'react';

import { RouteError } from '@/components/errors';
import { Button } from '@/components/ui/button';
import { VoiceAssignmentPanel } from '@/components/voice-casting';
import { useScreenplayCharacters } from '@/hooks/queries/useScreenplayCharacters';
import { useSessionAssignments } from '@/hooks/queries/useSessionAssignments';
import { useVoiceCastingNavigation } from '@/hooks/useVoiceCastingNavigation';
import { apiService } from '@/services/api';

export const Route = createFileRoute(
  '/voice-casting/$sessionId/assign/$characterName'
)({
  component: VoiceAssignmentRoute,
  errorComponent: RouteError,
});

function VoiceAssignmentRoute() {
  const { sessionId, characterName } = Route.useParams();
  const { navigateToSession } = useVoiceCastingNavigation();

  // Fetch session data
  const {
    data: session,
    isLoading: sessionLoading,
    error: sessionError,
  } = useQuery({
    queryKey: ['voice-casting-session', sessionId],
    queryFn: async () => {
      const response = await apiService.getVoiceCastingSession(sessionId);
      if (response.error) {
        throw new Error(response.error);
      }
      return response.data;
    },
  });

  // Fetch character data from backend using session's screenplay_json_path
  // The enabled flag prevents unnecessary requests when session is still loading
  const {
    data: charactersData,
    isLoading,
    error,
  } = useScreenplayCharacters(session?.screenplay_json_path);

  // Get session assignments
  const { data: sessionData } = useSessionAssignments(sessionId);

  // Transform character data for display
  const character = useMemo(() => {
    if (!charactersData) return null;

    const characterInfo = charactersData.characters[characterName];
    if (!characterInfo) return null;

    const assignments = sessionData?.assignments || new Map();
    const assignment = assignments.get(characterName);

    return {
      name: characterName,
      displayName: characterName === 'default' ? 'Narrator' : characterName,
      lineCount: characterInfo.lineCount,
      totalCharacters: characterInfo.totalCharacters || 0,
      longestDialogue: characterInfo.longestDialogue || 0,
      isNarrator: characterInfo.isNarrator || false,
      castingNotes: assignment?.castingNotes,
      role: assignment?.role,
      assignedVoice: assignment
        ? {
            provider: assignment.provider,
            voiceName: assignment.voiceEntry?.sts_id || assignment.sts_id,
            voiceId: assignment.sts_id,
          }
        : null,
    };
  }, [charactersData, characterName, sessionData]);

  const handleBack = () => {
    navigateToSession(sessionId);
  };

  const handleAssign = () => {
    navigateToSession(sessionId, { highlightCharacter: characterName });
  };

  // Loading state
  if (isLoading || sessionLoading) {
    return (
      <div className="container mx-auto max-w-6xl space-y-6 p-6">
        <div className="flex h-64 items-center justify-center">
          <div className="space-y-4 text-center">
            <Loader2 className="text-muted-foreground mx-auto h-8 w-8 animate-spin" />
            <p className="text-muted-foreground">
              Loading character information...
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error || sessionError || !character) {
    return (
      <div className="container mx-auto max-w-6xl space-y-6 p-6">
        <div className="space-y-4 text-center">
          <p className="text-destructive">
            Failed to load character:{' '}
            {error?.message || sessionError?.message || 'Character not found'}
          </p>
          <Button variant="link" onClick={handleBack}>
            Back to Voice Casting
          </Button>
        </div>
      </div>
    );
  }

  return (
    <VoiceAssignmentPanel
      sessionId={sessionId}
      characterName={characterName}
      character={character}
      onBack={handleBack}
      onAssign={handleAssign}
    />
  );
}
