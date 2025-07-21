import {
  ArrowLeft,
  Clock,
  Copy,
  FileText,
  Play,
  Settings,
  Volume2,
} from 'lucide-react';
import React from 'react';

import { useCentralAudio } from '../stores/appStore';
import type { TaskStatusResponse } from '../types';
import { getAudioFilename, getAudioUrls } from '../utils/audioUtils';
import { Badge } from './ui/badge';
import { appButtonVariants } from './ui/button-variants';
import { Card } from './ui/card';
import { DownloadButton, DownloadButtonPresets } from './ui/DownloadButton';

interface HistoryDetailsPanelProps {
  task: TaskStatusResponse;
  onBack: () => void;
}

export const HistoryDetailsPanel: React.FC<HistoryDetailsPanelProps> = ({
  task,
  onBack,
}) => {
  const { setAudioData } = useCentralAudio();
  const formatDateTime = (dateString?: string) => {
    if (!dateString) return 'Unknown time';

    const date = new Date(dateString);
    return date.toLocaleString();
  };

  const formatDuration = (startTime?: string, endTime?: string) => {
    if (!startTime || !endTime) return 'Unknown';

    const start = new Date(startTime).getTime();
    const end = new Date(endTime).getTime();
    const durationMs = end - start;
    const seconds = Math.round(durationMs / 1000);

    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-green-600 bg-green-50 border-green-200';
      case 'failed':
        return 'text-red-600 bg-red-50 border-red-200';
      case 'running':
        return 'text-blue-600 bg-blue-50 border-blue-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      // TODO: Show toast notification
    } catch (err) {
      console.error('Failed to copy text:', err);
    }
  };

  const handlePlayAudio = (audioUrl: string, index: number) => {
    const displayText =
      task.request?.text || task.result?.text_preview || 'Generated audio';
    const provider = task.request?.provider || task.result?.provider;
    const voiceId = task.request?.sts_id || task.result?.voice_id;

    // Load into central audio player with autoplay
    setAudioData(
      audioUrl,
      displayText.length > 50 ? displayText.slice(0, 50) + '...' : displayText,
      [provider, voiceId].filter(Boolean).join(' • '),
      getAudioFilename(task, index),
      true // autoplay
    );
  };

  return (
    <div className="bg-background flex h-full flex-col">
      {/* Header */}
      <div className="border-border flex items-center gap-3 border-b p-4">
        <button
          className={appButtonVariants({
            variant: 'list-action',
            size: 'icon-sm',
          })}
          onClick={onBack}
        >
          <ArrowLeft className="h-4 w-4" />
        </button>
        <h3 className="font-medium">Generation Details</h3>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        <div className="space-y-6 p-4">
          {/* Status Card */}
          <Card className="p-4">
            <div className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Clock className="text-muted-foreground h-4 w-4" />
                <span className="text-sm font-medium">Status</span>
              </div>
              <Badge className={getStatusColor(task.status)}>
                {task.status}
              </Badge>
            </div>

            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Created:</span>
                <span>{formatDateTime(task.created_at)}</span>
              </div>
              {task.completed_at && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Completed:</span>
                  <span>{formatDateTime(task.completed_at)}</span>
                </div>
              )}
              {task.created_at && task.completed_at && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Duration:</span>
                  <span>
                    {formatDuration(task.created_at, task.completed_at)}
                  </span>
                </div>
              )}
            </div>
          </Card>

          {/* Request Details */}
          {task.request && (
            <Card className="p-4">
              <div className="mb-3 flex items-center gap-2">
                <Settings className="text-muted-foreground h-4 w-4" />
                <span className="text-sm font-medium">Configuration</span>
              </div>

              <div className="space-y-3 text-sm">
                <div>
                  <span className="text-muted-foreground">Provider:</span>
                  <Badge variant="outline" className="ml-2">
                    {task.request.provider}
                  </Badge>
                </div>

                {task.request.sts_id && (
                  <div>
                    <span className="text-muted-foreground">Voice ID:</span>
                    <span className="ml-2 font-mono text-xs">
                      {task.request.sts_id}
                    </span>
                  </div>
                )}

                {task.request.config &&
                  Object.keys(task.request.config).length > 0 && (
                    <div>
                      <span className="text-muted-foreground">Parameters:</span>
                      <div className="bg-muted/30 mt-1 rounded p-2 font-mono text-xs">
                        {JSON.stringify(task.request.config, null, 2)}
                      </div>
                    </div>
                  )}
              </div>
            </Card>
          )}

          {/* Text Content */}
          {task.request?.text && (
            <Card className="p-4">
              <div className="mb-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FileText className="text-muted-foreground h-4 w-4" />
                  <span className="text-sm font-medium">Text Content</span>
                </div>
                <button
                  className={appButtonVariants({
                    variant: 'list-action',
                    size: 'sm',
                  })}
                  onClick={() => copyToClipboard(task.request!.text)}
                >
                  <Copy className="mr-1 h-3 w-3" />
                  Copy
                </button>
              </div>

              <div className="bg-muted/30 rounded-lg p-3 text-sm whitespace-pre-wrap">
                {task.request.text}
              </div>

              <div className="text-muted-foreground mt-2 text-xs">
                {task.request.text.length} characters
              </div>
            </Card>
          )}

          {/* Audio Results */}
          {getAudioUrls(task).length > 0 && (
            <Card className="p-4">
              <div className="mb-3 flex items-center gap-2">
                <Volume2 className="text-muted-foreground h-4 w-4" />
                <span className="text-sm font-medium">Generated Audio</span>
              </div>

              <div className="space-y-2">
                {getAudioUrls(task).map((url, index) => (
                  <div
                    key={index}
                    className="bg-muted/30 flex items-center justify-end rounded p-2"
                  >
                    <div className="flex items-center gap-1">
                      <button
                        className={appButtonVariants({
                          variant: 'list-action',
                          size: 'sm',
                        })}
                        onClick={() => handlePlayAudio(url, index)}
                      >
                        <Play className="mr-1 h-3 w-3" />
                        Play
                      </button>
                      <DownloadButton
                        url={url}
                        filename={getAudioFilename(task, index)}
                        {...DownloadButtonPresets.textButton}
                        tooltip={`Download audio ${index + 1}`}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Error Details */}
          {task.status === 'failed' && task.error && (
            <Card className="border-destructive p-4">
              <div className="mb-3 flex items-center gap-2">
                <span className="text-destructive text-sm font-medium">
                  Error Details
                </span>
              </div>

              <div className="bg-destructive/10 border-destructive/20 rounded-lg border p-3 text-sm">
                {task.error}
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};
