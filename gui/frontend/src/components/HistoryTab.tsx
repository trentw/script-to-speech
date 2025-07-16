import React, { useState, useMemo } from 'react';
import { Search, Clock, Play, Download, MoreHorizontal } from 'lucide-react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from './ui/tooltip';
import { useAllTasks } from '../hooks/queries/useTaskStatus';
import { useCentralAudio } from '../stores/appStore';
import { downloadAudio, getAudioUrls, getAudioFilename, hasAudioFiles } from '../utils/audioUtils';
import type { TaskStatusResponse } from '../types';

interface HistoryTabProps {
  onTaskSelect: (task: TaskStatusResponse) => void;
}

export const HistoryTab: React.FC<HistoryTabProps> = ({ onTaskSelect }) => {
  const [searchQuery, setSearchQuery] = useState('');
  
  const { data: allTasks = [], isLoading } = useAllTasks();
  const { setAudioData } = useCentralAudio();
  
  // Group tasks by date
  const groupedTasks = useMemo(() => {
    const completedTasks = allTasks
      .filter(task => task.status === 'completed' || task.status === 'failed')
      .sort((a, b) => new Date(b.created_at || '').getTime() - new Date(a.created_at || '').getTime());
    
    const filtered = !searchQuery ? completedTasks : completedTasks.filter(task => {
      const text = (task.request?.text || task.result?.text_preview || '').toLowerCase();
      const provider = (task.request?.provider || task.result?.provider || '').toLowerCase();
      return text.includes(searchQuery.toLowerCase()) || 
             provider.includes(searchQuery.toLowerCase());
    });

    // Group by date
    const groups = new Map<string, TaskStatusResponse[]>();
    
    filtered.forEach(task => {
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
      tasks
    }));
  }, [allTasks, searchQuery]);

  const getDateLabel = (date: Date) => {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today.getTime() - 24 * 60 * 60 * 1000);
    const taskDate = new Date(date.getFullYear(), date.getMonth(), date.getDate());

    if (taskDate.getTime() === today.getTime()) {
      return 'Today';
    } else if (taskDate.getTime() === yesterday.getTime()) {
      return 'Yesterday';
    } else {
      return date.toLocaleDateString('en-US', { 
        month: 'long', 
        day: 'numeric', 
        year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined 
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
      case 'completed': return 'bg-green-500';
      case 'failed': return 'bg-red-500';
      case 'running': return 'bg-blue-500';
      default: return 'bg-gray-500';
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
    const displayText = task.request?.text || task.result?.text_preview || 'Generated audio';
    const provider = task.request?.provider || task.result?.provider;
    const voiceId = task.request?.sts_id || task.result?.voice_id;
    
    // Load into central audio player with autoplay
    setAudioData(
      audioUrl,
      displayText.length > 50 ? displayText.slice(0, 50) + '...' : displayText,
      [provider, voiceId].filter(Boolean).join(' • '),
      getAudioFilename(task, 0),
      true // autoplay
    );
  };

  const handleDownloadAudio = (task: TaskStatusResponse) => {
    const audioUrls = getAudioUrls(task);
    if (audioUrls.length === 0) return;
    
    // Download all audio files for this task
    audioUrls.forEach((audioUrl, index) => {
      downloadAudio(audioUrl, getAudioFilename(task, index));
    });
  };

  if (isLoading) {
    return (
      <div className="p-4 flex items-center justify-center">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary"></div>
        <span className="ml-2 text-sm text-muted-foreground">Loading history...</span>
      </div>
    );
  }
  
  return (
    <TooltipProvider>
      <div className="flex flex-col h-full">
        {/* Search Header */}
        <div className="p-4 border-b border-border shrink-0">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search history..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-border rounded-md bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            />
          </div>
        </div>
      
      {/* History List */}
      <div className="flex-1 overflow-y-auto">
        {groupedTasks.length === 0 ? (
          <div className="p-4 text-center text-muted-foreground">
            {searchQuery ? (
              <>
                <Search className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No history found</p>
                <p className="text-xs mt-1">Try adjusting your search</p>
              </>
            ) : (
              <>
                <Clock className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No generation history</p>
                <p className="text-xs mt-1">Completed generations will appear here</p>
              </>
            )}
          </div>
        ) : (
          <div className="space-y-6">
            {groupedTasks.map(({ date, dateKey, tasks }) => (
              <div key={dateKey}>
                {/* Date Header */}
                <div className="px-4 py-2 sticky top-0 bg-background/95 backdrop-blur border-b border-border">
                  <h3 className="text-sm font-medium text-foreground">
                    {getDateLabel(date)}
                  </h3>
                </div>
                
                {/* Tasks for this date */}
                <div className="px-4 space-y-2">
                  {tasks.map((task) => (
                    <div
                      key={task.task_id}
                      className="group relative rounded-lg border p-3 cursor-pointer transition-all duration-200 hover:bg-accent hover:text-accent-foreground hover:border-accent hover:shadow-sm"
                      onClick={() => onTaskSelect(task)}
                    >
                      {/* Task Info - Full Width */}
                      <div className="flex-1 min-w-0 group-hover:pr-24 transition-all duration-200">
                        <div className="flex items-center gap-2 mb-1">
                          <div className={`w-2 h-2 rounded-full ${getStatusColor(task.status)}`} />
                          <span className="text-xs text-muted-foreground">
                            {formatTimeAgo(task.created_at)}
                          </span>
                          {(task.request?.provider || task.result?.provider) && (
                            <Badge variant="outline" className="text-xs px-1.5 py-0">
                              {task.request?.provider || task.result?.provider}
                            </Badge>
                          )}
                        </div>
                        
                        <p className="text-sm font-medium mb-1">
                          {task.request?.text ? truncateText(task.request.text) : 
                           task.result?.text_preview ? truncateText(task.result.text_preview) : 'No text'}
                        </p>
                        
                        {(task.request?.sts_id || task.result?.voice_id) && (
                          <p className="text-xs text-muted-foreground">
                            Voice: {task.request?.sts_id || task.result?.voice_id}
                          </p>
                        )}
                      </div>
                      
                      {/* Actions - Positioned Absolutely */}
                      <div className="absolute right-3 top-3 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        {task.status === 'completed' && hasAudioFiles(task) && (
                          <>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-7 w-7 p-0 hover:bg-gray-800 hover:text-white dark:hover:bg-gray-700 dark:hover:text-white transition-colors cursor-pointer"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handlePlayAudio(task);
                                  }}
                                >
                                  <Play className="w-3 h-3" />
                                </Button>
                              </TooltipTrigger>
                              <TooltipContent>
                                <p>Play audio</p>
                              </TooltipContent>
                            </Tooltip>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-7 w-7 p-0 hover:bg-gray-800 hover:text-white dark:hover:bg-gray-700 dark:hover:text-white transition-colors cursor-pointer"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleDownloadAudio(task);
                                  }}
                                >
                                  <Download className="w-3 h-3" />
                                </Button>
                              </TooltipTrigger>
                              <TooltipContent>
                                <p>Download audio</p>
                              </TooltipContent>
                            </Tooltip>
                          </>
                        )}
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-7 w-7 p-0 hover:bg-gray-800 hover:text-white dark:hover:bg-gray-700 dark:hover:text-white transition-colors cursor-pointer"
                              onClick={(e) => {
                                e.stopPropagation();
                                onTaskSelect(task);
                              }}
                            >
                              <MoreHorizontal className="w-3 h-3" />
                            </Button>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>View details</p>
                          </TooltipContent>
                        </Tooltip>
                      </div>
                    </div>
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