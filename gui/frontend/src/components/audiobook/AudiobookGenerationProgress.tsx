import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Loader2,
  XCircle,
} from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import type { AudiobookGenerationProgress as ProgressType } from '@/types';
import { PHASE_LABELS } from '@/types';

interface AudiobookGenerationProgressProps {
  progress: ProgressType;
}

export function AudiobookGenerationProgress({
  progress,
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
      default:
        return 'secondary';
    }
  };

  const overallPercentage = progress.overallProgress * 100;
  const phasePercentage = progress.phaseProgress * 100;
  const phaseLabel = PHASE_LABELS[progress.phase] || progress.phase;

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
      </div>
    </Card>
  );
}
