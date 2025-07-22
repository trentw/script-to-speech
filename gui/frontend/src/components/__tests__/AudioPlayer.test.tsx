import { act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { render, screen, waitFor } from '@/test/utils/render'
import type { TaskStatusResponse } from '@/types'

import { AudioPlayer } from '../AudioPlayer'

// Mock the audio utilities
vi.mock('@/utils/audioUtils', () => ({
  getAudioUrls: vi.fn((task) => {
    if (task.audio_urls) return task.audio_urls
    if (task.result?.files) return task.result.files
    return []
  }),
  hasAudioFiles: vi.fn((task) => {
    if (task.audio_urls?.length > 0) return true
    if (task.result?.files?.length > 0) return true
    return false
  }),
  getAudioFilename: vi.fn((task, index) => `${task.task_id}-${index}.mp3`),
  downloadAudio: vi.fn(() => Promise.resolve()),
}))

// Mock the DownloadButton to simplify testing
vi.mock('../ui/DownloadButton', () => ({
  DownloadButton: ({ url, filename, onClick, iconOnly, ...props }: {
    url?: string
    filename?: string
    onClick?: () => void
    iconOnly?: boolean
    [key: string]: unknown
  }) => (
    <button
      data-testid="download-button"
      data-url={url}
      data-filename={filename}
      onClick={onClick}
      {...props}
    >
      {iconOnly ? '⬇' : 'Download'}
    </button>
  )
}))

// Create test tasks
const createTask = (overrides: Partial<TaskStatusResponse> = {}): TaskStatusResponse => ({
  task_id: 'test-123',
  status: 'completed',
  created_at: new Date().toISOString(),
  audio_urls: ['http://example.com/audio1.mp3'],
  request: {
    text: 'Test audio text',
    provider: 'openai',
    sts_id: 'alloy',
    config: {},
  },
  ...overrides,
})

describe('AudioPlayer', () => {
  // Get references to mocked methods
  let mockPlay: ReturnType<typeof vi.fn>
  let mockPause: ReturnType<typeof vi.fn>

  beforeEach(() => {
    // Reset any existing audio instances
    vi.clearAllMocks()
    
    // Get references to the mocked methods from our setup
    mockPlay = HTMLMediaElement.prototype.play as ReturnType<typeof vi.fn>
    mockPause = HTMLMediaElement.prototype.pause as ReturnType<typeof vi.fn>
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Empty State', () => {
    it('should show empty state when no tasks', () => {
      // Arrange & Act
      render(<AudioPlayer tasks={[]} />)

      // Assert
      expect(screen.getByText('No audio files ready')).toBeInTheDocument()
      expect(screen.getByText('Generate speech to see audio player')).toBeInTheDocument()
    })

    it('should show empty state when no completed tasks', () => {
      // Arrange
      const pendingTasks = [
        createTask({ status: 'pending', audio_urls: [] }),
        createTask({ status: 'processing', audio_urls: [] }),
      ]

      // Act
      render(<AudioPlayer tasks={pendingTasks} />)

      // Assert
      expect(screen.getByText('No audio files ready')).toBeInTheDocument()
    })

    it('should show empty state when completed tasks have no audio', () => {
      // Arrange
      const tasksWithoutAudio = [
        createTask({ status: 'completed', audio_urls: [] }),
      ]

      // Act
      render(<AudioPlayer tasks={tasksWithoutAudio} />)

      // Assert
      expect(screen.getByText('No audio files ready')).toBeInTheDocument()
    })
  })

  describe('Audio Track Display', () => {
    it('should display completed tasks with audio', () => {
      // Arrange
      const tasks = [
        createTask({
          task_id: 'task-1',
          request: { text: 'First audio', provider: 'openai', sts_id: 'alloy', config: {} },
        }),
        createTask({
          task_id: 'task-2',
          request: { text: 'Second audio', provider: 'elevenlabs', sts_id: 'rachel', config: {} },
        }),
      ]

      // Act
      render(<AudioPlayer tasks={tasks} />)

      // Assert
      expect(screen.getByText('"First audio"')).toBeInTheDocument()
      expect(screen.getByText('"Second audio"')).toBeInTheDocument()
      expect(screen.getByText('openai')).toBeInTheDocument()
      expect(screen.getByText('elevenlabs')).toBeInTheDocument()
      expect(screen.getByText('alloy')).toBeInTheDocument()
      expect(screen.getByText('rachel')).toBeInTheDocument()
    })

    it('should truncate long text', () => {
      // Arrange
      const longText = 'This is a very long text that should be truncated after 60 characters to prevent UI overflow'
      const tasks = [
        createTask({
          request: { text: longText, provider: 'openai', sts_id: 'alloy', config: {} },
        }),
      ]

      // Act
      render(<AudioPlayer tasks={tasks} />)

      // Assert
      const truncated = screen.getByText(/^"This is a very long text.*\.\.\."$/)
      expect(truncated).toBeInTheDocument()
      expect(truncated.textContent).toHaveLength(65) // 60 chars + quotes + ellipsis
    })

    it('should handle tasks with multiple audio files', () => {
      // Arrange
      const tasks = [
        createTask({
          audio_urls: [
            'http://example.com/audio1.mp3',
            'http://example.com/audio2.mp3',
          ],
        }),
      ]

      // Act
      render(<AudioPlayer tasks={tasks} />)

      // Assert
      const playButtons = screen.getAllByRole('button').filter(btn => 
        btn.querySelector('svg.lucide-play')
      )
      expect(playButtons).toHaveLength(2)
    })
  })

  describe('Audio Playback', () => {
    it('should play audio when play button is clicked', async () => {
      // Arrange
      const user = userEvent.setup()
      const tasks = [createTask()]
      render(<AudioPlayer tasks={tasks} />)

      // Act
      const playButton = screen.getAllByRole('button').find(btn => 
        btn.querySelector('svg.lucide-play')
      )!
      await user.click(playButton)

      // Assert
      await waitFor(() => {
        expect(mockPlay).toHaveBeenCalled()
      })
    })

    it('should pause audio when clicking play on current track', async () => {
      // Arrange
      const user = userEvent.setup()
      const tasks = [createTask()]
      render(<AudioPlayer tasks={tasks} />)
      
      // Start playing
      const playButton = screen.getAllByRole('button').find(btn => 
        btn.querySelector('svg.lucide-play')
      )!
      await user.click(playButton)
      
      // Act - click again to pause
      await user.click(playButton)

      // Assert
      await waitFor(() => {
        expect(mockPause).toHaveBeenCalled()
      })
    })

    it('should show now playing indicator', async () => {
      // Arrange
      const user = userEvent.setup()
      const tasks = [createTask()]
      render(<AudioPlayer tasks={tasks} />)

      // Act
      const playButton = screen.getAllByRole('button').find(btn => 
        btn.querySelector('svg.lucide-play')
      )!
      await user.click(playButton)

      // Assert
      await waitFor(() => {
        expect(screen.getByText('Now Playing')).toBeInTheDocument()
      })
    })

    it('should handle play errors gracefully', async () => {
      // Arrange
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
      const originalPlay = mockPlay.getMockImplementation()
      mockPlay.mockRejectedValue(new Error('Playback failed'))
      
      const user = userEvent.setup()
      const tasks = [createTask()]
      render(<AudioPlayer tasks={tasks} />)

      // Act
      const playButton = screen.getAllByRole('button').find(btn => 
        btn.querySelector('svg.lucide-play')
      )!
      await user.click(playButton)

      // Assert
      await waitFor(() => {
        expect(consoleError).toHaveBeenCalledWith('Error playing audio:', expect.any(Error))
      })

      // Cleanup - restore original implementation
      consoleError.mockRestore()
      mockPlay.mockImplementation(originalPlay || (() => Promise.resolve()))
    })
  })

  describe('Audio Controls', () => {
    it('should stop audio when stop button is clicked', async () => {
      // Arrange
      const user = userEvent.setup()
      const tasks = [createTask()]
      render(<AudioPlayer tasks={tasks} />)
      
      // Start playing
      const playButton = screen.getAllByRole('button').find(btn => 
        btn.querySelector('svg.lucide-play')
      )!
      await user.click(playButton)

      // Act
      const stopButton = await screen.findByText('Stop')
      await user.click(stopButton)

      // Assert
      expect(mockPause).toHaveBeenCalled()
    })

    it('should update time display during playback', async () => {
      // Arrange
      const user = userEvent.setup()
      const tasks = [createTask()]
      render(<AudioPlayer tasks={tasks} />)
      
      // Start playing
      const playButton = screen.getAllByRole('button').find(btn => 
        btn.querySelector('svg.lucide-play')
      )!
      await user.click(playButton)
      
      // Wait for play to be called
      await waitFor(() => {
        expect(mockPlay).toHaveBeenCalled()
      })

      // Act - simulate time progression by finding the audio element and updating it
      const audioElement = document.querySelector('audio') as HTMLAudioElement;
      expect(audioElement).toBeTruthy();
      
      // Get the mock instance for this element
      const mockInstance = (global as any).getAudioMockInstance(audioElement);
      expect(mockInstance).toBeTruthy();
      
      // Simulate time update
      act(() => {
        mockInstance.setCurrentTime(30); // 30 seconds
        audioElement.dispatchEvent(new Event('timeupdate'));
      });

      // Assert
      await waitFor(() => {
        expect(screen.getByText('0:30')).toBeInTheDocument()
      })
    })

    it('should display correct duration', async () => {
      // Arrange
      const user = userEvent.setup()
      const tasks = [createTask()]
      render(<AudioPlayer tasks={tasks} />)
      
      // Act - need to play audio to trigger loadedmetadata event
      const playButton = screen.getAllByRole('button').find(btn => 
        btn.querySelector('svg.lucide-play')
      )!
      await user.click(playButton)
      
      // Wait for loadedmetadata to fire
      await waitFor(() => {
        expect(mockPlay).toHaveBeenCalled()
      })

      // Assert - our mock has 120 seconds (2:00) duration
      await waitFor(() => {
        expect(screen.getByText('2:00')).toBeInTheDocument()
      })
    })

    it('should handle track ended event', async () => {
      // Arrange
      const user = userEvent.setup()
      const tasks = [createTask()]
      render(<AudioPlayer tasks={tasks} />)
      
      // Start playing
      const playButton = screen.getAllByRole('button').find(btn => 
        btn.querySelector('svg.lucide-play')
      )!
      await user.click(playButton)
      
      await waitFor(() => {
        expect(mockPlay).toHaveBeenCalled()
      })

      // Act - simulate track ending
      const audioElement = document.querySelector('audio') as HTMLAudioElement;
      expect(audioElement).toBeTruthy();
      
      const mockInstance = (global as any).getAudioMockInstance(audioElement);
      expect(mockInstance).toBeTruthy();
      
      // Simulate track ending
      act(() => {
        mockInstance.ended = true;
        mockInstance.paused = true;
        audioElement.dispatchEvent(new Event('ended'));
      });

      // Assert - track should no longer be playing (but "Now Playing" panel stays visible)
      // The component keeps the current track loaded, just stops playing
      await waitFor(() => {
        // Check that the Stop button is visible (indicating track is still loaded but not playing)
        expect(screen.getByText('Stop')).toBeInTheDocument()
        // The mockInstance should be paused
        expect(mockInstance.paused).toBe(true)
        expect(mockInstance.ended).toBe(true)
      })
    })
  })

  describe('Download Functionality', () => {
    it('should show download button for each track', () => {
      // Arrange
      const tasks = [
        createTask({ task_id: 'task-1' }),
        createTask({ task_id: 'task-2' }),
      ]

      // Act
      render(<AudioPlayer tasks={tasks} />)

      // Assert
      const downloadButtons = screen.getAllByTestId('download-button')
      expect(downloadButtons).toHaveLength(2)
      expect(downloadButtons[0]).toHaveAttribute('data-filename', 'task-1-0.mp3')
      expect(downloadButtons[1]).toHaveAttribute('data-filename', 'task-2-0.mp3')
    })

    it('should show batch download when multiple tasks', () => {
      // Arrange
      const tasks = [
        createTask({ task_id: 'task-1' }),
        createTask({ task_id: 'task-2' }),
      ]

      // Act
      render(<AudioPlayer tasks={tasks} />)

      // Assert
      expect(screen.getByText('Download All')).toBeInTheDocument()
      expect(screen.getByText('2 audio files')).toBeInTheDocument()
    })

    it('should not show batch download for single task', () => {
      // Arrange
      const tasks = [createTask()]

      // Act
      render(<AudioPlayer tasks={tasks} />)

      // Assert
      expect(screen.queryByText('Download All')).not.toBeInTheDocument()
    })

    it('should handle batch download', async () => {
      // Arrange
      const { downloadAudio } = await import('@/utils/audioUtils')
      const tasks = [
        createTask({ task_id: 'task-1' }),
        createTask({ task_id: 'task-2' }),
      ]
      const user = userEvent.setup()
      render(<AudioPlayer tasks={tasks} />)

      // Act
      await user.click(screen.getByText('Download All'))

      // Assert
      await waitFor(() => {
        expect(downloadAudio).toHaveBeenCalledTimes(2)
        expect(downloadAudio).toHaveBeenCalledWith(
          'http://example.com/audio1.mp3',
          'task-1-0.mp3'
        )
        expect(downloadAudio).toHaveBeenCalledWith(
          'http://example.com/audio1.mp3',
          'task-2-0.mp3'
        )
      })
    })

    it('should handle download errors gracefully', async () => {
      // Arrange
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
      const { downloadAudio } = await import('@/utils/audioUtils')
      vi.mocked(downloadAudio).mockRejectedValue(new Error('Download failed'))
      
      const tasks = [
        createTask({ task_id: 'task-1' }),
        createTask({ task_id: 'task-2' }),
      ]
      const user = userEvent.setup()
      render(<AudioPlayer tasks={tasks} />)

      // Act
      await user.click(screen.getByText('Download All'))

      // Assert
      await waitFor(() => {
        expect(consoleError).toHaveBeenCalledWith(
          'Failed to download task-1-0.mp3:',
          expect.any(Error)
        )
      })

      consoleError.mockRestore()
    })
  })

  describe('UI States', () => {
    it('should highlight current playing track', async () => {
      // Arrange
      const user = userEvent.setup()
      const tasks = [
        createTask({ 
          task_id: 'task-1',
          audio_urls: ['http://example.com/audio1.mp3'],
          request: { text: 'First audio', provider: 'openai', sts_id: 'alloy', config: {} }
        }),
        createTask({ 
          task_id: 'task-2',
          audio_urls: ['http://example.com/audio2.mp3'],
          request: { text: 'Second audio', provider: 'elevenlabs', sts_id: 'rachel', config: {} }
        }),
      ]
      render(<AudioPlayer tasks={tasks} />)

      // Act
      const playButtons = screen.getAllByRole('button').filter(btn => 
        btn.querySelector('svg.lucide-play')
      )
      await user.click(playButtons[0])

      // Assert
      // Wait for the track to start playing
      await waitFor(() => {
        expect(mockPlay).toHaveBeenCalled()
      })
      
      // Find track containers by looking for the provider badges
      const firstTrackContainer = screen.getByText('alloy').closest('.rounded-lg')
      const secondTrackContainer = screen.getByText('rachel').closest('.rounded-lg')
      
      expect(firstTrackContainer).toBeTruthy()
      expect(secondTrackContainer).toBeTruthy()
      expect(firstTrackContainer).toHaveClass('border-primary', 'bg-accent')
      expect(secondTrackContainer).not.toHaveClass('border-primary')
    })

    it('should show pause icon for playing track', async () => {
      // Arrange
      const user = userEvent.setup()
      const tasks = [createTask()]
      render(<AudioPlayer tasks={tasks} />)

      // Act
      const playButton = screen.getAllByRole('button').find(btn => 
        btn.querySelector('svg.lucide-play')
      )!
      await user.click(playButton)

      // Assert - check for Pause icon (different SVG path)
      await waitFor(() => {
        const pauseButton = screen.getAllByRole('button').find(btn => 
          btn.querySelector('svg.lucide-pause')
        )
        expect(pauseButton).toBeInTheDocument()
      })
    })
  })
})