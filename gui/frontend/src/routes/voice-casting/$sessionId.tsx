import { useQuery } from '@tanstack/react-query';
import { createFileRoute, Outlet, useNavigate, useRouterState } from '@tanstack/react-router';
import { AlertCircle, ArrowLeft, Brain, CheckCircle2, Circle, Download, Eye, FileText,Loader2, Upload } from 'lucide-react';
import { useEffect,useState } from 'react';

import { RouteError } from '@/components/errors';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { 
  CharacterCard,
  VoiceAssignmentPanel,
  YamlImportPanel,
  YamlPreview} from '@/components/voice-casting';
import { useScreenplayCharacters } from '@/hooks/queries/useScreenplayCharacters';
import { apiService } from '@/services/api';
import { type CharacterInfo,useVoiceCasting } from '@/stores/appStore';

export const Route = createFileRoute('/voice-casting/$sessionId')({
  component: VoiceCastingMain,
  errorComponent: RouteError,
});

function VoiceCastingMain() {
  const { sessionId } = Route.useParams();
  const navigate = useNavigate();
  const routerState = useRouterState();
  
  // Check if we're on a child route (notes or library)
  const isOnChildRoute = routerState.location.pathname.includes('/notes') || 
                         routerState.location.pathname.includes('/library');
  const [selectedCharacter, setSelectedCharacter] = useState<string | null>(null);
  const [showAssignmentPanel, setShowAssignmentPanel] = useState(false);
  const [showYamlPreview, setShowYamlPreview] = useState(false);
  const [showImportPanel, setShowImportPanel] = useState(false);

  // Fetch session data
  const { data: session, isLoading: sessionLoading, error: sessionError } = useQuery({
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
  const { data: charactersData, isLoading, error } = useScreenplayCharacters(
    session?.screenplay_json_path
  );
  
  // Connect to voice casting store
  const {
    castingSessionId,
    screenplayJsonPath,
    screenplayData,
    assignments,
    setCastingSessionId,
    setScreenplayJsonPath,
    setScreenplayData,
    setCharacterAssignment,
    resetCastingState,
  } = useVoiceCasting();

  // Initialize store with session ID and character data when component mounts
  useEffect(() => {
    if (sessionId && sessionId !== castingSessionId) {
      setCastingSessionId(sessionId);
    }
    
    if (charactersData && session) {
      // Store the file path
      if (session.screenplay_json_path && session.screenplay_json_path !== screenplayJsonPath) {
        setScreenplayJsonPath(session.screenplay_json_path);
      }
      
      if (!screenplayData) {
        // Convert character data to the format expected by the store
        const charactersMap = new Map<string, CharacterInfo>();
        Object.entries(charactersData.characters).forEach(([name, info]) => {
          charactersMap.set(name, info);
        });
        
        setScreenplayData({
          characters: charactersMap,
        });
      }
    }
  }, [sessionId, castingSessionId, charactersData, screenplayData, screenplayJsonPath, session, setCastingSessionId, setScreenplayData, setScreenplayJsonPath]);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      // Optional: Reset casting state when leaving the page
      // resetCastingState();
    };
  }, []);

  // Transform character data for display
  const characters = charactersData ? Object.entries(charactersData.characters).map(([name, info]) => {
    const assignment = assignments.get(name);
    return {
      name,
      displayName: name === 'default' ? 'Narrator' : name,
      lineCount: info.lineCount,
      totalCharacters: info.totalCharacters || 0,
      longestDialogue: info.longestDialogue || 0,
      isNarrator: info.isNarrator || false,
      castingNotes: assignment?.castingNotes,
      role: assignment?.role,
      assignedVoice: assignment ? {
        provider: assignment.provider,
        voiceName: assignment.voiceEntry?.sts_id || assignment.sts_id,
        voiceId: assignment.sts_id,
      } : null,
    };
  }) : [];

  // Calculate progress
  const assignedCount = characters.filter(c => c.assignedVoice).length;
  const totalCount = characters.length;
  const progressPercentage = totalCount > 0 ? (assignedCount / totalCount) * 100 : 0;

  const handleBack = () => {
    navigate({ to: '/voice-casting' });
  };

  const handleAssignVoice = (characterName: string) => {
    setSelectedCharacter(characterName);
    setShowAssignmentPanel(true);
  };

  const handleVoiceAssigned = () => {
    setShowAssignmentPanel(false);
    setSelectedCharacter(null);
  };

  const handlePreviewYaml = () => {
    setShowYamlPreview(true);
  };

  const handleExportYaml = () => {
    // This will be handled in the YamlPreview component
  };
  
  const handleImport = () => {
    setShowImportPanel(true);
  };
  
  const handleImportSuccess = () => {
    setShowImportPanel(false);
    // The assignments are already updated in the store by the import panel
  };

  const handleLLMCharacterNotes = () => {
    navigate({ to: '/voice-casting/$sessionId/notes', params: { sessionId } });
  };

  const handleLLMVoiceLibrary = () => {
    navigate({ to: '/voice-casting/$sessionId/library', params: { sessionId } });
  };

  // Loading state
  if (isLoading || sessionLoading) {
    return (
      <div className="container max-w-6xl mx-auto p-6 space-y-6">
        <div className="flex items-center justify-center h-64">
          <div className="text-center space-y-4">
            <Loader2 className="h-8 w-8 animate-spin mx-auto text-muted-foreground" />
            <p className="text-muted-foreground">Loading screenplay characters...</p>
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error || sessionError) {
    return (
      <div className="container max-w-6xl mx-auto p-6 space-y-6">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Failed to load screenplay characters: {error?.message || sessionError?.message}
          </AlertDescription>
        </Alert>
        <Button variant="outline" onClick={handleBack}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Voice Casting
        </Button>
      </div>
    );
  }

  if (showAssignmentPanel && selectedCharacter) {
    const character = characters.find(c => c.name === selectedCharacter);
    if (!character) return null;
    
    return (
      <VoiceAssignmentPanel
        characterName={selectedCharacter}
        character={character}
        onBack={() => setShowAssignmentPanel(false)}
        onAssign={handleVoiceAssigned}
      />
    );
  }

  if (showYamlPreview) {
    return (
      <YamlPreview
        characters={characters}
        onBack={() => setShowYamlPreview(false)}
        onExport={handleExportYaml}
      />
    );
  }
  
  if (showImportPanel) {
    return (
      <YamlImportPanel
        onBack={() => setShowImportPanel(false)}
        onImportSuccess={handleImportSuccess}
      />
    );
  }

  // If we're on a child route (notes or library), render the outlet
  if (isOnChildRoute) {
    return <Outlet />;
  }

  return (
    <div className="container max-w-6xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={handleBack}
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold">Voice Casting</h1>
            <p className="text-muted-foreground">
              {session?.screenplay_name || charactersData?.screenplay_name || 'Screenplay'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={handleImport}
          >
            <Upload className="h-4 w-4 mr-2" />
            Import
          </Button>
          <Button
            variant="outline"
            onClick={handlePreviewYaml}
            disabled={assignedCount === 0}
          >
            <Eye className="h-4 w-4 mr-2" />
            Preview YAML
          </Button>
          <Button
            onClick={handleExportYaml}
            disabled={assignedCount === 0}
          >
            <Download className="h-4 w-4 mr-2" />
            Export Configuration
          </Button>
        </div>
      </div>

      {/* Progress */}
      <div className="bg-card rounded-lg border p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <p className="text-sm font-medium">Assignment Progress</p>
            <p className="text-xs text-muted-foreground">
              {assignedCount} of {totalCount} characters assigned
            </p>
          </div>
          <Badge variant={assignedCount === totalCount ? "default" : "secondary"}>
            {Math.round(progressPercentage)}% Complete
          </Badge>
        </div>
        <Progress value={progressPercentage} className="h-2" />
      </div>

      {/* LLM-Assisted Features */}
      <div className="bg-card rounded-lg border p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <p className="text-sm font-medium flex items-center gap-2">
              <Brain className="h-4 w-4" />
              LLM-Assisted Features
            </p>
            <p className="text-xs text-muted-foreground">
              Use AI to analyze characters and suggest voice assignments
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleLLMCharacterNotes}
          >
            <FileText className="h-4 w-4 mr-2" />
            Character Analysis
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleLLMVoiceLibrary}
          >
            <Brain className="h-4 w-4 mr-2" />
            Voice Suggestions
          </Button>
        </div>
      </div>

      {/* Character List */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Characters</h2>
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
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