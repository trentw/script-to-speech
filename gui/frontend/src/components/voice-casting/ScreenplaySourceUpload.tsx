import { AlertCircle, CheckCircle2, FileText, Loader2 } from 'lucide-react';
import { useState } from 'react';

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
import { useUploadScreenplaySource } from '@/hooks/mutations/useUploadScreenplaySource';

interface ScreenplaySourceUploadProps {
  sessionId: string;
  onUploadComplete?: () => void;
}

export function ScreenplaySourceUpload({
  sessionId,
  onUploadComplete,
}: ScreenplaySourceUploadProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  const uploadMutation = useUploadScreenplaySource();

  const maxSizeBytes = 100 * 1024 * 1024; // 100MB

  const validateFile = (file: File): string | null => {
    // Check file type
    const extension = file.name.toLowerCase().split('.').pop();
    if (!extension || !['pdf', 'txt'].includes(extension)) {
      return 'Please select a PDF or TXT file';
    }

    // Check file size
    if (file.size > maxSizeBytes) {
      return 'File size must be less than 100MB';
    }

    return null;
  };

  const handleFileSelect = (file: File) => {
    const error = validateFile(file);
    if (error) {
      setValidationError(error);
      setSelectedFile(null);
      return;
    }

    setSelectedFile(file);
    setValidationError(null);
    uploadMutation.reset(); // Clear any previous errors
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    const error = validateFile(selectedFile);
    if (error) {
      setValidationError(error);
      return;
    }

    try {
      await uploadMutation.mutateAsync({
        sessionId,
        file: selectedFile,
      });

      onUploadComplete?.();
    } catch {
      // Error is handled by the mutation
    }
  };

  const clearFile = () => {
    setSelectedFile(null);
    setValidationError(null);
    uploadMutation.reset();
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileText className="h-5 w-5" />
          Upload Screenplay Source
        </CardTitle>
        <CardDescription>
          Upload the original screenplay file (PDF or TXT) to generate character
          notes. This helps the LLM understand character context and
          relationships.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* File Drop Zone using new component */}
        <FileUploadZone
          onFileSelect={handleFileSelect}
          accept={{
            'application/pdf': ['.pdf'],
            'text/plain': ['.txt'],
          }}
          maxSize={maxSizeBytes}
          disabled={uploadMutation.isPending}
          loading={false}
          selectedFile={selectedFile}
          onClearFile={clearFile}
          title="Drop your screenplay file here"
          subtitle="or click to browse"
          icon={<FileText className="text-muted-foreground h-12 w-12" />}
        />

        {/* Error Display */}
        {(validationError || uploadMutation.error) && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              {validationError || uploadMutation.error?.message}
            </AlertDescription>
          </Alert>
        )}

        {/* Success Display */}
        {uploadMutation.isSuccess && (
          <Alert>
            <CheckCircle2 className="h-4 w-4" />
            <AlertDescription>
              Screenplay source uploaded successfully! You can now generate the
              character notes prompt.
            </AlertDescription>
          </Alert>
        )}

        {/* Upload Button */}
        {selectedFile && !validationError && (
          <Button
            onClick={handleUpload}
            disabled={uploadMutation.isPending}
            className="w-full"
          >
            {uploadMutation.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Uploading...
              </>
            ) : (
              <>
                <Upload className="mr-2 h-4 w-4" />
                Upload Screenplay
              </>
            )}
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
