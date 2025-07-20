import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileText, AlertCircle, Loader2 } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { cn } from '@/lib/utils';

interface ScreenplayUploadZoneProps {
  onUpload: (file: File, textOnly: boolean) => void;
  disabled?: boolean;
}

const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB in bytes

export function ScreenplayUploadZone({ onUpload, disabled }: ScreenplayUploadZoneProps) {
  const [textOnly, setTextOnly] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onDrop = useCallback((acceptedFiles: File[], rejectedFiles: any[]) => {
    setError(null);
    
    if (rejectedFiles.length > 0) {
      const fileTooBig = rejectedFiles.some((rejected: any) => 
        rejected.errors?.some((error: any) => error.code === 'file-too-large')
      );
      if (fileTooBig) {
        setError(`File too large. Maximum size allowed is ${MAX_FILE_SIZE / (1024 * 1024)}MB.`);
      } else {
        setError('Please upload only PDF or TXT files');
      }
      return;
    }
    
    if (acceptedFiles.length > 0) {
      const file = acceptedFiles[0];
      if (file.size > MAX_FILE_SIZE) {
        setError(`File too large. Maximum size allowed is ${MAX_FILE_SIZE / (1024 * 1024)}MB.`);
        return;
      }
      onUpload(file, textOnly);
    }
  }, [onUpload, textOnly]);

  const { getRootProps, getInputProps, isDragActive, acceptedFiles } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'text/plain': ['.txt']
    },
    maxFiles: 1,
    maxSize: MAX_FILE_SIZE,
    disabled
  });

  return (
    <Card className="p-6 relative">
      {disabled && (
        <div className="absolute inset-0 bg-background/80 backdrop-blur-sm z-10 flex items-center justify-center rounded-lg">
          <div className="flex flex-col items-center space-y-3">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <p className="text-sm font-medium">Processing screenplay...</p>
          </div>
        </div>
      )}
      <div
        {...getRootProps()}
        className={cn(
          "border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors relative",
          isDragActive ? "border-primary bg-primary/5" : "border-muted-foreground/25",
          disabled && "opacity-50 cursor-not-allowed"
        )}
      >
        <input {...getInputProps()} />
        
        <div className="flex flex-col items-center space-y-4">
          {isDragActive ? (
            <>
              <Upload className="h-12 w-12 text-primary animate-pulse" />
              <p className="text-lg font-medium">Drop the screenplay here</p>
            </>
          ) : (
            <>
              <FileText className="h-12 w-12 text-muted-foreground" />
              <div>
                <p className="text-lg font-medium">Drag & drop a screenplay file here</p>
                <p className="text-sm text-muted-foreground mt-1">or click to select a file</p>
              </div>
              <p className="text-xs text-muted-foreground">Supports PDF and TXT files (max {MAX_FILE_SIZE / (1024 * 1024)}MB)</p>
            </>
          )}
        </div>
      </div>

      {acceptedFiles.length > 0 && (
        <div className="mt-4 p-3 bg-muted rounded-md">
          <p className="text-sm font-medium">Selected file:</p>
          <p className="text-sm text-muted-foreground">{acceptedFiles[0].name}</p>
        </div>
      )}

      {error && (
        <Alert variant="destructive" className="mt-4">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="mt-4 flex items-center space-x-2">
        <Checkbox
          id="text-only"
          checked={textOnly}
          onCheckedChange={(checked) => setTextOnly(checked as boolean)}
          disabled={disabled}
        />
        <Label
          htmlFor="text-only"
          className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
        >
          Extract text only (PDF files)
        </Label>
      </div>

      <p className="text-xs text-muted-foreground mt-2">
        When enabled, only extracts text without parsing screenplay structure
      </p>
    </Card>
  );
}