import { useQuery } from '@tanstack/react-query';
import { createFileRoute, useNavigate } from '@tanstack/react-router';
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  Copy,
  Info,
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
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  GeneratePromptDisplay,
  PrivacyWarning,
} from '@/components/voice-casting';
import { useGenerateVoiceLibraryPrompt } from '@/hooks/mutations/useGenerateVoiceLibraryPrompt';
import { useParseYaml } from '@/hooks/mutations/useParseYaml';
import { useProviders } from '@/hooks/queries';
import { apiService } from '@/services/api';
import { useVoiceCasting } from '@/stores/appStore';
import { yamlUtils } from '@/utils/yamlUtils';

export const Route = createFileRoute('/voice-casting/$sessionId/library')({
  component: VoiceLibraryCasting,
  errorComponent: RouteError,
});

function VoiceLibraryCasting() {
  const { sessionId } = Route.useParams();
  const navigate = useNavigate();
  const [promptText, setPromptText] = useState('');
  const [yamlResponse, setYamlResponse] = useState('');
  const [showSuccess, setShowSuccess] = useState(false);
  const [copiedResponse, setCopiedResponse] = useState(false);
  const [showPrivacyWarning, setShowPrivacyWarning] = useState(false);
  const [privacyAccepted, setPrivacyAccepted] = useState(false);
  const [selectedProviders, setSelectedProviders] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

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

  const { data: providers } = useProviders();
  const generatePromptMutation = useGenerateVoiceLibraryPrompt();
  const parseYamlMutation = useParseYaml();

  // Initialize selected providers when providers load
  useEffect(() => {
    if (providers && selectedProviders.length === 0) {
      // Start with common providers selected
      const commonProviders = ['openai', 'elevenlabs'];
      const availableCommon = providers
        .filter((p) => commonProviders.includes(p.identifier))
        .map((p) => p.identifier);
      setSelectedProviders(
        availableCommon.length > 0
          ? availableCommon
          : [providers[0]?.identifier].filter(Boolean)
      );
    }
  }, [providers, selectedProviders.length]);

  // Navigate back to main casting page
  const handleBack = () => {
    navigate({ to: '/voice-casting/$sessionId', params: { sessionId } });
  };

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

  // Step 1: Generate prompt
  const handleGeneratePrompt = async () => {
    // Show privacy warning first
    if (!privacyAccepted) {
      setShowPrivacyWarning(true);
      return;
    }

    // Validate provider selection
    if (selectedProviders.length === 0) {
      setError('Please select at least one provider');
      return;
    }

    // Note: It's OK to have empty assignments - LLM workflows are designed to work with minimal data

    try {
      // Export current assignments or screenplay characters to YAML format
      const yamlContent = await exportToYaml();
      console.log('Generated YAML content:', yamlContent);

      // Generate the voice library prompt directly using the simplified approach
      const result = await generatePromptMutation.mutateAsync({
        yaml_content: yamlContent,
        providers: selectedProviders,
      });

      if (result.prompt_content) {
        setPromptText(result.prompt_content);
        setError(null);
      }
    } catch (err) {
      console.error('Error generating prompt:', err);

      // Extract error message properly
      let errorMessage = 'Failed to generate prompt';

      if (err instanceof Error) {
        errorMessage = err.message;
        console.error('Error details:', {
          name: err.name,
          message: err.message,
          stack: err.stack,
        });
      } else if (typeof err === 'object' && err !== null) {
        console.error('Full error object:', err);

        // Handle serialization errors better
        if ('message' in err && typeof err.message === 'string') {
          errorMessage = err.message;
        } else if ('detail' in err && typeof err.detail === 'string') {
          errorMessage = err.detail;
        } else if ('error' in err && typeof err.error === 'string') {
          errorMessage = err.error;
        } else {
          // Try to extract meaningful error information
          try {
            errorMessage = JSON.stringify(err, null, 2);
          } catch (jsonErr) {
            errorMessage =
              'Unknown error occurred (cannot serialize error object)';
            console.error('Error serializing error object:', jsonErr);
          }
        }
      } else if (typeof err === 'string') {
        errorMessage = err;
      } else {
        errorMessage = String(err);
      }

      console.error('Final error message:', errorMessage);
      setError(errorMessage);
    }
  };

  const handlePrivacyAccept = async () => {
    setPrivacyAccepted(true);
    setShowPrivacyWarning(false);
    // Proceed with generation after accepting - but skip privacy check since we just accepted
    await generatePromptInternal();
  };

  const generatePromptInternal = useCallback(async () => {
    // Validate provider selection
    if (selectedProviders.length === 0) {
      setError('Please select at least one provider');
      return;
    }

    try {
      // Export current assignments or screenplay characters to YAML format
      const yamlContent = await exportToYaml();
      console.log('Generated YAML content:', yamlContent);

      // Generate the voice library prompt directly using the simplified approach
      const result = await generatePromptMutation.mutateAsync({
        yaml_content: yamlContent,
        providers: selectedProviders,
      });

      if (result.prompt_content) {
        setPromptText(result.prompt_content);
        setError(null);
      }
    } catch (err) {
      console.error('Error generating prompt:', err);

      // Extract error message properly
      let errorMessage = 'Failed to generate prompt';

      if (err instanceof Error) {
        errorMessage = err.message;
        console.error('Error details:', {
          name: err.name,
          message: err.message,
          stack: err.stack,
        });
      } else if (typeof err === 'object' && err !== null) {
        console.error('Full error object:', err);

        // Handle serialization errors better
        if ('message' in err && typeof err.message === 'string') {
          errorMessage = err.message;
        } else if ('detail' in err && typeof err.detail === 'string') {
          errorMessage = err.detail;
        } else if ('error' in err && typeof err.error === 'string') {
          errorMessage = err.error;
        } else {
          // Try to extract meaningful error information
          try {
            errorMessage = JSON.stringify(err, null, 2);
          } catch (jsonErr) {
            errorMessage =
              'Unknown error occurred (cannot serialize error object)';
            console.error('Error serializing error object:', jsonErr);
          }
        }
      } else if (typeof err === 'string') {
        errorMessage = err;
      } else {
        errorMessage = String(err);
      }

      console.error('Final error message:', errorMessage);
      setError(errorMessage);
    }
  }, [selectedProviders, exportToYaml, generatePromptMutation, setError]);

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

  const toggleProvider = (providerId: string) => {
    setSelectedProviders((prev) => {
      const newSelection = prev.includes(providerId)
        ? prev.filter((id) => id !== providerId)
        : [...prev, providerId];
      console.log(
        `Toggling provider ${providerId}: ${prev} -> ${newSelection}`
      );
      return newSelection;
    });
  };

  // Auto-generate prompt on mount if we have the necessary data
  useEffect(() => {
    if (
      session?.screenplay_json_path &&
      !promptText &&
      providers &&
      privacyAccepted
    ) {
      generatePromptInternal();
    }
  }, [
    session?.screenplay_json_path,
    providers,
    privacyAccepted,
    generatePromptInternal,
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
            Failed to load session:{' '}
            {sessionError instanceof Error
              ? sessionError.message
              : String(sessionError)}
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
          <h1 className="text-2xl font-bold">Voice Library Casting</h1>
          <p className="text-muted-foreground">
            Use an LLM to suggest voices from your configured TTS providers
          </p>
        </div>
      </div>

      {/* Privacy Warning Modal */}
      <PrivacyWarning
        isModal={showPrivacyWarning}
        onAccept={handlePrivacyAccept}
        onCancel={handlePrivacyCancel}
      />

      <Alert>
        <Info className="h-4 w-4" />
        <AlertDescription>
          This workflow helps you leverage an LLM to suggest appropriate voices
          from your available TTS providers based on character descriptions and
          casting notes.
        </AlertDescription>
      </Alert>

      {/* Error Display */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Provider Selection */}
      {providers && providers.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Select Providers</CardTitle>
            <CardDescription>
              Choose which TTS providers to include in the voice library prompt
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() =>
                    setSelectedProviders(providers.map((p) => p.identifier))
                  }
                  disabled={selectedProviders.length === providers.length}
                >
                  Select All
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setSelectedProviders([])}
                  disabled={selectedProviders.length === 0}
                >
                  Clear All
                </Button>
              </div>
              <div className="space-y-2">
                {providers.map((provider, index) => (
                  <div
                    key={`provider-${provider.identifier}-${index}`}
                    className="flex items-center space-x-2"
                  >
                    <Checkbox
                      id={`provider-checkbox-${provider.identifier}`}
                      checked={selectedProviders.includes(provider.identifier)}
                      onCheckedChange={(checked) => {
                        console.log(
                          `Checkbox change for ${provider.identifier}: ${checked}`
                        );
                        if (checked === 'indeterminate') return;
                        toggleProvider(provider.identifier);
                      }}
                    />
                    <Label
                      htmlFor={`provider-checkbox-${provider.identifier}`}
                      className="text-sm leading-none font-medium peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                    >
                      {provider.name || provider.identifier}
                    </Label>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 1: Generate Prompt */}
      <Card>
        <CardHeader>
          <CardTitle>Step 1: Generate Prompt</CardTitle>
          <CardDescription>
            Copy this prompt and paste it into your preferred LLM
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <GeneratePromptDisplay
            promptText={promptText}
            isGenerating={generatePromptMutation.isPending}
            onGenerate={handleGeneratePrompt}
            generateButtonText="Generate Prompt"
            filePrefix="voice-library-prompt"
            sessionId={sessionId}
          />
        </CardContent>
      </Card>

      {/* Step 2: Paste Response */}
      <Card>
        <CardHeader>
          <CardTitle>Step 2: Paste LLM Response</CardTitle>
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
              'Import Voice Assignments'
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
                Voice assignments imported successfully! Redirecting...
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
