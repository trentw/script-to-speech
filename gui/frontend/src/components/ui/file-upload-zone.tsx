import { FileText, Loader2, Upload } from 'lucide-react';
import { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';

import { cn } from '@/lib/utils';

import { fileUploadZoneVariants } from './interactive.variants';

interface FileUploadZoneProps {
  onFileSelect: (file: File) => void;
  accept?: Record<string, string[]>;
  maxSize?: number;
  disabled?: boolean;
  loading?: boolean;
  selectedFile?: File | null;
  onClearFile?: () => void;
  className?: string;
  // UI customization
  title?: string;
  subtitle?: string;
  icon?: React.ReactNode;
  loadingText?: string;
}

export function FileUploadZone({
  onFileSelect,
  accept = {
    'application/pdf': ['.pdf'],
    'text/plain': ['.txt'],
  },
  maxSize = 100 * 1024 * 1024, // 100MB default
  disabled = false,
  loading = false,
  selectedFile,
  onClearFile,
  className,
  title = 'Drag & drop your file here',
  subtitle = 'or click to select a file',
  icon,
  loadingText = 'Processing...',
}: FileUploadZoneProps) {
  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      if (acceptedFiles.length > 0 && acceptedFiles[0]) {
        onFileSelect(acceptedFiles[0]);
      }
    },
    [onFileSelect]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept,
    maxFiles: 1,
    maxSize,
    disabled: disabled || loading,
  });

  // Determine current state for styling
  const getState = () => {
    if (disabled || loading) return 'disabled';
    if (selectedFile) return 'hasFile';
    if (isDragActive) return 'active';
    return 'idle';
  };

  // Format file size for display
  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  // Get accepted file extensions for display
  const getAcceptedFormats = () => {
    const extensions = Object.values(accept).flat();
    if (extensions.length === 0) return 'All files';
    if (extensions.length === 1) return extensions[0].toUpperCase();
    const lastExt = extensions.pop();
    return lastExt
      ? `${extensions.join(', ').toUpperCase()} or ${lastExt.toUpperCase()}`
      : extensions.join(', ').toUpperCase();
  };

  return (
    <div className={cn('relative', className)}>
      {/* Loading overlay */}
      {loading && (
        <div className="bg-background/80 absolute inset-0 z-10 flex items-center justify-center rounded-lg backdrop-blur-sm">
          <div className="flex flex-col items-center space-y-3">
            <Loader2 className="text-primary h-8 w-8 animate-spin" />
            <p className="text-sm font-medium">{loadingText}</p>
          </div>
        </div>
      )}

      {/* Main dropzone */}
      <div
        {...getRootProps()}
        className={cn(fileUploadZoneVariants({ state: getState() }))}
      >
        <input {...getInputProps()} />

        <div className="flex flex-col items-center space-y-4">
          {selectedFile ? (
            // File selected state
            <>
              <FileText className="text-primary h-12 w-12" />
              <div className="space-y-1 text-center">
                <p className="font-medium">{selectedFile.name}</p>
                <p className="text-muted-foreground text-sm">
                  {formatFileSize(selectedFile.size)}
                </p>
              </div>
              {onClearFile && (
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onClearFile();
                  }}
                  className="text-primary hover:text-primary/80 text-sm font-medium underline transition-colors"
                >
                  Choose different file
                </button>
              )}
            </>
          ) : isDragActive ? (
            // Drag active state
            <>
              <Upload className="text-primary h-12 w-12 animate-pulse" />
              <p className="text-lg font-medium">Drop the file here</p>
            </>
          ) : (
            // Default state
            <>
              {icon || <Upload className="text-muted-foreground h-12 w-12" />}
              <div className="space-y-1 text-center">
                <p className="text-lg font-medium">{title}</p>
                <p className="text-muted-foreground text-sm">{subtitle}</p>
              </div>
              <div className="text-muted-foreground space-y-1 text-center text-xs">
                <p>Accepted: {getAcceptedFormats()}</p>
                <p>Max size: {formatFileSize(maxSize)}</p>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
