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
import { useMemo, useState } from 'react';
import { toast } from 'sonner';

import { RouteError } from '@/components/errors';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { CharacterCard } from '@/components/voice-casting/CharacterCard.rq'; // Use RQ version
import { useSessionAssignments } from '@/hooks/queries/useSessionAssignments';
import { useUpdateSessionYaml } from '@/hooks/mutations/useUpdateSessionYaml';
import { useVoiceCastingNavigation } from '@/hooks/useVoiceCastingNavigation';
import { useVoiceCastingUI } from '@/stores/uiStore';
import type { RouteStaticData } from '@/types/route-metadata';
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
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  
  const {
    navigateToIndex,
    navigateToAssign,
    navigateToPreview,
    navigateToImport,
    navigateToNotes,
    navigateToLibrary,
  } = useVoiceCastingNavigation();

  // Use React Query to fetch session with derived state
  const {
    data: sessionData,
    isLoading,
    error,
    refetch,
  } = useSessionAssignments(sessionId);

  // UI state from UI store
  const {
    searchQuery,
    filterProvider,
    sortBy,
    sortDirection,
    showOnlyUnassigned,
    setSearchQuery,
  } = useVoiceCastingUI();

  // Mutation for updating YAML
  const updateYamlMutation = useUpdateSessionYaml();

  // Calculate assignment statistics
  const stats = useMemo(() => {
    if (!sessionData) {
      return {
        totalCharacters: 0,
        assignedCount: 0,
        completionPercentage: 0,
      };
    }

    return {
      totalCharacters: sessionData.totalCount,
      assignedCount: sessionData.assignedCount,
      completionPercentage: sessionData.progress,
    };
  }, [sessionData]);

  // Filter and sort characters
  const displayCharacters = useMemo(() => {
    if (!sessionData?.characters) return [];

    let chars = Array.from(sessionData.characters.entries());

    // Apply search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      chars = chars.filter(([name]) => 
        name.toLowerCase().includes(query)
      );
    }

    // Apply provider filter
    if (filterProvider) {
      chars = chars.filter(([name]) => {
        const assignment = sessionData.assignments.get(name);
        return assignment?.provider === filterProvider;
      });
    }

    // Apply unassigned filter
    if (showOnlyUnassigned) {
      chars = chars.filter(([name]) => {
        const assignment = sessionData.assignments.get(name);
        return !assignment || !assignment.provider;
      });
    }

    // Sort characters
    chars.sort(([nameA, charA], [nameB, charB]) => {
      let comparison = 0;
      
      switch (sortBy) {
        case 'name':
          comparison = nameA.localeCompare(nameB);
          break;
        case 'lines':
          comparison = (charB[1].lineCount || 0) - (charA[1].lineCount || 0);
          break;
        case 'assigned':
          const assignedA = sessionData.assignments.has(nameA) ? 1 : 0;
          const assignedB = sessionData.assignments.has(nameB) ? 1 : 0;
          comparison = assignedB - assignedA;
          break;
      }
      
      return sortDirection === 'asc' ? comparison : -comparison;
    });

    return chars;
  }, [sessionData, searchQuery, filterProvider, showOnlyUnassigned, sortBy, sortDirection]);

  // Handle YAML export
  const handleExport = async () => {
    if (!sessionData) return;

    setIsExporting(true);
    try {
      // Generate YAML from current assignments
      const yamlContent = await yamlUtils.assignmentsToYaml(
        sessionData.assignments,
        sessionData.characters
      );

      // Update backend with version ID
      await updateYamlMutation.mutateAsync({
        sessionId,
        yamlContent,
        versionId: sessionData.yamlVersionId || 1,
      });

      // Download the YAML file
      yamlUtils.downloadYamlFile(
        yamlContent,
        `${sessionData.session.screenplay_name}_voice_config.yaml`
      );

      toast.success('Configuration exported successfully!');
      setHasUnsavedChanges(false);
    } catch (error: any) {
      if (error.message?.includes('modified by another source')) {
        toast.error('Session was modified by another user. Please refresh and try again.');
        refetch(); // Refresh session data
      } else {
        toast.error('Export failed: ' + (error.message || 'Unknown error'));
      }
    } finally {
      setIsExporting(false);
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="flex flex-col items-center gap-2">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <span className="text-sm text-muted-foreground">Loading session...</span>
        </div>
      </div>
    );
  }

  // Error state
  if (error || !sessionData) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <Alert variant="destructive" className="max-w-md">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            {error?.message || 'Failed to load session data'}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={navigateToIndex}
              className="gap-2"
            >
              <ArrowLeft className="h-4 w-4" />
              Back
            </Button>
            <div>
              <h1 className="text-lg font-semibold">
                {sessionData.session.screenplay_name}
              </h1>
              <p className="text-sm text-muted-foreground">
                Voice Casting Session
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Import YAML */}
            <Button
              variant="outline"
              size="sm"
              onClick={navigateToImport}
              className="gap-2"
            >
              <Upload className="h-4 w-4" />
              Import YAML
            </Button>

            {/* Generate Notes */}
            <Button
              variant="outline"
              size="sm"
              onClick={navigateToNotes}
              className="gap-2"
            >
              <Brain className="h-4 w-4" />
              Generate Notes
            </Button>

            {/* Export YAML */}
            <Button
              variant="default"
              size="sm"
              onClick={handleExport}
              disabled={isExporting || updateYamlMutation.isPending}
              className="gap-2"
            >
              {isExporting ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Download className="h-4 w-4" />
              )}
              Export YAML
            </Button>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mt-4">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">
              {stats.assignedCount} of {stats.totalCharacters} characters assigned
            </span>
            <span className="font-medium">
              {Math.round(stats.completionPercentage)}%
            </span>
          </div>
          <Progress
            value={stats.completionPercentage}
            className="mt-2 h-2"
          />
        </div>

        {/* Unsaved Changes Warning */}
        {hasUnsavedChanges && (
          <Alert className="mt-4">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              You have unsaved changes. Click Export YAML to save your assignments.
            </AlertDescription>
          </Alert>
        )}
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {/* Search Bar */}
        <div className="mb-4">
          <input
            type="text"
            placeholder="Search characters..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-md border px-3 py-2 text-sm"
          />
        </div>

        {/* Character Grid */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {displayCharacters.map(([name, character]) => {
            const assignment = sessionData.assignments.get(name);
            const isAssigned = !!(
              assignment?.provider &&
              (assignment.sts_id || assignment.provider_config)
            );

            return (
              <CharacterCard
                key={name}
                sessionId={sessionId}
                character={{
                  name,
                  displayName: name,
                  lineCount: character.lineCount,
                  totalCharacters: character.totalCharacters,
                  longestDialogue: character.longestDialogue,
                  isNarrator: name === 'default',
                  castingNotes: assignment?.castingNotes,
                  role: assignment?.role,
                  assignedVoice: isAssigned && assignment
                    ? {
                        provider: assignment.provider,
                        voiceName: assignment.sts_id || 'Custom Voice',
                        voiceId: assignment.sts_id || '',
                      }
                    : null,
                }}
                onAssignVoice={() => navigateToAssign(name)}
              />
            );
          })}
        </div>

        {/* Empty State */}
        {displayCharacters.length === 0 && (
          <div className="flex h-64 items-center justify-center">
            <div className="text-center">
              <FileText className="mx-auto h-12 w-12 text-muted-foreground/50" />
              <p className="mt-2 text-sm text-muted-foreground">
                No characters found matching your filters
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="border-t px-6 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="gap-1">
              <Circle className="h-3 w-3" />
              {stats.totalCharacters - stats.assignedCount} Unassigned
            </Badge>
            <Badge variant="outline" className="gap-1">
              <CheckCircle2 className="h-3 w-3" />
              {stats.assignedCount} Assigned
            </Badge>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={navigateToLibrary}
              className="gap-2"
            >
              <Eye className="h-4 w-4" />
              View Library
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={navigateToPreview}
              className="gap-2"
            >
              <FileText className="h-4 w-4" />
              Preview YAML
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}