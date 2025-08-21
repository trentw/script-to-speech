import { useQuery } from '@tanstack/react-query';
import {
  createFileRoute,
  useNavigate,
  useRouterState,
} from '@tanstack/react-router';
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
import { useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';

import { RouteError } from '@/components/errors';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { CharacterCard } from '@/components/voice-casting';
import { useScreenplayCharacters } from '@/hooks/queries/useScreenplayCharacters';
import { useSessionAssignments } from '@/hooks/queries/useSessionAssignments';
import { useVoiceCastingNavigation } from '@/hooks/useVoiceCastingNavigation';
import { apiService } from '@/services/api';
import type { RouteStaticData } from '@/types/route-metadata';
import { calculateVoiceUsage } from '@/utils/voiceUsageHelper';
import { yamlUtils } from '@/utils/yamlUtils';

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
  const [isExporting, setIsExporting] = useState(false);
  const navigate = useNavigate();
  const {
    navigateToIndex,
    navigateToAssign,
    navigateToPreview,
    navigateToImport,
    navigateToNotes,
    navigateToLibrary,
  } = useVoiceCastingNavigation();

  // Get highlight character from location state
  const location = useRouterState({ select: (s) => s.location });
  const highlightCharacter = location.state?.highlightCharacter;

  // Handle character highlighting effect
  useEffect(() => {
    if (highlightCharacter) {
      // Wait for DOM to be ready, then scroll to the highlighted character
      const scrollToCharacter = () => {
        const characterElement = document.querySelector(
          `[data-character-name="${highlightCharacter}"]`
        );
        if (characterElement) {
          characterElement.scrollIntoView({
            behavior: 'smooth',
            block: 'center',
          });
        }
      };

      // Use requestAnimationFrame to ensure DOM is ready
      const frameId = requestAnimationFrame(() => {
        setTimeout(scrollToCharacter, 50); // Small delay for layout
      });

      // Clear highlight state after animation completes (2.5 seconds)
      const timer = setTimeout(() => {
        navigate({
          to: '.',
          replace: true,
          state: {},
        });
      }, 2500);

      return () => {
        clearTimeout(timer);
        cancelAnimationFrame(frameId);
      };
    }
  }, [highlightCharacter, navigate]);

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

  // Fetch session assignments using React Query
  const {
    data: sessionData,
    isLoading: sessionDataLoading,
    error: sessionDataError,
  } = useSessionAssignments(sessionId);

  // Data loss prevention state - DISABLED FOR DEBUGGING
  // const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  // Check for recovery data after session loads - DISABLED FOR DEBUGGING
  // useEffect(() => {
  //   // Only check for recovery after session data and characters have loaded
  //   if (!session || !charactersData) return;
  //
  //   const recoveryKey = `yaml_recovery_${sessionId}`;
  //   const recoveryData = localStorage.getItem(recoveryKey);
  //
  //   if (recoveryData) {
  //     try {
  //       const data = JSON.parse(recoveryData);
  //       const age = Date.now() - data.timestamp;
  //
  //       // Only offer recovery for data less than 1 hour old
  //       if (age < 3600000) { // 1 hour = 3600000ms
  //         const timeStr = new Date(data.timestamp).toLocaleTimeString();
  //         const shouldRecover = window.confirm(
  //           `Found unsaved work from ${timeStr}. Would you like to recover it?\n\n` +
  //           'This will replace any current assignments with your unsaved changes.'
  //         );
  //
  //         if (shouldRecover && data.assignments) {
  //           // Restore assignments from recovery data
  //           const recoveredAssignments = new Map(data.assignments);
  //           const activeSession = getActiveSession();
  //           if (activeSession) {
  //             selectOrCreateSession(sessionId, {
  //               ...activeSession,
  //               assignments: recoveredAssignments,
  //               yamlContent: data.yaml || activeSession.yamlContent,
  //               yaml_version_id: data.versionId || activeSession.yaml_version_id,
  //             });
  //             setHasUnsavedChanges(true);
  //             toast.info('Recovered unsaved work. Remember to click Export to save.');
  //           }
  //         } else {
  //           localStorage.removeItem(recoveryKey);
  //         }
  //       } else {
  //         // Remove stale recovery data
  //         localStorage.removeItem(recoveryKey);
  //       }
  //     } catch (error) {
  //       console.error('Failed to parse recovery data:', error);
  //       localStorage.removeItem(recoveryKey);
  //     }
  //   }
  // }, [session, charactersData, sessionId]);

  // // Keep track of the initial assignments to detect changes - DISABLED FOR DEBUGGING
  // const [initialAssignments, setInitialAssignments] = useState<Map<string, VoiceAssignment> | null>(null);

  // // Set initial assignments when session first loads
  // useEffect(() => {
  //   if (session && currentAssignments && !initialAssignments) {
  //     // Create a deep copy of the assignments to track the initial state
  //     setInitialAssignments(new Map(currentAssignments));
  //     setHasUnsavedChanges(false); // Reset unsaved changes when loading fresh session
  //   }
  // }, [session, currentAssignments, initialAssignments]);

  // // Detect actual changes to assignments
  // useEffect(() => {
  //   if (!initialAssignments || !currentAssignments) return;
  //
  //   // Compare current assignments with initial state
  //   const hasChanges =
  //     currentAssignments.size !== initialAssignments.size ||
  //     Array.from(currentAssignments.entries()).some(([character, assignment]) => {
  //       const initial = initialAssignments.get(character);
  //       return !initial || JSON.stringify(assignment) !== JSON.stringify(initial);
  //     });
  //
  //   setHasUnsavedChanges(hasChanges);
  // }, [currentAssignments, initialAssignments]);

  // // Auto-save to localStorage for recovery
  // useEffect(() => {
  //   const activeSession = getActiveSession();
  //   if (activeSession && hasUnsavedChanges && currentAssignments) {
  //     const recovery = {
  //       yaml: activeSession.yamlContent || '',
  //       assignments: Array.from(currentAssignments.entries()),
  //       timestamp: Date.now(),
  //       versionId: activeSession.yaml_version_id || 1
  //     };
  //     localStorage.setItem(`yaml_recovery_${sessionId}`, JSON.stringify(recovery));
  //   }
  // }, [sessionId, currentAssignments, hasUnsavedChanges, getActiveSession]);

  // // Warn before navigation if there are unsaved changes
  // useEffect(() => {
  //   const handleBeforeUnload = (e: BeforeUnloadEvent) => {
  //     if (hasUnsavedChanges) {
  //       e.preventDefault();
  //       e.returnValue = 'You have unsaved changes. Click Export to save.';
  //       return 'You have unsaved changes. Click Export to save.';
  //     }
  //   };
  //
  //   window.addEventListener('beforeunload', handleBeforeUnload);
  //   return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  // }, [hasUnsavedChanges]);

  // Transform character data for display
  const characters = useMemo(() => {
    if (!charactersData) return [];
    if (!sessionData) return [];

    // Defensive check for assignments - it should always be a Map from useSessionAssignments
    // but during cache updates it might be temporarily undefined
    const assignments = sessionData.assignments || new Map();

    return Object.entries(charactersData.characters).map(([name, char]) => {
      const assignment = assignments.get(name);
      const characterInfo = {
        name,
        displayName: name === 'default' ? 'Narrator' : name,
        lineCount: char.lineCount,
        totalCharacters: char.totalCharacters || 0,
        longestDialogue: char.longestDialogue || 0,
        isNarrator: char.isNarrator || false,
        // Assignments are the single source of truth for user-editable metadata
        castingNotes: assignment?.castingNotes,
        role: assignment?.role,
        // Only mark as assigned if there's actual voice data (not just empty provider)
        assignedVoice:
          assignment &&
          assignment.provider &&
          (assignment.sts_id || assignment.provider_config)
            ? {
                provider: assignment.provider,
                voiceName: assignment.voiceEntry?.sts_id || assignment.sts_id,
                voiceId: assignment.sts_id,
              }
            : null,
      };
      return characterInfo;
    });
  }, [charactersData, sessionData]);

  // Calculate assignment progress
  const assignedCount = characters.filter((char) => char.assignedVoice).length;
  const totalCount = characters.length;
  const progressPercentage =
    totalCount > 0 ? (assignedCount / totalCount) * 100 : 0;

  // Memoize voice usage calculations to avoid O(n²) complexity
  const voiceUsageMaps = useMemo(() => {
    if (!sessionData) return new Map();

    const maps = new Map();
    characters.forEach((character) => {
      maps.set(
        character.name,
        calculateVoiceUsage(
          sessionData.assignments || new Map(),
          sessionData.characters || new Map(),
          character.name
        )
      );
    });
    return maps;
  }, [sessionData, characters]);

  const handleBack = () => {
    navigateToIndex();
  };

  const handleAssignVoice = (characterName: string) => {
    navigateToAssign(sessionId, characterName);
  };

  const handlePreviewYaml = () => {
    navigateToPreview(sessionId);
  };

  const handleExportYaml = async () => {
    if (!sessionData || !session) {
      toast.error('No active session found');
      return;
    }

    if (assignedCount === 0) {
      toast.error('No voice assignments to export');
      return;
    }

    setIsExporting(true);

    try {
      // Use the stored YAML content as source of truth
      // If no YAML content exists (shouldn't happen), fall back to generating
      let yamlContent = sessionData.yamlContent;

      if (!yamlContent || yamlContent.trim() === '') {
        // This should rarely happen since backend generates initial YAML
        // But if it does, we can generate a basic structure
        toast.warning('No stored YAML found, generating from assignments');
        yamlContent = await yamlUtils.assignmentsToYaml(
          sessionData.assignments || new Map(),
          characters
        );
      }

      // Save to backend with version control
      const versionId = sessionData.yamlVersionId || 1;
      const response = await apiService.updateSessionYaml(
        sessionId,
        yamlContent,
        versionId
      );

      if (response.error) {
        // Check for version conflict errors
        if (
          response.error.includes('409') ||
          response.error.includes('modified') ||
          response.error.includes('concurrent')
        ) {
          toast.error(
            'Session was modified by another source. Please refresh and try again.'
          );
          return;
        }
        throw new Error(response.error);
      }

      // Show validation warnings if present (non-blocking)
      if (response.data?.warnings && response.data.warnings.length > 0) {
        const warningMessages = response.data.warnings.slice(0, 3); // Limit to first 3 warnings
        toast.warning(
          `Export completed with warnings:\n${warningMessages.join('\n')}`,
          {
            duration: 6000,
          }
        );
      } else {
        toast.success('Configuration exported successfully!');
      }

      // Download the YAML file
      const filename = `${session.screenplay_name}_voice_config.yaml`;
      yamlUtils.downloadYamlFile(yamlContent, filename);

      // Clear unsaved changes flag and recovery data on successful export - DISABLED FOR DEBUGGING
      // setHasUnsavedChanges(false);
      // localStorage.removeItem(`yaml_recovery_${sessionId}`);
    } catch (error) {
      console.error('Export failed:', error);
      const errorMessage =
        error instanceof Error ? error.message : 'Export failed';
      toast.error(`Export failed: ${errorMessage}`);
    } finally {
      setIsExporting(false);
    }
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
  if (isLoading || sessionLoading || sessionDataLoading) {
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
  if (error || sessionError || sessionDataError) {
    return (
      <div className="container mx-auto max-w-6xl space-y-6 p-6">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Failed to load voice casting session:{' '}
            {error?.message ||
              sessionError?.message ||
              sessionDataError?.message}
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
          <Button
            onClick={handleExportYaml}
            disabled={assignedCount === 0 || isExporting}
          >
            {isExporting ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Download className="mr-2 h-4 w-4" />
            )}
            {isExporting ? 'Exporting...' : 'Export Configuration'}
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

        {/* Unsaved changes indicator - DISABLED FOR DEBUGGING */}
        {/* {hasUnsavedChanges && (
          <div className="flex items-center gap-2 text-amber-600 text-sm">
            <AlertCircle className="h-4 w-4" />
            <span>⚠️ Unsaved changes - Click Export to save</span>
          </div>
        )} */}
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
              sessionId={sessionId}
              assignment={sessionData?.assignments?.get(character.name)}
              yamlVersionId={sessionData?.yamlVersionId}
              voiceUsageMap={voiceUsageMaps.get(character.name) || new Map()}
              onAssignVoice={() => handleAssignVoice(character.name)}
              shouldHighlight={character.name === highlightCharacter}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
