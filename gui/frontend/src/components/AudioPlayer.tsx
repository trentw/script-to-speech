import React, { useState, useRef } from 'react';
import { Play, Pause, Square, Download, Volume2, MoreHorizontal } from 'lucide-react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Slider } from './ui/slider';
import { getAudioUrls, downloadAudio, getAudioFilename, hasAudioFiles } from '../utils/audioUtils';
import type { TaskStatusResponse } from '../types';

interface AudioPlayerProps {
  tasks: TaskStatusResponse[];
}

export const AudioPlayer: React.FC<AudioPlayerProps> = ({ tasks }) => {
  const [currentTrack, setCurrentTrack] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const audioRef = useRef<HTMLAudioElement>(null);

  const completedTasks = tasks.filter(task => 
    task.status === 'completed' && hasAudioFiles(task)
  );

  const playAudio = async (audioUrl: string) => {
    if (audioRef.current) {
      if (currentTrack === audioUrl && isPlaying) {
        // Pause current track
        audioRef.current.pause();
        setIsPlaying(false);
      } else {
        // Play new track or resume
        if (currentTrack !== audioUrl) {
          audioRef.current.src = audioUrl;
          setCurrentTrack(audioUrl);
        }
        try {
          await audioRef.current.play();
          setIsPlaying(true);
        } catch (error) {
          console.error('Error playing audio:', error);
        }
      }
    }
  };

  const stopAudio = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      setIsPlaying(false);
      setCurrentTime(0);
    }
  };

  const handleTimeUpdate = () => {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime);
    }
  };

  const handleLoadedMetadata = () => {
    if (audioRef.current) {
      setDuration(audioRef.current.duration);
    }
  };

  const handleEnded = () => {
    setIsPlaying(false);
    setCurrentTime(0);
  };

  const handleSeek = (values: number[]) => {
    const newTime = values[0];
    if (audioRef.current) {
      audioRef.current.currentTime = newTime;
      setCurrentTime(newTime);
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleDownloadAudio = (audioUrl: string, filename?: string) => {
    downloadAudio(audioUrl, filename);
  };

  if (completedTasks.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <Volume2 className="w-8 h-8 mx-auto mb-2 opacity-50" />
        <p className="text-sm">No audio files ready</p>
        <p className="text-xs mt-1">Generate speech to see audio player</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Hidden audio element */}
      <audio
        ref={audioRef}
        onTimeUpdate={handleTimeUpdate}
        onLoadedMetadata={handleLoadedMetadata}
        onEnded={handleEnded}
      />

      {/* Current track player */}
      {currentTrack && (
        <div className="p-4 bg-accent/30 border border-accent rounded-lg">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Volume2 className="w-4 h-4" />
              <span className="font-medium">Now Playing</span>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={stopAudio}
              className="h-7 px-2"
            >
              <Square className="w-3 h-3 mr-1" />
              Stop
            </Button>
          </div>

          {/* Progress bar */}
          <div className="space-y-2">
            <Slider
              value={[currentTime]}
              onValueChange={handleSeek}
              max={duration || 0}
              step={0.1}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>{formatTime(currentTime)}</span>
              <span>{formatTime(duration)}</span>
            </div>
          </div>
        </div>
      )}

      {/* Track list */}
      <div className="space-y-2">
        {completedTasks.map((task) => {
          // Use shared utility to get audio URLs
          const audioItems = getAudioUrls(task);
          
          return audioItems.map((audioUrl, fileIndex) => {
            const isCurrentTrack = currentTrack === audioUrl;
            const isPlayingThis = isCurrentTrack && isPlaying;
            
            // Get display text from different possible sources
            const displayText = task.request?.text || 
                               task.result?.text_preview || 
                               'Generated audio';
            const truncatedText = displayText.length > 60 ? 
              displayText.slice(0, 60) + '...' : displayText;

            // Get provider and voice info
            const provider = task.request?.provider || task.result?.provider;
            const voiceId = task.request?.sts_id || task.result?.voice_id;

            return (
              <div
                key={`${task.task_id}-${fileIndex}`}
                className={`p-3 border rounded-lg transition-all duration-200 ${
                  isCurrentTrack
                    ? 'border-primary bg-accent'
                    : 'border-border hover:border-accent hover:bg-accent/50'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => playAudio(audioUrl)}
                      className="h-8 w-8 p-0 rounded-full"
                    >
                      {isPlayingThis ? (
                        <Pause className="w-4 h-4" />
                      ) : (
                        <Play className="w-4 h-4" />
                      )}
                    </Button>
                    
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-foreground">
                        {provider && (
                          <Badge variant="outline" className="mr-2 text-xs">
                            {provider}
                          </Badge>
                        )}
                        {voiceId && (
                          <span className="text-sm">{voiceId}</span>
                        )}
                      </div>
                      <div className="text-sm text-muted-foreground italic truncate">
                        "{truncatedText}"
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDownloadAudio(audioUrl, getAudioFilename(task, fileIndex))}
                      className="h-7 px-2"
                    >
                      <Download className="w-3 h-3" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 w-7 p-0"
                    >
                      <MoreHorizontal className="w-3 h-3" />
                    </Button>
                  </div>
                </div>
              </div>
            );
          });
        })}
      </div>

      {/* Batch actions */}
      {completedTasks.length > 1 && (
        <div className="border-t border-border pt-4">
          <div className="flex justify-between items-center">
            <span className="text-sm text-muted-foreground">
              {completedTasks.reduce((sum, task) => {
                const audioItems = getAudioUrls(task);
                return sum + audioItems.length;
              }, 0)} audio files
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                completedTasks.forEach(task => {
                  const audioItems = getAudioUrls(task);
                  audioItems.forEach((audioUrl, index) => 
                    handleDownloadAudio(audioUrl, getAudioFilename(task, index))
                  );
                });
              }}
            >
              <Download className="w-3 h-3 mr-1" />
              Download All
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};