import { useQuery, useQueryClient } from '@tanstack/react-query';
import { createFileRoute, useNavigate } from '@tanstack/react-router';
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  Copy,
  Loader2,
} from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

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
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  GeneratePromptDisplay,
  PrivacyWarning,
  ScreenplaySourceUpload,
} from '@/components/voice-casting';
import { useGenerateCharacterNotesPrompt } from '@/hooks/mutations/useGenerateCharacterNotesPrompt';
import { useGenerateYaml } from '@/hooks/mutations/useGenerateYaml';
import { useParseYaml } from '@/hooks/mutations/useParseYaml';
import { apiService } from '@/services/api';
import { useVoiceCasting } from '@/stores/appStore';
import { yamlUtils } from '@/utils/yamlUtils';

export const Route = createFileRoute('/voice-casting/$sessionId/notes')({
  component: CharacterNotesGeneration,
  errorComponent: RouteError,
});

function CharacterNotesGeneration() {
  const { sessionId } = Route.useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [promptText, setPromptText] = useState('');
  const [yamlResponse, setYamlResponse] = useState('');
  const [showSuccess, setShowSuccess] = useState(false);
  const [copiedResponse, setCopiedResponse] = useState(false);
  const [showPrivacyWarning, setShowPrivacyWarning] = useState(false);
  const [privacyAccepted, setPrivacyAccepted] = useState(false);

  const { assignments, importAssignments, setYamlContent } = useVoiceCasting();

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

  const generatePromptMutation = useGenerateCharacterNotesPrompt();
  const generateYamlMutation = useGenerateYaml();
  const parseYamlMutation = useParseYaml();

  // Navigate back to main casting page
  const handleBack = () => {
    navigate({ to: '/voice-casting/$sessionId', params: { sessionId } });
  };

  // Step 1: Generate prompt
  const handleGeneratePrompt = useCallback(async () => {
    if (!session?.screenplay_json_path) return;

    // Show privacy warning first
    if (!privacyAccepted) {
      setShowPrivacyWarning(true);
      return;
    }

    await generatePromptInternal();
  }, [session?.screenplay_json_path, privacyAccepted, generatePromptInternal]);

  const generatePromptInternal = useCallback(async () => {
    // Generate YAML structure for character notes prompt
    // If we have assignments, use them, otherwise create YAML from screenplay character data
    let yamlContent = '';

    if (assignments.size > 0) {
      // Generate YAML from current assignments
      const yamlResult = await generateYamlMutation.mutateAsync({
        assignments,
      });
      yamlContent = yamlResult.data.yaml_content;
    } else {
      // Create YAML structure from screenplay character data
      yamlContent = await exportToYaml();
    }

    // Generate the character notes prompt using session_id
    const result = await generatePromptMutation.mutateAsync({
      sessionId: sessionId,
      yamlContent: yamlContent,
    });

    if (result) {
      setPromptText(result.prompt_content);
    }
  }, [
    assignments,
    generateYamlMutation,
    exportToYaml,
    generatePromptMutation,
    sessionId,
    setPromptText,
  ]);

  // Function to export current assignments or screenplay characters to YAML format
  const exportToYaml = useCallback(async (): Promise<string> => {
    // If we have assignments, use them with character info
    if (assignments && assignments.size > 0) {
      // Get character info for comments
      let characterInfo = [];
      if (session?.screenplay_json_path) {
        try {
          const extractResponse = await apiService.extractCharacters(
            session.screenplay_json_path
          );
          if (!extractResponse.error) {
            characterInfo = extractResponse.data!.characters;
          }
        } catch (err) {
          console.warn('Failed to fetch character info for comments:', err);
        }
      }

      return await yamlUtils.assignmentsToYaml(assignments, characterInfo);
    }

    // If no assignments, create minimal YAML from screenplay characters
    if (!session?.screenplay_json_path) {
      throw new Error(
        'No screenplay data available. Please ensure the session has character data.'
      );
    }

    return await yamlUtils.charactersToYaml(session.screenplay_json_path);
  }, [assignments, session?.screenplay_json_path]);

  const handlePrivacyAccept = async () => {
    setPrivacyAccepted(true);
    setShowPrivacyWarning(false);
    // Proceed with generation after accepting privacy
    await generatePromptInternal();
  };

  const handlePrivacyCancel = () => {
    setShowPrivacyWarning(false);
    // Navigate back
    navigate({ to: '/voice-casting/$sessionId', params: { sessionId } });
  };

  // Step 2: Parse YAML response
  const handleParseResponse = async () => {
    if (!yamlResponse.trim()) return;

    const result = await parseYamlMutation.mutateAsync({
      yamlContent: yamlResponse,
    });

    // Convert parsed assignments to Map format for the store
    const newAssignments = new Map();
    result.assignments.forEach((assignment) => {
      newAssignments.set(assignment.character, {
        provider: assignment.provider,
        sts_id: assignment.sts_id,
        voiceEntry: {
          sts_id: assignment.sts_id,
          casting_notes: assignment.casting_notes,
          role: assignment.role,
        },
      });
    });

    // Import the assignments to the store
    importAssignments(newAssignments);
    setYamlContent(yamlResponse);

    setShowSuccess(true);
    setTimeout(() => {
      navigate({ to: '/voice-casting/$sessionId', params: { sessionId } });
    }, 2000);
  };

  const handleCopyResponse = () => {
    navigator.clipboard.writeText(yamlResponse);
    setCopiedResponse(true);
    setTimeout(() => setCopiedResponse(false), 2000);
  };

  // Auto-generate prompt on mount if we have the necessary data
  useEffect(() => {
    if (
      session?.screenplay_json_path &&
      session?.screenplay_source_path &&
      assignments.size > 0 &&
      !promptText &&
      privacyAccepted
    ) {
      handleGeneratePrompt();
    }
  }, [
    session?.screenplay_json_path,
    session?.screenplay_source_path,
    assignments.size,
    privacyAccepted,
    handleGeneratePrompt,
    promptText,
  ]);

  if (sessionLoading) {
    return (
      <div className="container mx-auto max-w-4xl space-y-6 p-6">
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="text-muted-foreground h-6 w-6 animate-spin" />
        </div>
      </div>
    );
  }

  if (sessionError) {
    return (
      <div className="container mx-auto max-w-4xl space-y-6 p-6">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Failed to load session: {sessionError.message}
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
    <div className="container mx-auto max-w-4xl space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={handleBack}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold">Generate Character Notes</h1>
          <p className="text-muted-foreground">
            Use an LLM to add casting notes to your characters
          </p>
        </div>
      </div>

      {/* Privacy Warning Modal */}
      <PrivacyWarning
        isModal={showPrivacyWarning}
        onAccept={handlePrivacyAccept}
        onCancel={handlePrivacyCancel}
      />

      {/* Step 1: Screenplay Source */}
      <Card>
        <CardHeader>
          <CardTitle>Step 1: Screenplay Source</CardTitle>
          <CardDescription>
            Upload the original screenplay file (PDF or TXT) to generate
            character notes. This helps the LLM understand character context and
            relationships.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {session?.screenplay_source_path ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between rounded-lg border border-green-200 bg-green-50 p-4">
                <div className="flex items-center space-x-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-green-100">
                    <svg
                      className="h-4 w-4 text-green-600"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-green-900">
                      Screenplay uploaded successfully
                    </p>
                    <p className="text-sm text-green-700">
                      Source: {session.screenplay_source_path.split('/').pop()}
                    </p>
                  </div>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    // Reset the screenplay source path to show upload again
                    queryClient.setQueryData(
                      ['voice-casting-session', sessionId],
                      {
                        ...session,
                        screenplay_source_path: null,
                      }
                    );
                  }}
                >
                  Change File
                </Button>
              </div>
            </div>
          ) : (
            <ScreenplaySourceUpload
              sessionId={sessionId}
              onUploadComplete={() => {
                // Invalidate session query to refetch updated data
                queryClient.invalidateQueries({
                  queryKey: ['voice-casting-session', sessionId],
                });
              }}
            />
          )}
        </CardContent>
      </Card>

      {/* Step 2: Generate Prompt */}
      <Card>
        <CardHeader>
          <CardTitle>Step 2: Generate Prompt</CardTitle>
          <CardDescription>
            {session?.screenplay_source_path
              ? 'Copy this prompt and paste it into your preferred LLM'
              : 'Upload the screenplay source file first to generate the character notes prompt'}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {session?.screenplay_source_path ? (
            <GeneratePromptDisplay
              promptText={promptText}
              isGenerating={generatePromptMutation.isPending}
              onGenerate={handleGeneratePrompt}
              generateButtonText="Generate Prompt"
              filePrefix="character-notes-prompt"
              sessionId={sessionId}
            />
          ) : (
            <div className="text-muted-foreground py-8 text-center">
              <p>
                Please upload the screenplay source file above to generate the
                prompt.
              </p>
            </div>
          )}

          {generatePromptMutation.error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                {generatePromptMutation.error.message}
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Step 3: Paste Response */}
      <Card>
        <CardHeader>
          <CardTitle>Step 3: Paste LLM Response</CardTitle>
          <CardDescription>
            Paste the YAML response from the LLM here. The parser is flexible
            and accepts various YAML formats.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="yaml-response">YAML Response</Label>
            <div className="relative">
              <Textarea
                id="yaml-response"
                value={yamlResponse}
                onChange={(e) => setYamlResponse(e.target.value)}
                placeholder="Paste the YAML configuration here..."
                className="min-h-[200px] font-mono text-sm"
              />
              {yamlResponse && (
                <Button
                  size="sm"
                  variant="outline"
                  className="absolute top-2 right-2"
                  onClick={handleCopyResponse}
                >
                  {copiedResponse ? (
                    <>
                      <CheckCircle2 className="mr-2 h-4 w-4" />
                      Copied!
                    </>
                  ) : (
                    <>
                      <Copy className="mr-2 h-4 w-4" />
                      Copy
                    </>
                  )}
                </Button>
              )}
            </div>
          </div>

          <Button
            onClick={handleParseResponse}
            disabled={!yamlResponse.trim() || parseYamlMutation.isPending}
            className="w-full"
          >
            {parseYamlMutation.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Parsing...
              </>
            ) : (
              'Import Character Notes'
            )}
          </Button>

          {parseYamlMutation.error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                Failed to parse YAML: {parseYamlMutation.error.message}
              </AlertDescription>
            </Alert>
          )}

          {showSuccess && (
            <Alert>
              <CheckCircle2 className="h-4 w-4" />
              <AlertDescription>
                Character notes imported successfully! Redirecting...
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
