import React, { useState, useRef } from 'react';
import type { TaskStatusResponse } from '../types';
import { apiService } from '../services/api';

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
    task.status === 'completed' && task.result && task.result.files.length > 0
  );

  const playAudio = async (filename: string) => {
    if (audioRef.current) {
      if (currentTrack === filename && isPlaying) {
        // Pause current track
        audioRef.current.pause();
        setIsPlaying(false);
      } else {
        // Play new track or resume
        if (currentTrack !== filename) {
          audioRef.current.src = apiService.getAudioFile(filename);
          setCurrentTrack(filename);
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

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newTime = parseFloat(e.target.value);
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

  const downloadAudio = (filename: string) => {
    const url = apiService.getAudioFile(filename);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (completedTasks.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <p>No audio files ready</p>
        <p className="text-sm mt-1">Generate speech to see audio player</p>
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
        <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex items-center justify-between mb-3">
            <div className="font-medium text-blue-900">Now Playing</div>
            <button
              onClick={stopAudio}
              className="text-blue-600 hover:text-blue-800 text-sm"
            >
              Stop
            </button>
          </div>
          
          <div className="text-sm text-blue-800 mb-2 truncate">
            {currentTrack}
          </div>

          {/* Progress bar */}
          <div className="mb-2">
            <input
              type="range"
              min="0"
              max={duration || 0}
              value={currentTime}
              onChange={handleSeek}
              className="w-full h-2 bg-blue-200 rounded-lg appearance-none cursor-pointer"
            />
          </div>

          <div className="flex justify-between text-xs text-blue-700">
            <span>{formatTime(currentTime)}</span>
            <span>{formatTime(duration)}</span>
          </div>
        </div>
      )}

      {/* Track list */}
      <div className="space-y-2">
        {completedTasks.map((task) => 
          task.result!.files.map((filename, fileIndex) => {
            const isCurrentTrack = currentTrack === filename;
            const isPlayingThis = isCurrentTrack && isPlaying;

            return (
              <div
                key={`${task.task_id}-${fileIndex}`}
                className={`p-3 border rounded-lg ${
                  isCurrentTrack
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <button
                      onClick={() => playAudio(filename)}
                      className={`w-8 h-8 rounded-full flex items-center justify-center text-white ${
                        isPlayingThis
                          ? 'bg-blue-600 hover:bg-blue-700'
                          : 'bg-gray-600 hover:bg-gray-700'
                      }`}
                    >
                      {isPlayingThis ? '⏸️' : '▶️'}
                    </button>
                    
                    <div>
                      <div className="font-medium text-gray-900">
                        {task.result!.provider} - {task.result!.voice_id}
                      </div>
                      <div className="text-sm text-gray-600 italic">
                        "{task.result!.text_preview}"
                      </div>
                      <div className="text-xs text-gray-500">
                        {filename}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => downloadAudio(filename)}
                      className="text-gray-600 hover:text-gray-800 text-sm px-2 py-1 border border-gray-300 rounded"
                    >
                      ⬇️ Download
                    </button>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Batch actions */}
      {completedTasks.length > 1 && (
        <div className="border-t pt-4">
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600">
              {completedTasks.reduce((sum, task) => sum + task.result!.files.length, 0)} audio files
            </span>
            <button
              onClick={() => {
                completedTasks.forEach(task => 
                  task.result!.files.forEach(filename => 
                    downloadAudio(filename)
                  )
                );
              }}
              className="btn-secondary text-sm"
            >
              Download All
            </button>
          </div>
        </div>
      )}
    </div>
  );
};