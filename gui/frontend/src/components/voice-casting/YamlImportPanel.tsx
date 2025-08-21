import {
  AlertCircle,
  ArrowLeft,
  Check,
  FileText,
  Loader2,
  Upload,
} from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { useParseYaml } from '@/hooks/mutations/useParseYaml';
import { useUpdateSessionYaml } from '@/hooks/mutations/useUpdateSessionYaml';
import { useValidateYaml } from '@/hooks/mutations/useValidateYaml';
import { useSessionAssignments } from '@/hooks/queries/useSessionAssignments';
import { useDebounce } from '@/hooks/useDebounce';

interface YamlImportPanelProps {
  sessionId: string;
  onBack: () => void;
  onImportSuccess: () => void;
}

export function YamlImportPanel({
  sessionId,
  onBack,
  onImportSuccess,
}: YamlImportPanelProps) {
  const [yamlInput, setYamlInput] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [importWarnings, setImportWarnings] = useState<string[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Fetch session data using React Query
  const {
    data: sessionData,
    isLoading: sessionLoading,
    error: sessionError,
  } = useSessionAssignments(sessionId);

  // Mutations
  const parseYamlMutation = useParseYaml();
  const validateYamlMutation = useValidateYaml();
  const updateSessionYamlMutation = useUpdateSessionYaml();

  // Debounce the YAML input to avoid excessive API calls
  const debouncedYamlInput = useDebounce(yamlInput, 500);

  // Parse and validate YAML when debounced content changes
  useEffect(() => {
    if (debouncedYamlInput.trim().length > 0) {
      // Parse the YAML
      parseYamlMutation.mutate({ yamlContent: debouncedYamlInput });

      // Validate if we have a screenplay JSON path from session data
      const screenplayJsonPath = sessionData?.screenplayJsonPath;

      if (screenplayJsonPath) {
        validateYamlMutation.mutate({
          yamlContent: debouncedYamlInput,
          screenplayJsonPath,
        });
      }
    }
  }, [debouncedYamlInput, sessionData?.screenplayJsonPath]); // Depend on debounced input and screenplay path

  const handleFileSelect = async (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      const text = await file.text();
      setYamlInput(text);
    }
  };

  const handleImport = async () => {
    if (yamlInput.trim().length > 0 && sessionData?.yamlVersionId) {
      try {
        await updateSessionYamlMutation.mutateAsync({
          sessionId,
          yamlContent: yamlInput,
          versionId: sessionData.yamlVersionId,
        });
        onImportSuccess();
      } catch (error) {
        // Handle version conflict (409 error)
        if (error?.response?.status === 409) {
          setImportWarnings([
            'The session has been modified by another process.',
            'Please refresh and try again.',
          ]);
        } else {
          console.error('Failed to import YAML:', error);
        }
        // Error handling is also displayed via mutation error state
      }
    }
  };

  const isLoading =
    parseYamlMutation.isPending ||
    validateYamlMutation.isPending ||
    updateSessionYamlMutation.isPending;
  const parseError = parseYamlMutation.error;
  const validationResult = validateYamlMutation.data;
  const hasErrors = validationResult && !validationResult.is_valid;
  const canImport =
    yamlInput.trim().length > 0 &&
    !isLoading &&
    !parseError &&
    !hasErrors &&
    !!sessionData?.yamlVersionId;

  // Handle session loading/error states
  if (sessionLoading) {
    return (
      <div className="container mx-auto max-w-6xl space-y-6 p-6">
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="text-muted-foreground h-6 w-6 animate-spin" />
        </div>
      </div>
    );
  }

  if (sessionError) {
    return (
      <div className="container mx-auto max-w-6xl space-y-6 p-6">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Failed to load session data: {sessionError.message}
          </AlertDescription>
        </Alert>
        <Button variant="outline" onClick={onBack}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>
      </div>
    );
  }

  return (
    <div className="container mx-auto max-w-6xl space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={onBack}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold">Import Voice Configuration</h1>
          <p className="text-muted-foreground">
            Import an existing YAML configuration to assign voices
          </p>
        </div>
      </div>

      {/* Import Warnings */}
      {importWarnings.length > 0 && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            <div className="space-y-1">
              {importWarnings.map((warning, idx) => (
                <p key={idx}>{warning}</p>
              ))}
            </div>
          </AlertDescription>
        </Alert>
      )}

      {/* Mutation Error */}
      {updateSessionYamlMutation.error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Failed to import configuration:{' '}
            {updateSessionYamlMutation.error.message}
          </AlertDescription>
        </Alert>
      )}

      <Tabs defaultValue="paste" className="space-y-4">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="paste">Paste YAML</TabsTrigger>
          <TabsTrigger value="upload">Upload File</TabsTrigger>
        </TabsList>

        <TabsContent value="paste" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Paste YAML Configuration</CardTitle>
              <CardDescription>
                Paste your voice configuration YAML below
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="yaml-input">YAML Content</Label>
                <Textarea
                  id="yaml-input"
                  placeholder="# Paste your YAML configuration here..."
                  className="min-h-[400px] font-mono text-sm"
                  value={yamlInput}
                  onChange={(e) => setYamlInput(e.target.value)}
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="upload" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Upload YAML File</CardTitle>
              <CardDescription>
                Select a YAML configuration file from your computer
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-col items-center justify-center space-y-4 rounded-lg border-2 border-dashed p-8">
                <FileText className="text-muted-foreground h-12 w-12" />
                <div className="space-y-2 text-center">
                  <p className="text-muted-foreground text-sm">
                    {selectedFile ? selectedFile.name : 'No file selected'}
                  </p>
                  <Button
                    variant="outline"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <Upload className="mr-2 h-4 w-4" />
                    Choose File
                  </Button>
                </div>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".yaml,.yml"
                  onChange={handleFileSelect}
                  className="hidden"
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Validation Results */}
      {yamlInput && (
        <Card>
          <CardHeader>
            <CardTitle>Validation Results</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {isLoading ? (
              <div className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span className="text-muted-foreground text-sm">
                  Validating YAML...
                </span>
              </div>
            ) : parseError ? (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  Failed to parse YAML: {parseError.message}
                </AlertDescription>
              </Alert>
            ) : validationResult ? (
              <div className="space-y-2">
                {validationResult.is_valid ? (
                  <Alert className="border-green-500">
                    <Check className="h-4 w-4 text-green-500" />
                    <AlertDescription className="text-green-700">
                      {validationResult.message ||
                        'YAML configuration is valid'}
                    </AlertDescription>
                  </Alert>
                ) : (
                  <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>
                      <div className="space-y-1">
                        <p className="font-medium">
                          {validationResult.message}
                        </p>
                        {validationResult.missing_speakers.length > 0 && (
                          <div className="mt-2">
                            <p className="text-sm">Missing speakers:</p>
                            <ul className="list-inside list-disc text-sm">
                              {validationResult.missing_speakers.map(
                                (speaker, idx) => (
                                  <li key={idx}>{speaker}</li>
                                )
                              )}
                            </ul>
                          </div>
                        )}
                        {validationResult.extra_speakers.length > 0 && (
                          <div className="mt-2">
                            <p className="text-sm">
                              Extra speakers not in screenplay:
                            </p>
                            <ul className="list-inside list-disc text-sm">
                              {validationResult.extra_speakers.map(
                                (speaker, idx) => (
                                  <li key={idx}>{speaker}</li>
                                )
                              )}
                            </ul>
                          </div>
                        )}
                        {validationResult.duplicate_speakers.length > 0 && (
                          <div className="mt-2">
                            <p className="text-sm">Duplicate speakers:</p>
                            <ul className="list-inside list-disc text-sm">
                              {validationResult.duplicate_speakers.map(
                                (speaker, idx) => (
                                  <li key={idx}>{speaker}</li>
                                )
                              )}
                            </ul>
                          </div>
                        )}
                        {Object.keys(validationResult.invalid_configs).length >
                          0 && (
                          <div className="mt-2">
                            <p className="text-sm">Invalid configurations:</p>
                            <ul className="list-inside list-disc text-sm">
                              {Object.entries(
                                validationResult.invalid_configs
                              ).map(([speaker, error], idx) => (
                                <li key={idx}>
                                  {speaker}: {error}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    </AlertDescription>
                  </Alert>
                )}
              </div>
            ) : null}

            {/* Parsed Data Preview */}
            {parseYamlMutation.data && parseYamlMutation.data.assignments && (
              <div className="space-y-2">
                <h4 className="text-sm font-medium">Parsed Assignments:</h4>
                <div className="max-h-64 space-y-2 overflow-y-auto rounded-md border p-3">
                  {parseYamlMutation.data.assignments.map((assignment) => (
                    <div
                      key={assignment.character}
                      className="border-b pb-2 last:border-0 last:pb-0"
                    >
                      <div className="flex justify-between text-sm">
                        <span className="font-medium">
                          {assignment.character}:
                        </span>
                        <span className="text-muted-foreground">
                          {assignment.provider} - {assignment.sts_id}
                        </span>
                      </div>
                      {(assignment.role || assignment.casting_notes) && (
                        <div className="mt-1 space-y-1 pl-4">
                          {assignment.role && (
                            <p className="text-muted-foreground text-xs">
                              <span className="font-medium">Role:</span>{' '}
                              {assignment.role}
                            </p>
                          )}
                          {assignment.casting_notes && (
                            <p className="text-muted-foreground text-xs">
                              <span className="font-medium">Notes:</span>{' '}
                              {assignment.casting_notes}
                            </p>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Actions */}
      <div className="flex items-center justify-between">
        <Button variant="outline" onClick={onBack}>
          Cancel
        </Button>
        <Button onClick={handleImport} disabled={!canImport}>
          Import Configuration
        </Button>
      </div>
    </div>
  );
}
