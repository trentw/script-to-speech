import { Clock, MoreHorizontal, Play, Search } from 'lucide-react';
import React, { useMemo, useState } from 'react';

import { useSmartTaskPolling } from '../hooks/queries/useSmartTaskPolling';
import { useAudioCommands } from '../hooks/useAudioCommands';
import type { TaskStatusResponse } from '../types';
import {
  getAudioFilename,
  getAudioUrls,
  hasAudioFiles,
} from '../utils/audioUtils';
import { Badge } from './ui/badge';
import { appButtonVariants } from './ui/button-variants';
import { DownloadButton, DownloadButtonPresets } from './ui/DownloadButton';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from './ui/tooltip';

interface HistoryTabProps {
  onTaskSelect: (task: TaskStatusResponse) => void;
}

export const HistoryTab: React.FC<HistoryTabProps> = ({ onTaskSelect }) => {
  const [searchQuery, setSearchQuery] = useState('');

  const { data: allTasks = [], isLoading } = useSmartTaskPolling();
  const { playGeneratedAudio } = useAudioCommands();

  // Group tasks by date
  const groupedTasks = useMemo(() => {
    const completedTasks = allTasks
      .filter((task) => task.status === 'completed' || task.status === 'failed')
      .sort(
        (a, b) =>
          new Date(b.created_at || '').getTime() -
          new Date(a.created_at || '').getTime()
      );

    const filtered = !searchQuery
      ? completedTasks
      : completedTasks.filter((task) => {
          const text = (
            task.request?.text ||
            task.result?.text_preview ||
            ''
          ).toLowerCase();
          const provider = (
            task.request?.provider ||
            task.result?.provider ||
            ''
          ).toLowerCase();
          return (
            text.includes(searchQuery.toLowerCase()) ||
            provider.includes(searchQuery.toLowerCase())
          );
        });

    // Group by date
    const groups = new Map<string, TaskStatusResponse[]>();

    filtered.forEach((task) => {
      const date = task.created_at ? new Date(task.created_at) : new Date();
      const dateKey = date.toDateString();

      if (!groups.has(dateKey)) {
        groups.set(dateKey, []);
      }
      groups.get(dateKey)!.push(task);
    });

    return Array.from(groups.entries()).map(([dateKey, tasks]) => ({
      date: new Date(dateKey),
      dateKey,
      tasks,
    }));
  }, [allTasks, searchQuery]);

  const getDateLabel = (date: Date) => {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today.getTime() - 24 * 60 * 60 * 1000);
    const taskDate = new Date(
      date.getFullYear(),
      date.getMonth(),
      date.getDate()
    );

    if (taskDate.getTime() === today.getTime()) {
      return 'Today';
    } else if (taskDate.getTime() === yesterday.getTime()) {
      return 'Yesterday';
    } else {
      return date.toLocaleDateString('en-US', {
        month: 'long',
        day: 'numeric',
        year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
      });
    }
  };

  const formatTimeAgo = (dateString?: string) => {
    if (!dateString) return 'Unknown time';

    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-500';
      case 'failed':
        return 'bg-red-500';
      case 'running':
        return 'bg-blue-500';
      default:
        return 'bg-gray-500';
    }
  };

  const truncateText = (text: string, maxLength: number = 60) => {
    if (text.length <= maxLength) return text;
    return text.slice(0, maxLength) + '...';
  };

  const handlePlayAudio = (task: TaskStatusResponse) => {
    const audioUrls = getAudioUrls(task);
    if (audioUrls.length === 0) return;

    const audioUrl = audioUrls[0]; // Play first audio file
    const displayText =
      task.request?.text || task.result?.text_preview || 'Generated audio';
    const provider = task.request?.provider || task.result?.provider;
    const voiceId = task.request?.sts_id || task.result?.voice_id;

    // Load and play audio using command pattern
    playGeneratedAudio(
      audioUrl,
      displayText.length > 50 ? displayText.slice(0, 50) + '...' : displayText,
      [provider, voiceId].filter(Boolean).join(' • '),
      getAudioFilename(task, 0)
    );
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-4">
        <div className="border-primary h-6 w-6 animate-spin rounded-full border-b-2"></div>
        <span className="text-muted-foreground ml-2 text-sm">
          Loading history...
        </span>
      </div>
    );
  }

  return (
    <TooltipProvider>
      <div className="flex h-full flex-col">
        {/* Search Header */}
        <div className="border-border shrink-0 border-b p-4">
          <div className="relative">
            <Search className="text-muted-foreground absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 transform" />
            <input
              type="text"
              placeholder="Search history..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="border-border bg-background text-foreground placeholder:text-muted-foreground focus:ring-primary w-full rounded-md border py-2 pr-4 pl-10 focus:border-transparent focus:ring-2 focus:outline-none"
            />
          </div>
        </div>

        {/* History List */}
        <div className="flex-1 overflow-y-auto">
          {groupedTasks.length === 0 ? (
            <div className="text-muted-foreground p-4 text-center">
              {searchQuery ? (
                <>
                  <Search className="mx-auto mb-2 h-8 w-8 opacity-50" />
                  <p className="text-sm">No history found</p>
                  <p className="mt-1 text-xs">Try adjusting your search</p>
                </>
              ) : (
                <>
                  <Clock className="mx-auto mb-2 h-8 w-8 opacity-50" />
                  <p className="text-sm">No generation history</p>
                  <p className="mt-1 text-xs">
                    Completed generations will appear here
                  </p>
                </>
              )}
            </div>
          ) : (
            <div className="space-y-6">
              {groupedTasks.map(({ date, dateKey, tasks }) => (
                <div key={dateKey}>
                  {/* Date Header */}
                  <div className="bg-background/95 border-border sticky top-0 mb-2 border-b px-4 py-2 backdrop-blur">
                    <h3 className="text-foreground text-sm font-medium">
                      {getDateLabel(date)}
                    </h3>
                  </div>

                  {/* Tasks for this date */}
                  <div className="space-y-2 px-4">
                    {tasks.map((task) => (
                      <button
                        key={task.task_id}
                        className="group hover:bg-accent hover:text-accent-foreground hover:border-accent relative w-full cursor-pointer rounded-lg border p-3 text-left transition-all duration-200 hover:shadow-sm"
                        onClick={() => onTaskSelect(task)}
                      >
                        {/* Task Info - Full Width */}
                        <div className="min-w-0 flex-1">
                          <div className="mb-1 flex items-center gap-2">
                            <div
                              className={`h-2 w-2 rounded-full ${getStatusColor(task.status)}`}
                            />
                            <span className="text-muted-foreground text-xs">
                              {formatTimeAgo(task.created_at)}
                            </span>
                            {(task.request?.provider ||
                              task.result?.provider) && (
                              <Badge
                                variant="outline"
                                className="px-1.5 py-0 text-xs"
                              >
                                {task.request?.provider ||
                                  task.result?.provider}
                              </Badge>
                            )}
                          </div>

                          <p className="mb-1 text-sm font-medium">
                            {task.request?.text
                              ? truncateText(task.request.text)
                              : task.result?.text_preview
                                ? truncateText(task.result.text_preview)
                                : 'No text'}
                          </p>

                          {(task.request?.sts_id || task.result?.voice_id) && (
                            <p className="text-muted-foreground text-xs">
                              Voice:{' '}
                              {task.request?.sts_id || task.result?.voice_id}
                            </p>
                          )}
                        </div>

                        {/* Actions - Positioned at Top Line */}
                        <div className="absolute top-2 right-3 flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                          {task.status === 'completed' &&
                            hasAudioFiles(task) && (
                              <>
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <button
                                      className={appButtonVariants({
                                        variant: 'list-action',
                                        size: 'icon-sm',
                                      })}
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        handlePlayAudio(task);
                                      }}
                                    >
                                      <Play className="h-3 w-3" />
                                    </button>
                                  </TooltipTrigger>
                                  <TooltipContent>
                                    <p>Play audio</p>
                                  </TooltipContent>
                                </Tooltip>
                                {/* Download first audio file - for multiple files, user can see all in details panel */}
                                <DownloadButton
                                  url={getAudioUrls(task)[0]}
                                  filename={getAudioFilename(task, 0)}
                                  {...DownloadButtonPresets.listItem}
                                  tooltip="Download audio"
                                />
                              </>
                            )}
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <button
                                className={appButtonVariants({
                                  variant: 'list-action',
                                  size: 'icon-sm',
                                })}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  onTaskSelect(task);
                                }}
                              >
                                <MoreHorizontal className="h-3 w-3" />
                              </button>
                            </TooltipTrigger>
                            <TooltipContent>
                              <p>View details</p>
                            </TooltipContent>
                          </Tooltip>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </TooltipProvider>
  );
};
