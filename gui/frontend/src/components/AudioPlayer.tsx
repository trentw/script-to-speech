import {
  Download,
  MoreHorizontal,
  Pause,
  Play,
  Square,
  Volume2,
} from 'lucide-react';
import React, { useRef, useState } from 'react';

import type { TaskStatusResponse } from '../types';
import {
  downloadAudio,
  getAudioFilename,
  getAudioUrls,
  hasAudioFiles,
} from '../utils/audioUtils';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { DownloadButton } from './ui/DownloadButton';
import { Slider } from './ui/slider';

interface AudioPlayerProps {
  tasks: TaskStatusResponse[];
}

export const AudioPlayer: React.FC<AudioPlayerProps> = ({ tasks }) => {
  const [currentTrack, setCurrentTrack] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const audioRef = useRef<HTMLAudioElement>(null);

  const completedTasks = tasks.filter(
    (task) => task.status === 'completed' && hasAudioFiles(task)
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

  const handleBatchDownload = async () => {
    for (const task of completedTasks) {
      const audioItems = getAudioUrls(task);
      for (let index = 0; index < audioItems.length; index++) {
        const audioUrl = audioItems[index];
        const filename = getAudioFilename(task, index);
        try {
          await downloadAudio(audioUrl, filename);
          // Small delay between downloads to prevent overwhelming the browser
          await new Promise((resolve) => setTimeout(resolve, 100));
        } catch (error) {
          console.error(`Failed to download ${filename}:`, error);
        }
      }
    }
  };

  if (completedTasks.length === 0) {
    return (
      <div className="text-muted-foreground py-8 text-center">
        <Volume2 className="mx-auto mb-2 h-8 w-8 opacity-50" />
        <p className="text-sm">No audio files ready</p>
        <p className="mt-1 text-xs">Generate speech to see audio player</p>
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
      >
        <track kind="captions" />
      </audio>

      {/* Current track player */}
      {currentTrack && (
        <div className="bg-accent/30 border-accent rounded-lg border p-4">
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Volume2 className="h-4 w-4" />
              <span className="font-medium">Now Playing</span>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={stopAudio}
              className="h-7 px-2"
            >
              <Square className="mr-1 h-3 w-3" />
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
            <div className="text-muted-foreground flex justify-between text-xs">
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
            const displayText =
              task.request?.text ||
              task.result?.text_preview ||
              'Generated audio';
            const truncatedText =
              displayText.length > 60
                ? displayText.slice(0, 60) + '...'
                : displayText;

            // Get provider and voice info
            const provider = task.request?.provider || task.result?.provider;
            const voiceId = task.request?.sts_id || task.result?.voice_id;

            return (
              <div
                key={`${task.task_id}-${fileIndex}`}
                className={`rounded-lg border p-3 transition-all duration-200 ${
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
                      className="h-8 w-8 rounded-full p-0"
                    >
                      {isPlayingThis ? (
                        <Pause className="h-4 w-4" />
                      ) : (
                        <Play className="h-4 w-4" />
                      )}
                    </Button>

                    <div className="min-w-0 flex-1">
                      <div className="text-foreground font-medium">
                        {provider && (
                          <Badge variant="outline" className="mr-2 text-xs">
                            {provider}
                          </Badge>
                        )}
                        {voiceId && <span className="text-sm">{voiceId}</span>}
                      </div>
                      <div className="text-muted-foreground truncate text-sm italic">
                        "{truncatedText}"
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-1">
                    <DownloadButton
                      url={audioUrl}
                      filename={getAudioFilename(task, fileIndex)}
                      variant="secondary"
                      size="sm"
                      iconOnly={false}
                      className="h-7 px-2"
                    />
                    <Button variant="ghost" size="sm" className="h-7 w-7 p-0">
                      <MoreHorizontal className="h-3 w-3" />
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
        <div className="border-border border-t pt-4">
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground text-sm">
              {completedTasks.reduce((sum, task) => {
                const audioItems = getAudioUrls(task);
                return sum + audioItems.length;
              }, 0)}{' '}
              audio files
            </span>
            <Button variant="outline" size="sm" onClick={handleBatchDownload}>
              <Download className="mr-1 h-3 w-3" />
              Download All
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};
