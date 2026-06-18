import {
  AlertCircle,
  AlertTriangle,
  Ban,
  CheckCircle2,
  Clock,
  Loader2,
  X,
  XCircle,
} from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import {
  appButtonVariants,
  buttonUtils,
} from '@/components/ui/button-variants';
import { Card } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import type { AudiobookGenerationProgress as ProgressType } from '@/types';
import { PHASE_LABELS } from '@/types';

interface AudiobookGenerationProgressProps {
  progress: ProgressType;
  /** Called when the user confirms cancelling the generation. */
  onCancel?: () => void;
  /** True while a cancel request is in flight (button shows a spinner). */
  isCancelling?: boolean;
}

// Phases during which concatenation/export has started: cancelling here is a
// no-op (we let it finish to avoid a partial/corrupt output MP3).
const NON_CANCELLABLE_PHASES = ['concatenating', 'exporting', 'finalizing'];

export function AudiobookGenerationProgress({
  progress,
  onCancel,
  isCancelling = false,
}: AudiobookGenerationProgressProps) {
  const getStatusIcon = () => {
    switch (progress.status) {
      case 'pending':
        return <Clock className="h-5 w-5 text-blue-500" />;
      case 'processing':
        return <Loader2 className="text-primary h-5 w-5 animate-spin" />;
      case 'completed':
        return <CheckCircle2 className="h-5 w-5 text-green-500" />;
      case 'failed':
        return <XCircle className="text-destructive h-5 w-5" />;
      case 'cancelled':
        return <Ban className="text-muted-foreground h-5 w-5" />;
    }
  };

  const getStatusBadgeVariant = ():
    | 'secondary'
    | 'default'
    | 'destructive'
    | 'success' => {
    switch (progress.status) {
      case 'pending':
        return 'secondary';
      case 'processing':
        return 'default';
      case 'completed':
        return 'success';
      case 'failed':
        return 'destructive';
      case 'cancelled':
        return 'secondary';
      default:
        return 'secondary';
    }
  };

  const overallPercentage = progress.overallProgress * 100;
  const phasePercentage = progress.phaseProgress * 100;
  const phaseLabel = PHASE_LABELS[progress.phase] || progress.phase;

  const isRunning =
    progress.status === 'processing' || progress.status === 'pending';
  const isFinishing = NON_CANCELLABLE_PHASES.includes(progress.phase);
  const showCancel = !!onCancel && isRunning;

  return (
    <Card className="p-6">
      <div className="space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            {getStatusIcon()}
            <h3 className="text-lg font-semibold">Audio Generation</h3>
          </div>
          <Badge variant={getStatusBadgeVariant()}>{progress.status}</Badge>
        </div>

        {/* Phase indicator */}
        {progress.status === 'processing' && (
          <div className="bg-muted rounded-lg p-3">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium">{phaseLabel}</span>
              <span className="text-muted-foreground">
                {phasePercentage.toFixed(0)}%
              </span>
            </div>
          </div>
        )}

        {/* Overall Progress */}
        {(progress.status === 'processing' ||
          progress.status === 'pending') && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Overall Progress</span>
              <span className="font-medium">
                {overallPercentage.toFixed(0)}%
              </span>
            </div>
            <Progress value={overallPercentage} className="h-2" />
          </div>
        )}

        {/* Message */}
        <p className="text-sm">{progress.message}</p>

        {/* Cancelled summary — generated clips are kept and reused */}
        {progress.status === 'cancelled' && (
          <Alert>
            <Ban className="h-4 w-4" />
            <AlertTitle>Generation cancelled</AlertTitle>
            <AlertDescription>
              {progress.stats
                ? `${
                    progress.stats.cachedClips + progress.stats.generatedClips
                  } of ${progress.stats.totalClips} clips are cached. `
                : ''}
              Generate again to continue — already generated clips are reused.
            </AlertDescription>
          </Alert>
        )}

        {/* Stats during generation */}
        {progress.stats && progress.phase === 'generating' && (
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div className="bg-muted rounded-lg p-3">
              <div className="text-muted-foreground">Total Clips</div>
              <div className="text-lg font-semibold">
                {progress.stats.totalClips}
              </div>
            </div>
            <div className="bg-muted rounded-lg p-3">
              <div className="text-muted-foreground">Generated</div>
              <div className="text-lg font-semibold text-green-600">
                {progress.stats.generatedClips}
              </div>
            </div>
            {progress.stats.cachedClips > 0 && (
              <div className="bg-muted rounded-lg p-3">
                <div className="text-muted-foreground">Cached</div>
                <div className="text-lg font-semibold text-blue-600">
                  {progress.stats.cachedClips}
                </div>
              </div>
            )}
            {progress.stats.failedClips > 0 && (
              <div className="bg-muted rounded-lg p-3">
                <div className="text-muted-foreground">Failed</div>
                <div className="text-destructive text-lg font-semibold">
                  {progress.stats.failedClips}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Rate limit warnings */}
        {progress.stats?.rateLimitedProviders &&
          progress.stats.rateLimitedProviders.length > 0 && (
            <Alert variant="warning">
              <AlertTriangle className="h-4 w-4" />
              <AlertTitle>Rate Limited</AlertTitle>
              <AlertDescription>
                {progress.stats.rateLimitedProviders.map((p, i) => (
                  <span key={p.provider}>
                    {i > 0 && ', '}
                    {p.provider}
                  </span>
                ))}
                {' - Generation may be slower'}
              </AlertDescription>
            </Alert>
          )}

        {/* Error Alert */}
        {progress.error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Error</AlertTitle>
            <AlertDescription>{progress.error}</AlertDescription>
          </Alert>
        )}

        {/* Timestamps */}
        <div className="text-muted-foreground space-y-1 text-xs">
          {progress.createdAt && (
            <p>Started: {new Date(progress.createdAt).toLocaleString()}</p>
          )}
          {progress.completedAt && (
            <p>Completed: {new Date(progress.completedAt).toLocaleString()}</p>
          )}
        </div>

        {/* Cancel action (bottom-right) */}
        {showCancel && (
          <div className="flex justify-end pt-2">
            {isFinishing ? (
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button
                      type="button"
                      aria-disabled
                      onClick={(e) => e.preventDefault()}
                      className={cn(
                        appButtonVariants({ variant: 'secondary', size: 'sm' }),
                        buttonUtils.ariaDisabled
                      )}
                    >
                      <X className="h-4 w-4" />
                      Cancel generation
                    </button>
                  </TooltipTrigger>
                  <TooltipContent side="top">
                    <p>
                      Finishing audiobook — generation can&apos;t be cancelled
                      now.
                    </p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            ) : (
              <button
                type="button"
                onClick={onCancel}
                disabled={isCancelling}
                className={appButtonVariants({
                  variant: 'secondary',
                  size: 'sm',
                })}
              >
                {isCancelling ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <X className="h-4 w-4" />
                )}
                {isCancelling ? 'Cancelling…' : 'Cancel generation'}
              </button>
            )}
          </div>
        )}
      </div>
    </Card>
  );
}
