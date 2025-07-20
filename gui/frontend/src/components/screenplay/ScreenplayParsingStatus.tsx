import { Card } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Loader2, CheckCircle2, XCircle, AlertCircle } from 'lucide-react';
import type { TaskStatusResponse } from '@/types';

interface ScreenplayParsingStatusProps {
  status: TaskStatusResponse;
}

export function ScreenplayParsingStatus({ status }: ScreenplayParsingStatusProps) {
  const getStatusIcon = () => {
    switch (status.status) {
      case 'pending':
        return <Loader2 className="h-5 w-5 animate-spin text-blue-500" />;
      case 'processing':
        return <Loader2 className="h-5 w-5 animate-spin text-primary" />;
      case 'completed':
        return <CheckCircle2 className="h-5 w-5 text-green-500" />;
      case 'failed':
        return <XCircle className="h-5 w-5 text-destructive" />;
    }
  };

  const getStatusBadgeVariant = () => {
    switch (status.status) {
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

  const progressPercentage = status.progress ? status.progress * 100 : 0;

  return (
    <Card className="p-6">
      <div className="space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            {getStatusIcon()}
            <h3 className="text-lg font-semibold">Parsing Status</h3>
          </div>
          <Badge variant={getStatusBadgeVariant() as any}>
            {status.status}
          </Badge>
        </div>

        {/* Progress */}
        {status.status === 'processing' && (
          <div className="space-y-2">
            <Progress value={progressPercentage} className="h-2" />
            <p className="text-sm text-muted-foreground">
              {progressPercentage.toFixed(0)}% complete
            </p>
          </div>
        )}

        {/* Message */}
        <p className="text-sm">{status.message}</p>

        {/* Error Alert */}
        {status.error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Error</AlertTitle>
            <AlertDescription>{status.error}</AlertDescription>
          </Alert>
        )}

        {/* Timestamps */}
        <div className="text-xs text-muted-foreground space-y-1">
          {status.created_at && (
            <p>Started: {new Date(status.created_at).toLocaleString()}</p>
          )}
          {status.completed_at && (
            <p>Completed: {new Date(status.completed_at).toLocaleString()}</p>
          )}
        </div>
      </div>
    </Card>
  );
}