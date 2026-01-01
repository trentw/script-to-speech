import { Link, useNavigate } from '@tanstack/react-router';
import { ArrowLeft, Loader2, RefreshCw } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { appButtonVariants } from '@/components/ui/button-variants';
import { useDetectHeaders, useReparseScreenplay } from '@/hooks/mutations';
import type { DetectedPattern, DetectionResult, ReparseRequest } from '@/types';

import { DetectionSection } from './DetectionSection';
import { RemovalSection } from './RemovalSection';

interface ConfigureParsingViewProps {
  inputPath: string;
  screenplayName: string;
  pdfPath: string;
}

/**
 * Full-page view for configuring screenplay parsing options.
 * Allows detection of headers/footers and configuration of removal options.
 */
export function ConfigureParsingView({
  inputPath,
  screenplayName,
  pdfPath,
}: ConfigureParsingViewProps) {
  const navigate = useNavigate();
  const detectMutation = useDetectHeaders();
  const reparseMutation = useReparseScreenplay();

  // Detection state
  const [detectedPatterns, setDetectedPatterns] = useState<DetectedPattern[]>(
    []
  );
  const [hasDetected, setHasDetected] = useState(false);

  // Selection state - patterns selected for removal
  const [selectedPatterns, setSelectedPatterns] = useState<Set<string>>(
    new Set()
  );

  // Manual entries - user-added patterns
  const [manualEntries, setManualEntries] = useState<string[]>([]);

  // Removal settings
  const [removeLines, setRemoveLines] = useState(2);
  const [globalReplace, setGlobalReplace] = useState(false);

  // Reset all detection state when project changes
  useEffect(() => {
    setDetectedPatterns([]);
    setHasDetected(false);
    setSelectedPatterns(new Set());
    setManualEntries([]);
    setRemoveLines(2);
    setGlobalReplace(false);
  }, [inputPath]);

  const handleDetectionComplete = useCallback((result: DetectionResult) => {
    setDetectedPatterns(result.patterns);
    setHasDetected(true);

    // Pre-select patterns based on thresholds:
    // - >= 40% (isAutoApplied): checked by default
    // - 20-40% (isSuggestion): unchecked by default
    // - Blacklisted: unchecked by default
    // For patterns with variations, select the variations; otherwise select root text
    const autoSelected = new Set<string>();
    result.patterns
      .filter((p) => p.isAutoApplied && !p.isBlacklisted)
      .forEach((p) => {
        if (p.variations.length > 0) {
          // Select all variations for this pattern
          p.variations.forEach((v) => autoSelected.add(v));
        } else {
          // No variations - select the root pattern text
          autoSelected.add(p.text);
        }
      });
    setSelectedPatterns(autoSelected);
  }, []);

  const handleDetect = useCallback(
    async (
      params: Parameters<typeof detectMutation.mutateAsync>[0]
    ): Promise<DetectionResult> => {
      return detectMutation.mutateAsync(params);
    },
    [detectMutation]
  );

  const handleReparse = async () => {
    // Combine selected patterns with manual entries
    const stringsToRemove = [
      ...Array.from(selectedPatterns),
      ...manualEntries.filter((e) => e.trim()),
    ];

    const request: ReparseRequest = {
      inputPath,
      screenplayName,
      stringsToRemove,
      removeLines: globalReplace ? 0 : removeLines,
      globalReplace,
    };

    try {
      await reparseMutation.mutateAsync(request);
      // Navigate back to screenplay page on success
      navigate({ to: '/project/screenplay' });
    } catch (error) {
      console.error('Reparse failed:', error);
    }
  };

  const totalPatternsToRemove =
    selectedPatterns.size + manualEntries.filter((e) => e.trim()).length;

  return (
    <div className="container mx-auto max-w-3xl px-6 py-8">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-4">
          <Link
            to="/project/screenplay"
            className={appButtonVariants({
              variant: 'secondary',
              size: 'icon',
            })}
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">
              Configure Parsing
            </h1>
            <p className="text-muted-foreground mt-1">{screenplayName}</p>
          </div>
        </div>
      </div>

      <div className="space-y-6">
        {/* Error Display */}
        {(detectMutation.isError || reparseMutation.isError) && (
          <Alert variant="destructive">
            <AlertDescription>
              {detectMutation.error?.message ||
                reparseMutation.error?.message ||
                'An error occurred'}
            </AlertDescription>
          </Alert>
        )}

        {/* Success Message */}
        {reparseMutation.isSuccess && (
          <Alert>
            <AlertDescription>
              Screenplay re-parsed successfully!
            </AlertDescription>
          </Alert>
        )}

        {/* Detection Section */}
        <DetectionSection
          pdfPath={pdfPath}
          onDetectionComplete={handleDetectionComplete}
          onDetect={handleDetect}
          isDetecting={detectMutation.isPending}
        />

        {/* Removal Section */}
        <RemovalSection
          detectedPatterns={detectedPatterns}
          selectedPatterns={selectedPatterns}
          onSelectionChange={setSelectedPatterns}
          manualEntries={manualEntries}
          onManualEntriesChange={setManualEntries}
          removeLines={removeLines}
          onRemoveLinesChange={setRemoveLines}
          globalReplace={globalReplace}
          onGlobalReplaceChange={setGlobalReplace}
        />

        {/* Re-parse Button */}
        <div className="flex flex-col items-center gap-2 pt-4">
          <button
            onClick={handleReparse}
            disabled={reparseMutation.isPending || totalPatternsToRemove === 0}
            className={appButtonVariants({
              variant: 'primary',
              size: 'lg',
            })}
          >
            {reparseMutation.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Re-parsing...
              </>
            ) : (
              <>
                <RefreshCw className="mr-2 h-4 w-4" />
                Re-parse Screenplay
              </>
            )}
          </button>

          {totalPatternsToRemove === 0 ? (
            <p className="text-muted-foreground text-sm">
              {hasDetected
                ? 'Select patterns or add manual entries to enable re-parsing'
                : 'Run detection or add patterns manually to enable re-parsing'}
            </p>
          ) : (
            <p className="text-muted-foreground text-sm">
              {totalPatternsToRemove} pattern
              {totalPatternsToRemove !== 1 ? 's' : ''} will be removed
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
