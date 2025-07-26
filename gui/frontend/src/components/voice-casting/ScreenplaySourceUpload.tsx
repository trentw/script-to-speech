import { AlertCircle, CheckCircle2, FileText, Loader2, Upload } from 'lucide-react';
import { useRef, useState } from 'react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useUploadScreenplaySource } from '@/hooks/mutations/useUploadScreenplaySource';

interface ScreenplaySourceUploadProps {
  sessionId: string;
  onUploadComplete?: () => void;
}

export function ScreenplaySourceUpload({ sessionId, onUploadComplete }: ScreenplaySourceUploadProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const uploadMutation = useUploadScreenplaySource();

  const acceptedTypes = '.pdf,.txt';
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

  const handleFileInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      handleFileSelect(file);
    }
  };

  const handleDragOver = (event: React.DragEvent) => {
    event.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = (event: React.DragEvent) => {
    event.preventDefault();
    setDragOver(false);
  };

  const handleDrop = (event: React.DragEvent) => {
    event.preventDefault();
    setDragOver(false);
    
    const file = event.dataTransfer.files[0];
    if (file) {
      handleFileSelect(file);
    }
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

  const handleBrowseClick = () => {
    fileInputRef.current?.click();
  };

  const clearFile = () => {
    setSelectedFile(null);
    setValidationError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
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
          Upload the original screenplay file (PDF or TXT) to generate character notes. 
          This helps the LLM understand character context and relationships.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* File Drop Zone */}
        <div
          className={`
            border-2 border-dashed rounded-lg p-8 text-center transition-colors
            ${dragOver ? 'border-primary bg-primary/5' : 'border-muted-foreground/25'}
            ${selectedFile ? 'bg-muted/50' : 'hover:border-primary/50 hover:bg-primary/5'}
          `}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept={acceptedTypes}
            onChange={handleFileInputChange}
            className="hidden"
          />
          
          {selectedFile ? (
            <div className="space-y-2">
              <FileText className="h-12 w-12 mx-auto text-primary" />
              <div>
                <p className="font-medium">{selectedFile.name}</p>
                <p className="text-sm text-muted-foreground">
                  {(selectedFile.size / (1024 * 1024)).toFixed(1)} MB
                </p>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={clearFile}
                disabled={uploadMutation.isPending}
              >
                Choose Different File
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              <Upload className="h-12 w-12 mx-auto text-muted-foreground" />
              <div>
                <p className="text-lg font-medium">
                  Drop your screenplay file here
                </p>
                <p className="text-sm text-muted-foreground">
                  or click to browse
                </p>
              </div>
              <Button
                type="button"
                variant="outline"
                onClick={handleBrowseClick}
              >
                Browse Files
              </Button>
            </div>
          )}
        </div>

        {/* File Requirements */}
        <div className="text-sm text-muted-foreground space-y-1">
          <p><strong>Accepted formats:</strong> PDF, TXT</p>
          <p><strong>Maximum size:</strong> 100MB</p>
        </div>

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
              Screenplay source uploaded successfully! You can now generate the character notes prompt.
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
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Uploading...
              </>
            ) : (
              <>
                <Upload className="h-4 w-4 mr-2" />
                Upload Screenplay
              </>
            )}
          </Button>
        )}
      </CardContent>
    </Card>
  );
}