import { AlertCircle, FileText } from 'lucide-react';
import { useState } from 'react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Card } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { FileUploadZone } from '@/components/ui/file-upload-zone';
import { Label } from '@/components/ui/label';

interface ScreenplayUploadZoneProps {
  onUpload: (file: File, textOnly: boolean) => void;
  disabled?: boolean;
}

const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB in bytes

export function ScreenplayUploadZone({
  onUpload,
  disabled,
}: ScreenplayUploadZoneProps) {
  const [textOnly, setTextOnly] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const handleFileSelect = (file: File) => {
    setError(null);
    setSelectedFile(file);
    // Automatically trigger upload when file is selected
    onUpload(file, textOnly);
  };

  const handleClearFile = () => {
    setSelectedFile(null);
    setError(null);
  };

  return (
    <Card className="relative p-6">
      <FileUploadZone
        onFileSelect={handleFileSelect}
        accept={{
          'application/pdf': ['.pdf'],
          'text/plain': ['.txt'],
        }}
        maxSize={MAX_FILE_SIZE}
        disabled={disabled}
        loading={disabled}
        selectedFile={selectedFile}
        onClearFile={handleClearFile}
        title="Drag & drop a screenplay file here"
        subtitle="or click to select a file"
        icon={<FileText className="text-muted-foreground h-12 w-12" />}
        loadingText="Processing screenplay..."
      />

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
          className="text-sm leading-none font-medium peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
        >
          Extract text only (PDF files)
        </Label>
      </div>

      <p className="text-muted-foreground mt-2 text-xs">
        When enabled, only extracts text without parsing screenplay structure
      </p>
    </Card>
  );
}
