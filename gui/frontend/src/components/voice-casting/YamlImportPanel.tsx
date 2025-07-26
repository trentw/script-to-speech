import { AlertCircle, ArrowLeft, Check, FileText, Loader2,Upload } from 'lucide-react';
import { useEffect,useRef, useState } from 'react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { useDebounce } from '@/hooks/useDebounce';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { useParseYaml } from '@/hooks/mutations/useParseYaml';
import { useValidateYaml } from '@/hooks/mutations/useValidateYaml';
import { useVoiceCasting, type VoiceAssignment } from '@/stores/appStore';

interface YamlImportPanelProps {
  onBack: () => void;
  onImportSuccess: () => void;
}

export function YamlImportPanel({ onBack, onImportSuccess }: YamlImportPanelProps) {
  const [yamlInput, setYamlInput] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { importAssignments, screenplayJsonPath } = useVoiceCasting();
  
  const parseYamlMutation = useParseYaml();
  const validateYamlMutation = useValidateYaml();
  
  // Debounce the YAML input to avoid excessive API calls
  const debouncedYamlInput = useDebounce(yamlInput, 500);

  // Parse and validate YAML when debounced content changes
  useEffect(() => {
    if (debouncedYamlInput.trim().length > 0) {
      // Parse the YAML
      parseYamlMutation.mutate({ yamlContent: debouncedYamlInput });
      
      // Validate if we have a screenplay JSON path
      if (screenplayJsonPath) {
        validateYamlMutation.mutate({ 
          yamlContent: debouncedYamlInput,
          screenplayJsonPath 
        });
      }
    }
  }, [debouncedYamlInput, screenplayJsonPath]);

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      const text = await file.text();
      setYamlInput(text);
    }
  };

  const handleImport = () => {
    if (parseYamlMutation.data && parseYamlMutation.data.assignments) {
      // Convert array to Map for the store
      const assignmentsMap = new Map<string, VoiceAssignment>();
      parseYamlMutation.data.assignments.forEach(assignment => {
        assignmentsMap.set(assignment.character, {
          voiceId: assignment.sts_id,
          provider: assignment.provider,
          castingNotes: assignment.casting_notes,
          role: assignment.role,
        });
      });
      importAssignments(assignmentsMap);
      onImportSuccess();
    }
  };

  const isLoading = parseYamlMutation.isPending || validateYamlMutation.isPending;
  const parseError = parseYamlMutation.error;
  const validationResult = validateYamlMutation.data;
  const hasErrors = validationResult && !validationResult.is_valid;
  const canImport = yamlInput.trim().length > 0 && !isLoading && !parseError && !hasErrors;

  return (
    <div className="container max-w-4xl mx-auto p-6 space-y-6">
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
              <div className="flex flex-col items-center justify-center border-2 border-dashed rounded-lg p-8 space-y-4">
                <FileText className="h-12 w-12 text-muted-foreground" />
                <div className="text-center space-y-2">
                  <p className="text-sm text-muted-foreground">
                    {selectedFile ? selectedFile.name : 'No file selected'}
                  </p>
                  <Button
                    variant="outline"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <Upload className="h-4 w-4 mr-2" />
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
                <span className="text-sm text-muted-foreground">Validating YAML...</span>
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
                      {validationResult.message || 'YAML configuration is valid'}
                    </AlertDescription>
                  </Alert>
                ) : (
                  <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>
                      <div className="space-y-1">
                        <p className="font-medium">{validationResult.message}</p>
                        {validationResult.missing_speakers.length > 0 && (
                          <div className="mt-2">
                            <p className="text-sm">Missing speakers:</p>
                            <ul className="list-disc list-inside text-sm">
                              {validationResult.missing_speakers.map((speaker, idx) => (
                                <li key={idx}>{speaker}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                        {validationResult.extra_speakers.length > 0 && (
                          <div className="mt-2">
                            <p className="text-sm">Extra speakers not in screenplay:</p>
                            <ul className="list-disc list-inside text-sm">
                              {validationResult.extra_speakers.map((speaker, idx) => (
                                <li key={idx}>{speaker}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                        {validationResult.duplicate_speakers.length > 0 && (
                          <div className="mt-2">
                            <p className="text-sm">Duplicate speakers:</p>
                            <ul className="list-disc list-inside text-sm">
                              {validationResult.duplicate_speakers.map((speaker, idx) => (
                                <li key={idx}>{speaker}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                        {Object.keys(validationResult.invalid_configs).length > 0 && (
                          <div className="mt-2">
                            <p className="text-sm">Invalid configurations:</p>
                            <ul className="list-disc list-inside text-sm">
                              {Object.entries(validationResult.invalid_configs).map(([speaker, error], idx) => (
                                <li key={idx}>{speaker}: {error}</li>
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
                <div className="rounded-md border p-3 space-y-2 max-h-64 overflow-y-auto">
                  {parseYamlMutation.data.assignments.map((assignment) => (
                    <div key={assignment.character} className="border-b last:border-0 pb-2 last:pb-0">
                      <div className="flex justify-between text-sm">
                        <span className="font-medium">{assignment.character}:</span>
                        <span className="text-muted-foreground">
                          {assignment.provider} - {assignment.sts_id}
                        </span>
                      </div>
                      {(assignment.role || assignment.casting_notes) && (
                        <div className="mt-1 space-y-1 pl-4">
                          {assignment.role && (
                            <p className="text-xs text-muted-foreground">
                              <span className="font-medium">Role:</span> {assignment.role}
                            </p>
                          )}
                          {assignment.casting_notes && (
                            <p className="text-xs text-muted-foreground">
                              <span className="font-medium">Notes:</span> {assignment.casting_notes}
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
        <Button 
          onClick={handleImport} 
          disabled={!canImport}
        >
          Import Configuration
        </Button>
      </div>
    </div>
  );
}