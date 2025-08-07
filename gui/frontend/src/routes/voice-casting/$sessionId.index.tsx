import { useQuery } from '@tanstack/react-query';
import { createFileRoute } from '@tanstack/react-router';
import {
  AlertCircle,
  ArrowLeft,
  Brain,
  CheckCircle2,
  Circle,
  Download,
  Eye,
  FileText,
  Loader2,
  Upload,
} from 'lucide-react';
import { useEffect, useMemo } from 'react';

import { RouteError } from '@/components/errors';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { CharacterCard } from '@/components/voice-casting';
import { useScreenplayCharacters } from '@/hooks/queries/useScreenplayCharacters';
import { useVoiceCastingNavigation } from '@/hooks/useVoiceCastingNavigation';
import { apiService } from '@/services/api';
import { type CharacterInfo, useVoiceCasting } from '@/stores/appStore';
import type { RouteStaticData } from '@/types/route-metadata';

export const Route = createFileRoute('/voice-casting/$sessionId/')({
  component: VoiceCastingSessionIndex,
  errorComponent: RouteError,
  staticData: {
    title: 'Voice Casting Session',
    description: 'Assign voices to screenplay characters',
    ui: {
      showPanel: false,
      showFooter: false,
      mobileDrawers: [],
    },
  } satisfies RouteStaticData,
});

function VoiceCastingSessionIndex() {
  const { sessionId } = Route.useParams();
  const {
    navigateToIndex,
    navigateToAssign,
    navigateToPreview,
    navigateToImport,
    navigateToNotes,
    navigateToLibrary,
  } = useVoiceCastingNavigation();

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

  // Connect to voice casting store
  const { 
    assignments, 
    setScreenplayData, 
    setCastingSessionId, 
    setScreenplayJsonPath,
    createOrUpdateSession
  } = useVoiceCasting();

  // Set session information in store when session data loads
  useEffect(() => {
    if (session) {
      setCastingSessionId(session.session_id);
      setScreenplayJsonPath(session.screenplay_json_path);
      
      // Create or update the session in the multi-session store
      createOrUpdateSession({
        sessionId: session.session_id,
        screenplayName: session.screenplay_name,
        screenplayJsonPath: session.screenplay_json_path,
      });
    }
  }, [session, setCastingSessionId, setScreenplayJsonPath, createOrUpdateSession]);

  // Update the screenplay data in the store when characters data loads
  useEffect(() => {
    if (charactersData) {
      // Convert character data to Map format expected by store
      const charactersMap = new Map<string, CharacterInfo>();
      Object.entries(charactersData.characters).forEach(([name, info]) => {
        charactersMap.set(name, info);
      });

      setScreenplayData({
        characters: charactersMap,
      });
    }
  }, [charactersData, setScreenplayData]);

  // Transform character data for display
  const characters = useMemo(() => {
    if (!charactersData) return [];

    return Object.entries(charactersData.characters).map(([name, char]) => {
      const assignment = assignments.get(name);
      const characterInfo: CharacterInfo = {
        name,
        displayName: name === 'default' ? 'Narrator' : name,
        lineCount: char.lineCount,
        totalCharacters: char.totalCharacters || 0,
        longestDialogue: char.longestDialogue || 0,
        isNarrator: char.isNarrator || false,
        castingNotes: assignment?.castingNotes || char.castingNotes,
        role: assignment?.role || char.role,
        assignedVoice: assignment
          ? {
              provider: assignment.provider,
              voiceName: assignment.voiceEntry?.sts_id || assignment.sts_id,
              voiceId: assignment.sts_id,
            }
          : null,
      };
      return characterInfo;
    });
  }, [charactersData, assignments]);

  // Calculate assignment progress
  const assignedCount = characters.filter((char) => char.assignedVoice).length;
  const totalCount = characters.length;
  const progressPercentage =
    totalCount > 0 ? (assignedCount / totalCount) * 100 : 0;

  const handleBack = () => {
    navigateToIndex();
  };

  const handleAssignVoice = (characterName: string) => {
    navigateToAssign(sessionId, characterName);
  };

  const handlePreviewYaml = () => {
    navigateToPreview(sessionId);
  };

  const handleExportYaml = () => {
    // Navigate to preview page for export functionality
    navigateToPreview(sessionId);
  };

  const handleImport = () => {
    navigateToImport(sessionId);
  };

  const handleLLMCharacterNotes = () => {
    navigateToNotes(sessionId);
  };

  const handleLLMVoiceLibrary = () => {
    navigateToLibrary(sessionId);
  };

  // Loading state
  if (isLoading || sessionLoading) {
    return (
      <div className="container mx-auto max-w-6xl space-y-6 p-6">
        <div className="flex h-64 items-center justify-center">
          <div className="space-y-4 text-center">
            <Loader2 className="text-muted-foreground mx-auto h-8 w-8 animate-spin" />
            <p className="text-muted-foreground">
              Loading voice casting session...
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error || sessionError) {
    return (
      <div className="container mx-auto max-w-6xl space-y-6 p-6">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Failed to load voice casting session:{' '}
            {error?.message || sessionError?.message}
          </AlertDescription>
        </Alert>
        <Button variant="outline" onClick={handleBack}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Voice Casting
        </Button>
      </div>
    );
  }

  return (
    <div className="container mx-auto max-w-6xl space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={handleBack}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold">Voice Casting</h1>
            <p className="text-muted-foreground">
              {session?.screenplay_name ||
                charactersData?.screenplay_name ||
                'Screenplay'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={handleImport}>
            <Upload className="mr-2 h-4 w-4" />
            Import
          </Button>
          <Button
            variant="outline"
            onClick={handlePreviewYaml}
            disabled={assignedCount === 0}
          >
            <Eye className="mr-2 h-4 w-4" />
            Preview YAML
          </Button>
          <Button onClick={handleExportYaml} disabled={assignedCount === 0}>
            <Download className="mr-2 h-4 w-4" />
            Export Configuration
          </Button>
        </div>
      </div>

      {/* Progress */}
      <div className="bg-card space-y-3 rounded-lg border p-4">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <p className="text-sm font-medium">Assignment Progress</p>
            <p className="text-muted-foreground text-xs">
              {assignedCount} of {totalCount} characters assigned
            </p>
          </div>
          <Badge
            variant={assignedCount === totalCount ? 'default' : 'secondary'}
          >
            {Math.round(progressPercentage)}% Complete
          </Badge>
        </div>
        <Progress value={progressPercentage} className="h-2" />
      </div>

      {/* LLM-Assisted Features */}
      <div className="bg-card space-y-3 rounded-lg border p-4">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <p className="flex items-center gap-2 text-sm font-medium">
              <Brain className="h-4 w-4" />
              LLM-Assisted Features
            </p>
            <p className="text-muted-foreground text-xs">
              Use AI to analyze characters and suggest voice assignments
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleLLMCharacterNotes}>
            <FileText className="mr-2 h-4 w-4" />
            Character Analysis
          </Button>
          <Button variant="outline" size="sm" onClick={handleLLMVoiceLibrary}>
            <Brain className="mr-2 h-4 w-4" />
            Voice Suggestions
          </Button>
        </div>
      </div>

      {/* Character List */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Characters</h2>
          <div className="text-muted-foreground flex items-center gap-4 text-sm">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-green-500" />
              <span>Assigned</span>
            </div>
            <div className="flex items-center gap-2">
              <Circle className="h-4 w-4" />
              <span>Unassigned</span>
            </div>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          {characters.map((character) => (
            <CharacterCard
              key={character.name}
              character={character}
              onAssignVoice={() => handleAssignVoice(character.name)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
