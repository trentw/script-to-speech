import { useMutation } from '@tanstack/react-query';
import { createFileRoute, useNavigate } from '@tanstack/react-router';
import {
  AlertCircle,
  ChevronRight,
  FileJson,
  Loader2,
  Upload,
} from 'lucide-react';
import { useState } from 'react';

import { RouteError } from '@/components/errors';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { FileUploadZone } from '@/components/ui/file-upload-zone';
import { interactiveCardVariants } from '@/components/ui/interactive.variants';
import {
  CastingMethodSelector,
  VoiceCastingHistoryList,
} from '@/components/voice-casting';
import { useRecentScreenplays } from '@/hooks/queries/useRecentScreenplays';
import { useVoiceCastingSessions } from '@/hooks/useVoiceCastingSessions';
import { apiService } from '@/services/api';
type VoiceCastingSearch = {
  method?: 'select';
};

export const Route = createFileRoute('/voice-casting/')<{
  Search: VoiceCastingSearch;
}>({
  validateSearch: (search: Record<string, unknown>): VoiceCastingSearch => {
    if (search.method === 'select') {
      return { method: 'select' };
    }
    return {};
  },
  component: VoiceCastingUpload,
  errorComponent: RouteError,
});

function VoiceCastingUpload() {
  const navigate = useNavigate();
  const { method } = Route.useSearch();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [creatingSession, setCreatingSession] = useState<string | null>(null);
  const [pendingSessionId, setPendingSessionId] = useState<string | null>(null);

  // Show method selector based on search parameter
  const showMethodSelector = method === 'select';

  // Fetch recent completed screenplay parsing tasks
  const { data: screenplays, isLoading } = useRecentScreenplays(5);

  // Fetch recent voice casting sessions
  const { data: recentSessions = [] } = useVoiceCastingSessions(5);

  // Mutation for uploading JSON file
  const uploadJsonMutation = useMutation({
    mutationFn: async (file: File) => {
      const response = await apiService.uploadScreenplayJson(file);
      if (response.error) {
        throw new Error(response.error);
      }
      return response.data;
    },
    onSuccess: (data) => {
      // Show method selector instead of navigating directly
      setPendingSessionId(data.session_id);
      navigate({ to: '.', search: { method: 'select' } });
    },
  });

  // Map the screenplay data for display
  const recentScreenplays =
    screenplays?.map((screenplay) => ({
      id: screenplay.task_id,
      name: screenplay.screenplay_name || 'Untitled Screenplay',
      characters: screenplay.analysis?.total_distinct_speakers || 0,
      lines: screenplay.analysis?.total_chunks || 0,
      date: new Date(screenplay.created_at).toLocaleDateString(),
    })) || [];

  const handleFileSelect = (file: File) => {
    setSelectedFile(file);
  };

  const handleClearFile = () => {
    setSelectedFile(null);
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    uploadJsonMutation.mutate(selectedFile);
  };

  const handleSelectRecent = async (taskId: string) => {
    // For recent screenplays, we need to create a session from the task
    setCreatingSession(taskId);

    try {
      // Create a session from the task
      const response = await apiService.createSessionFromTask(taskId);
      if (response.error) {
        throw new Error(response.error);
      }

      // Show method selector for recent screenplays too
      setPendingSessionId(response.data.session_id);
      navigate({ to: '.', search: { method: 'select' } });
    } catch (error) {
      // Failed to create session from task
      console.error('Failed to create session from task:', error);
    } finally {
      setCreatingSession(null);
    }
  };

  const handleResumeSession = (sessionId: string) => {
    // Navigate directly to the session
    navigate({ to: '/voice-casting/$sessionId', params: { sessionId } });
  };

  // Session data queries removed - not needed for method selector

  const handleMethodSelectorClose = () => {
    navigate({ to: '.', search: {} }); // Clear search parameters
    setPendingSessionId(null);
    setSelectedFile(null);
  };

  return (
    <div className="container mx-auto p-6">
      <div className="mb-6 space-y-2">
        <h1 className="text-3xl font-bold">Voice Casting</h1>
        <p className="text-muted-foreground">
          Assign TTS voices to your screenplay characters
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Main Content - Left Column */}
        <div className="space-y-6 lg:col-span-2">
          {/* Upload New Screenplay */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Upload className="h-5 w-5" />
                Upload Screenplay JSON
              </CardTitle>
              <CardDescription>
                Upload a parsed screenplay JSON file to begin voice casting
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <FileUploadZone
                onFileSelect={handleFileSelect}
                accept={{
                  'application/json': ['.json'],
                }}
                maxSize={10 * 1024 * 1024} // 10MB for JSON files
                disabled={uploadJsonMutation.isPending}
                loading={uploadJsonMutation.isPending}
                selectedFile={selectedFile}
                onClearFile={handleClearFile}
                title="Drag & drop your screenplay JSON here"
                subtitle="or click to select a file"
                icon={<FileJson className="text-muted-foreground h-12 w-12" />}
                loadingText="Uploading..."
              />
              <Button
                onClick={handleUpload}
                disabled={!selectedFile || uploadJsonMutation.isPending}
                className="w-full"
                variant={selectedFile ? 'default' : 'secondary'}
              >
                {uploadJsonMutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Uploading...
                  </>
                ) : selectedFile ? (
                  'Start Voice Casting'
                ) : (
                  'Select a file to continue'
                )}
              </Button>

              {uploadJsonMutation.error && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    {uploadJsonMutation.error.message}
                  </AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>

          {/* Cast from Recently Parsed Screenplays */}
          <div className="space-y-4">
            <h2 className="text-xl font-semibold">
              Cast from Recently Parsed Screenplays
            </h2>
            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="text-muted-foreground h-6 w-6 animate-spin" />
              </div>
            ) : recentScreenplays.length === 0 ? (
              <Card>
                <CardContent className="text-muted-foreground py-8 text-center">
                  <p>No completed screenplay parsing tasks found.</p>
                  <p className="mt-2 text-sm">
                    Parse a screenplay PDF first to begin voice casting.
                  </p>
                </CardContent>
              </Card>
            ) : (
              <div className="grid gap-4">
                {recentScreenplays.map((screenplay) => (
                  <Card
                    key={screenplay.id}
                    className={`${interactiveCardVariants({
                      variant: 'action',
                    })} ${creatingSession === screenplay.id ? 'opacity-60' : ''}`}
                    onClick={() =>
                      !creatingSession && handleSelectRecent(screenplay.id)
                    }
                  >
                    <CardContent className="flex items-center justify-between p-4">
                      <div className="space-y-1">
                        <h3 className="font-medium">{screenplay.name}</h3>
                        <p className="text-muted-foreground text-sm">
                          {screenplay.characters} characters •{' '}
                          {screenplay.lines} lines • {screenplay.date}
                        </p>
                      </div>
                      {creatingSession === screenplay.id ? (
                        <Loader2 className="text-muted-foreground h-5 w-5 animate-spin" />
                      ) : (
                        <ChevronRight className="text-muted-foreground h-5 w-5" />
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column - Recent Castings */}
        <div>
          <Card className="p-4">
            <h3 className="mb-4 text-lg font-semibold">Recent Castings</h3>
            <VoiceCastingHistoryList
              sessions={recentSessions}
              onSelect={handleResumeSession}
            />
          </Card>
        </div>
      </div>

      {/* Casting Method Selector Modal */}
      {showMethodSelector && pendingSessionId && (
        <CastingMethodSelector
          sessionId={pendingSessionId}
          open={showMethodSelector}
          onOpenChange={handleMethodSelectorClose}
        />
      )}
    </div>
  );
}
