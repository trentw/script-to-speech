import { useMutation, useQuery } from '@tanstack/react-query';
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
import { CastingMethodSelector } from '@/components/voice-casting';
import { useRecentScreenplays } from '@/hooks/queries/useRecentScreenplays';
import { useScreenplayCharacters } from '@/hooks/queries/useScreenplayCharacters';
import { apiService } from '@/services/api';

export const Route = createFileRoute('/voice-casting/')({
  component: VoiceCastingUpload,
  errorComponent: RouteError,
});

function VoiceCastingUpload() {
  const navigate = useNavigate();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [creatingSession, setCreatingSession] = useState<string | null>(null);
  const [showMethodSelector, setShowMethodSelector] = useState(false);
  const [pendingSessionId, setPendingSessionId] = useState<string | null>(null);

  // Fetch recent completed screenplay parsing tasks
  const { data: screenplays, isLoading } = useRecentScreenplays(5);

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
      setShowMethodSelector(true);
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

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
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
      setShowMethodSelector(true);
    } catch (error) {
      // Failed to create session from task
      console.error('Failed to create session from task:', error);
    } finally {
      setCreatingSession(null);
    }
  };

  // Get session data for the method selector
  const { data: sessionData } = useQuery({
    queryKey: ['voice-casting-session', pendingSessionId],
    queryFn: async () => {
      if (!pendingSessionId) return null;
      const response =
        await apiService.getVoiceCastingSession(pendingSessionId);
      if (response.error) {
        throw new Error(response.error);
      }
      return response.data;
    },
    enabled: !!pendingSessionId && showMethodSelector,
  });

  // Get character count for the method selector
  const { data: charactersData } = useScreenplayCharacters(
    sessionData?.screenplay_json_path,
    { enabled: !!sessionData?.screenplay_json_path && showMethodSelector }
  );

  const handleMethodSelectorClose = () => {
    setShowMethodSelector(false);
    setPendingSessionId(null);
    setSelectedFile(null);
  };

  return (
    <div className="container mx-auto max-w-4xl space-y-6 p-6">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold">Voice Casting</h1>
        <p className="text-muted-foreground">
          Assign TTS voices to your screenplay characters
        </p>
      </div>

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
          <div className="border-border space-y-4 rounded-lg border-2 border-dashed p-8 text-center">
            <FileJson className="text-muted-foreground mx-auto h-12 w-12" />
            <div className="space-y-2">
              <label htmlFor="file-upload" className="cursor-pointer">
                <span className="text-primary hover:underline">
                  Choose a file
                </span>
                <input
                  id="file-upload"
                  type="file"
                  accept=".json"
                  onChange={handleFileSelect}
                  className="sr-only"
                />
              </label>
              <p className="text-muted-foreground text-sm">
                or drag and drop your screenplay JSON here
              </p>
            </div>
            {selectedFile && (
              <div className="bg-muted rounded-md p-3">
                <p className="text-sm font-medium">{selectedFile.name}</p>
                <p className="text-muted-foreground text-xs">
                  {(selectedFile.size / 1024).toFixed(1)} KB
                </p>
              </div>
            )}
          </div>
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

      {/* Recent Screenplays */}
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Recent Screenplays</h2>
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
                className={`hover:bg-accent cursor-pointer transition-colors ${
                  creatingSession === screenplay.id ? 'opacity-60' : ''
                }`}
                onClick={() =>
                  !creatingSession && handleSelectRecent(screenplay.id)
                }
              >
                <CardContent className="flex items-center justify-between p-4">
                  <div className="space-y-1">
                    <h3 className="font-medium">{screenplay.name}</h3>
                    <p className="text-muted-foreground text-sm">
                      {screenplay.characters} characters • {screenplay.lines}{' '}
                      lines • {screenplay.date}
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
