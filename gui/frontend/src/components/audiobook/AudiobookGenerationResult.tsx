import { Link } from '@tanstack/react-router';
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Download,
  FileAudio,
  Folder,
  Loader2,
  Play,
  Volume2,
  VolumeX,
} from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { appButtonVariants } from '@/components/ui/button-variants';
import { Card } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { useCacheMisses } from '@/hooks/queries/useCacheMisses';
import { apiService } from '@/services/api';
import type { AudiobookGenerationResult as ResultType } from '@/types';
import { downloadFile } from '@/utils/downloadService';

interface AudiobookGenerationResultProps {
  result: ResultType;
  projectName: string;
  onStartNew?: () => void;
}

export function AudiobookGenerationResult({
  result,
  projectName,
  onStartNew,
}: AudiobookGenerationResultProps) {
  // Fetch CURRENT cache misses (not from the run, but what's still missing)
  const { data: cacheMissesData, isLoading: cacheMissesLoading } =
    useCacheMisses(projectName, true);

  // Use live cache miss data if available, otherwise show nothing for missing clips
  const currentMissingClips = cacheMissesData?.cacheMisses || [];

  const hasIssues =
    currentMissingClips.length > 0 || result.silentClips.length > 0;

  const handleDownload = async () => {
    if (!result.outputFile) return;

    // Extract filename from path
    const filename = result.outputFile.split('/').pop() || 'audiobook.mp3';

    // Get download URL from backend (reuses screenplay download endpoint for any file)
    const url = apiService.getScreenplayDownloadFromPathUrl(
      result.outputFile,
      filename
    );

    // Download using existing service
    await downloadFile(url, filename, {
      showDialog: true,
      defaultPath: filename,
    });
  };

  return (
    <Card className="p-6">
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center space-x-3">
          <CheckCircle2 className="h-6 w-6 text-green-500" />
          <h3 className="text-lg font-semibold">Generation Complete</h3>
        </div>

        {/* Output File */}
        {result.outputFile && (
          <div className="flex items-center justify-between rounded-lg bg-green-50 p-4">
            <div className="flex items-center space-x-3">
              <FileAudio className="h-8 w-8 text-green-600" />
              <div>
                <p className="font-medium">Audiobook Ready</p>
                <p className="text-muted-foreground text-sm">
                  {result.outputFile.split('/').pop()}
                </p>
              </div>
            </div>
            <button
              onClick={handleDownload}
              className={appButtonVariants({
                variant: 'primary',
                size: 'sm',
              })}
            >
              <Download className="mr-2 h-4 w-4" />
              Download
            </button>
          </div>
        )}

        {/* Statistics */}
        <div className="space-y-3">
          <h4 className="font-medium">Generation Statistics</h4>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="bg-muted rounded-lg p-3 text-center">
              <div className="text-2xl font-bold">
                {result.stats.totalClips}
              </div>
              <div className="text-muted-foreground text-xs">Total Clips</div>
            </div>
            <div className="rounded-lg bg-green-100 p-3 text-center">
              <div className="text-2xl font-bold text-green-600">
                {result.stats.generatedClips}
              </div>
              <div className="text-xs text-green-700">Generated</div>
            </div>
            <div className="rounded-lg bg-blue-100 p-3 text-center">
              <div className="text-2xl font-bold text-blue-600">
                {result.stats.cachedClips}
              </div>
              <div className="text-xs text-blue-700">From Cache</div>
            </div>
            {result.stats.failedClips > 0 && (
              <div className="rounded-lg bg-red-100 p-3 text-center">
                <div className="text-destructive text-2xl font-bold">
                  {result.stats.failedClips}
                </div>
                <div className="text-destructive text-xs">Failed</div>
              </div>
            )}
          </div>
        </div>

        {/* Cache Folder */}
        <div className="flex items-center space-x-3 text-sm">
          <Folder className="text-muted-foreground h-4 w-4" />
          <span className="text-muted-foreground">Cache:</span>
          <code className="bg-muted rounded px-2 py-1 text-xs">
            {result.cacheFolder}
          </code>
        </div>

        <Separator />

        {/* Issues Section */}
        {hasIssues && (
          <div className="space-y-4">
            <h4 className="flex items-center space-x-2 font-medium">
              <AlertTriangle className="h-4 w-4 text-yellow-500" />
              <span>Issues Detected</span>
            </h4>

            {/* Missing Clips (live cache check) */}
            {cacheMissesLoading ? (
              <Alert variant="warning">
                <Loader2 className="h-4 w-4 animate-spin" />
                <AlertTitle>Checking for missing clips...</AlertTitle>
              </Alert>
            ) : (
              currentMissingClips.length > 0 && (
                <Alert variant="warning">
                  <Volume2 className="h-4 w-4" />
                  <AlertTitle className="flex items-center justify-between">
                    <span>
                      {currentMissingClips.length} Missing Clip
                      {currentMissingClips.length !== 1 ? 's' : ''}
                    </span>
                    <Link
                      to="/project/review"
                      state={{ scrollToSection: 'missing-clips' }}
                      className="flex items-center gap-1 text-xs font-normal underline hover:no-underline"
                    >
                      Review and fix
                      <ArrowRight className="h-3 w-3" />
                    </Link>
                  </AlertTitle>
                  <AlertDescription>
                    <div className="mt-2 space-y-1">
                      {currentMissingClips.slice(0, 5).map((miss, i) => (
                        <div
                          key={i}
                          className="flex items-center space-x-2 text-xs"
                        >
                          <Badge variant="secondary" className="text-xs">
                            {miss.speaker}
                          </Badge>
                          <span className="text-muted-foreground truncate">
                            {miss.text}...
                          </span>
                        </div>
                      ))}
                      {currentMissingClips.length > 5 && (
                        <p className="text-muted-foreground text-xs">
                          ...and {currentMissingClips.length - 5} more
                        </p>
                      )}
                    </div>
                  </AlertDescription>
                </Alert>
              )
            )}

            {/* Silent Clips */}
            {result.silentClips.length > 0 && (
              <Alert variant="warning">
                <VolumeX className="h-4 w-4" />
                <AlertTitle className="flex items-center justify-between">
                  <span>
                    {result.silentClips.length} Silent Clip
                    {result.silentClips.length !== 1 ? 's' : ''}
                  </span>
                  <Link
                    to="/project/review"
                    state={{ scrollToSection: 'silent-clips' }}
                    className="flex items-center gap-1 text-xs font-normal underline hover:no-underline"
                  >
                    Review and fix
                    <ArrowRight className="h-3 w-3" />
                  </Link>
                </AlertTitle>
                <AlertDescription>
                  <div className="mt-2 space-y-1">
                    {result.silentClips.slice(0, 5).map((clip, i) => (
                      <div
                        key={i}
                        className="flex items-center space-x-2 text-xs"
                      >
                        <Badge variant="secondary" className="text-xs">
                          {clip.speaker}
                        </Badge>
                        <span className="text-muted-foreground truncate">
                          {clip.text}...
                        </span>
                      </div>
                    ))}
                    {result.silentClips.length > 5 && (
                      <p className="text-muted-foreground text-xs">
                        ...and {result.silentClips.length - 5} more
                      </p>
                    )}
                  </div>
                </AlertDescription>
              </Alert>
            )}
          </div>
        )}

        {/* Log File Link */}
        {result.logFile && (
          <div className="text-muted-foreground text-center text-xs">
            <p>
              Full log available at:{' '}
              <code className="bg-muted rounded px-1">{result.logFile}</code>
            </p>
          </div>
        )}

        {/* Start New Generation Button */}
        {onStartNew && (
          <>
            <Separator />
            <div className="flex justify-center">
              <button
                onClick={onStartNew}
                className={appButtonVariants({
                  variant: 'secondary',
                  size: 'lg',
                })}
              >
                <Play className="mr-2 h-4 w-4" />
                Start New Generation
              </button>
            </div>
          </>
        )}
      </div>
    </Card>
  );
}
