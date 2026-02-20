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
import { appButtonVariants } from '@/components/ui/button-variants';
import { Progress } from '@/components/ui/progress';
import { CharacterCard } from '@/components/voice-casting';
import { useScreenplayCharacters } from '@/hooks/queries/useScreenplayCharacters';
import { useSessionAssignments } from '@/hooks/queries/useSessionAssignments';
import { useVoiceCastingNavigation } from '@/hooks/useVoiceCastingNavigation';
import { apiService } from '@/services/api';
import { useProject } from '@/stores/appStore';
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
  const [isDownloading, setIsDownloading] = useState(false);
  const navigate = useNavigate();
  const { mode } = useProject();
  const isProjectMode = mode === 'project';
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

      // Clear highlight state after animation completes (4 seconds)
      const timer = setTimeout(() => {
        navigate({
          to: '.',
          replace: true,
          state: {},
        });
      }, 4000);

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
        ...(assignment?.casting_notes && {
          castingNotes: assignment.casting_notes,
        }),
        ...(assignment?.role && { role: assignment.role }),
        ...(assignment?.additional_notes?.length && {
          additionalNotes: assignment.additional_notes,
        }),
        // Only mark as assigned if there's actual voice data (not just empty provider)
        assignedVoice:
          assignment &&
          assignment.provider &&
          assignment.sts_id && // Ensure sts_id exists
          (assignment.sts_id || assignment.provider_config)
            ? {
                provider: assignment.provider,
                voiceName: assignment.sts_id,
                voiceId: assignment.sts_id, // Now guaranteed to be string
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

  const handleDownloadYaml = async () => {
    if (!sessionData || !session) {
      toast.error('No active session found');
      return;
    }

    if (assignedCount === 0) {
      toast.error('No voice assignments to download');
      return;
    }

    setIsDownloading(true);

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
          `Download completed with warnings:\n${warningMessages.join('\n')}`,
          {
            duration: 6000,
          }
        );
      } else {
        toast.success('Configuration downloaded successfully!');
      }

      // Download the YAML file (now uses native save dialog in Tauri)
      const filename = `${session.screenplay_name}_voice_config.yaml`;
      await yamlUtils.downloadYamlFile(yamlContent, filename);

      // Clear unsaved changes flag and recovery data on successful export - DISABLED FOR DEBUGGING
      // setHasUnsavedChanges(false);
      // localStorage.removeItem(`yaml_recovery_${sessionId}`);
    } catch (error) {
      console.error('Download failed:', error);
      const errorMessage =
        error instanceof Error ? error.message : 'Download failed';
      toast.error(`Download failed: ${errorMessage}`);
    } finally {
      setIsDownloading(false);
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

  const handleScrollToCharacter = (characterName: string) => {
    navigate({
      to: '.',
      replace: true,
      state: { highlightCharacter: characterName },
    });
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
        {!isProjectMode && (
          <button
            className={appButtonVariants({
              variant: 'secondary',
              size: 'sm',
            })}
            onClick={handleBack}
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Voice Casting
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col overflow-x-hidden overflow-y-auto">
      <div className="container mx-auto max-w-6xl space-y-6 p-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            {!isProjectMode && (
              <button
                className={appButtonVariants({
                  variant: 'secondary',
                  size: 'icon',
                })}
                onClick={handleBack}
              >
                <ArrowLeft className="h-4 w-4" />
              </button>
            )}
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
            <button
              className={appButtonVariants({
                variant: 'secondary',
                size: 'sm',
              })}
              onClick={handleImport}
            >
              <Upload className="mr-2 h-4 w-4" />
              Import
            </button>
            <button
              className={appButtonVariants({
                variant: 'secondary',
                size: 'sm',
              })}
              onClick={handlePreviewYaml}
              disabled={assignedCount === 0}
            >
              <Eye className="mr-2 h-4 w-4" />
              Preview YAML
            </button>
            <button
              className={appButtonVariants({
                variant: 'primary',
                size: 'sm',
              })}
              onClick={handleDownloadYaml}
              disabled={assignedCount === 0 || isDownloading}
            >
              {isDownloading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Download className="mr-2 h-4 w-4" />
              )}
              {isDownloading ? 'Downloading...' : 'Download Configuration'}
            </button>
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
            <button
              className={appButtonVariants({
                variant: 'secondary',
                size: 'sm',
              })}
              onClick={handleLLMCharacterNotes}
            >
              <FileText className="mr-2 h-4 w-4" />
              Character Analysis
            </button>
            <button
              className={appButtonVariants({
                variant: 'secondary',
                size: 'sm',
              })}
              onClick={handleLLMVoiceLibrary}
            >
              <Brain className="mr-2 h-4 w-4" />
              Voice Suggestions
            </button>
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
                onScrollToCharacter={handleScrollToCharacter}
                shouldHighlight={character.name === highlightCharacter}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
