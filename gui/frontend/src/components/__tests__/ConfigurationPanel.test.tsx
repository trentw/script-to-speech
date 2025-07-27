import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useConfiguration } from '@/stores/appStore';
import { render, screen, waitFor } from '@/test/utils/render';
import { TEST_PROVIDERS, TEST_VOICES } from '@/test/utils/test-data';
import type { VoiceEntry } from '@/types';

import { ConfigurationPanel } from '../ConfigurationPanel';

// Mock the store
vi.mock('@/stores/appStore', () => ({
  useConfiguration: vi.fn(() => ({
    selectedProvider: null,
    selectedVoice: null,
    currentConfig: {},
  })),
}));

// Mock the child components to simplify testing
vi.mock('../app/ProviderSelectionSelector', () => ({
  ProviderSelectionSelector: ({
    selectedProvider,
    onProviderSelect,
    onOpenProviderPanel,
  }: {
    selectedProvider?: string;
    onProviderSelect: (provider: string) => void;
    onOpenProviderPanel: () => void;
  }) => (
    <div data-testid="provider-selector">
      <button
        onClick={() => onProviderSelect('openai')}
        data-testid="select-provider-btn"
      >
        {selectedProvider || 'Select Provider'}
      </button>
      <button onClick={onOpenProviderPanel}>Browse All</button>
    </div>
  ),
}));

vi.mock('../VoiceSelector', () => ({
  VoiceSelector: ({
    selectedVoice,
    onVoiceSelect,
    onOpenVoicePanel,
  }: {
    selectedVoice?: VoiceEntry;
    onVoiceSelect: (voice: VoiceEntry) => void;
    onOpenVoicePanel: () => void;
  }) => (
    <div data-testid="voice-selector">
      <button onClick={() => onVoiceSelect(TEST_VOICES[0])}>
        {selectedVoice?.sts_id || 'Select Voice'}
      </button>
      <button onClick={onOpenVoicePanel}>Browse Voices</button>
    </div>
  ),
}));

vi.mock('../ConfigForm', () => ({
  ConfigForm: ({
    config,
    onConfigChange,
  }: {
    config?: Record<string, unknown>;
    onConfigChange: (config: Record<string, unknown>) => void;
  }) => (
    <div data-testid="config-form">
      <input
        type="number"
        value={config?.speed || 1}
        onChange={(e) => onConfigChange({ ...config, speed: e.target.value })}
        data-testid="speed-input"
      />
    </div>
  ),
}));

vi.mock('../ProviderSelectionPanel', () => ({
  ProviderSelectionPanel: ({
    onProviderSelect,
    onBack,
  }: {
    onProviderSelect: (provider: string) => void;
    onBack: () => void;
  }) => (
    <div data-testid="provider-panel">
      <button onClick={onBack}>Back</button>
      <button onClick={() => onProviderSelect('elevenlabs')}>ElevenLabs</button>
    </div>
  ),
}));

vi.mock('../VoiceSelectionPanel', () => ({
  VoiceSelectionPanel: ({
    onVoiceSelect,
    onBack,
  }: {
    onVoiceSelect: (voice: VoiceEntry) => void;
    onBack: () => void;
  }) => (
    <div data-testid="voice-panel">
      <button onClick={onBack}>Back</button>
      <button onClick={() => onVoiceSelect(TEST_VOICES[1])}>
        Select Second Voice
      </button>
    </div>
  ),
}));

vi.mock('../HistoryTab', () => ({
  HistoryTab: ({
    onTaskSelect,
  }: {
    onTaskSelect: (task: { task_id: string; status: string }) => void;
  }) => (
    <div data-testid="history-tab">
      <button
        onClick={() => onTaskSelect({ task_id: '123', status: 'completed' })}
      >
        Task 123
      </button>
    </div>
  ),
}));

vi.mock('../HistoryDetailsPanel', () => ({
  HistoryDetailsPanel: ({
    task,
    onBack,
  }: {
    task: { task_id: string };
    onBack: () => void;
  }) => (
    <div data-testid="history-details">
      <button onClick={onBack}>Back</button>
      <span>Task: {task.task_id}</span>
    </div>
  ),
}));

describe('ConfigurationPanel', () => {
  const defaultProps = {
    providers: TEST_PROVIDERS,
    voiceLibrary: { openai: TEST_VOICES },
    voiceCounts: { openai: 2 },
    providerErrors: {},
    loading: false,
    onProviderChange: vi.fn(),
    onVoiceSelect: vi.fn(),
    onConfigChange: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    // Reset store mock to default state
    vi.mocked(useConfiguration).mockReturnValue({
      selectedProvider: null,
      selectedVoice: null,
      currentConfig: {},
    });
  });

  describe('Tab Navigation', () => {
    it('should render settings and history tabs', () => {
      // Arrange & Act
      render(<ConfigurationPanel {...defaultProps} />);

      // Assert
      expect(screen.getByRole('tab', { name: 'Settings' })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: 'History' })).toBeInTheDocument();
    });

    it('should show settings content by default', () => {
      // Arrange & Act
      render(<ConfigurationPanel {...defaultProps} />);

      // Assert
      expect(screen.getByText('Text to Speech Provider')).toBeInTheDocument();
      expect(screen.queryByTestId('history-tab')).not.toBeInTheDocument();
    });

    it('should switch to history tab when clicked', async () => {
      // Arrange
      const user = userEvent.setup();
      render(<ConfigurationPanel {...defaultProps} />);

      // Act
      await user.click(screen.getByRole('tab', { name: 'History' }));

      // Assert
      await waitFor(() => {
        expect(screen.getByTestId('history-tab')).toBeInTheDocument();
      });
      expect(
        screen.queryByText('Text to Speech Provider')
      ).not.toBeInTheDocument();
    });
  });

  describe('Provider Selection', () => {
    it('should display provider selector', () => {
      // Arrange & Act
      render(<ConfigurationPanel {...defaultProps} />);

      // Assert
      expect(screen.getByTestId('provider-selector')).toBeInTheDocument();
    });

    it('should call onProviderChange when provider is selected', async () => {
      // Arrange
      const user = userEvent.setup();
      render(<ConfigurationPanel {...defaultProps} />);

      // Act
      await user.click(screen.getByText('Select Provider'));

      // Assert
      expect(defaultProps.onProviderChange).toHaveBeenCalledWith('openai');
    });

    it('should show provider panel when browse is clicked', async () => {
      // Arrange
      const user = userEvent.setup();
      render(<ConfigurationPanel {...defaultProps} />);

      // Act
      await user.click(screen.getByText('Browse All'));

      // Assert
      await waitFor(() => {
        expect(screen.getByTestId('provider-panel')).toBeInTheDocument();
      });
    });

    it('should hide provider panel when back is clicked', async () => {
      // Arrange
      const user = userEvent.setup();
      render(<ConfigurationPanel {...defaultProps} />);
      await user.click(screen.getByText('Browse All'));
      await waitFor(() => {
        expect(screen.getByTestId('provider-panel')).toBeInTheDocument();
      });

      // Act
      await user.click(screen.getByRole('button', { name: 'Back' }));

      // Assert
      await waitFor(() => {
        expect(screen.queryByTestId('provider-panel')).not.toBeInTheDocument();
      });
    });
  });

  describe('Voice Selection', () => {
    it('should not show voice selector when no provider selected', () => {
      // Arrange & Act
      render(<ConfigurationPanel {...defaultProps} />);

      // Assert
      expect(screen.queryByTestId('voice-selector')).not.toBeInTheDocument();
    });

    it('should show voice selector when provider is selected', () => {
      // Arrange
      vi.mocked(useConfiguration).mockReturnValue({
        selectedProvider: 'openai',
        selectedVoice: null,
        currentConfig: {},
      });

      // Act
      render(<ConfigurationPanel {...defaultProps} />);

      // Assert
      expect(screen.getByTestId('voice-selector')).toBeInTheDocument();
    });

    it('should call onVoiceSelect when voice is selected', async () => {
      // Arrange
      vi.mocked(useConfiguration).mockReturnValue({
        selectedProvider: 'openai',
        selectedVoice: null,
        currentConfig: {},
      });
      const user = userEvent.setup();
      render(<ConfigurationPanel {...defaultProps} />);

      // Act
      await user.click(screen.getByText('Select Voice'));

      // Assert
      expect(defaultProps.onVoiceSelect).toHaveBeenCalledWith(TEST_VOICES[0]);
    });
  });

  describe('Configuration Form', () => {
    it('should show config form when provider is selected', async () => {
      // Arrange
      vi.mocked(useConfiguration).mockReturnValue({
        selectedProvider: 'openai',
        selectedVoice: null,
        currentConfig: {},
      });

      // Act
      render(<ConfigurationPanel {...defaultProps} />);

      // Assert
      expect(screen.getByTestId('config-form')).toBeInTheDocument();
    });

    it('should call onConfigChange when config is updated', async () => {
      // Arrange
      vi.mocked(useConfiguration).mockReturnValue({
        selectedProvider: 'openai',
        selectedVoice: null,
        currentConfig: {},
      });
      const user = userEvent.setup();
      render(<ConfigurationPanel {...defaultProps} />);

      // Act
      const speedInput = screen.getByTestId('speed-input');
      await user.clear(speedInput);
      await user.type(speedInput, '1.5');

      // Assert
      expect(defaultProps.onConfigChange).toHaveBeenCalledWith({
        speed: '1.5',
      });
    });

    it('should show reset button when provider is selected', async () => {
      // Arrange
      vi.mocked(useConfiguration).mockReturnValue({
        selectedProvider: 'openai',
        selectedVoice: null,
        currentConfig: {},
      });

      // Act
      render(<ConfigurationPanel {...defaultProps} />);

      // Assert
      expect(screen.getByText('Reset to defaults')).toBeInTheDocument();
    });

    it('should reset config when reset button is clicked', async () => {
      // Arrange
      vi.mocked(useConfiguration).mockReturnValue({
        selectedProvider: 'openai',
        selectedVoice: null,
        currentConfig: {},
      });
      const user = userEvent.setup();
      render(<ConfigurationPanel {...defaultProps} />);

      // Act
      await user.click(screen.getByText('Reset to defaults'));

      // Assert
      expect(defaultProps.onConfigChange).toHaveBeenCalledWith({});
    });
  });

  describe('History Tab', () => {
    it('should show history details when task is selected', async () => {
      // Arrange
      const user = userEvent.setup();
      render(<ConfigurationPanel {...defaultProps} />);

      // Switch to history tab
      await user.click(screen.getByRole('tab', { name: 'History' }));

      // Act
      await user.click(screen.getByText('Task 123'));

      // Assert
      await waitFor(() => {
        expect(screen.getByTestId('history-details')).toBeInTheDocument();
        expect(screen.getByText('Task: 123')).toBeInTheDocument();
      });
    });

    it('should go back to history list when back is clicked', async () => {
      // Arrange
      const user = userEvent.setup();
      render(<ConfigurationPanel {...defaultProps} />);

      // Switch to history tab and select a task
      await user.click(screen.getByRole('tab', { name: 'History' }));
      await user.click(screen.getByText('Task 123'));

      await waitFor(() => {
        expect(screen.getByTestId('history-details')).toBeInTheDocument();
      });

      // Act
      const backButtons = screen.getAllByRole('button', { name: 'Back' });
      await user.click(backButtons[backButtons.length - 1]); // Click the last back button

      // Assert
      await waitFor(() => {
        expect(screen.queryByTestId('history-details')).not.toBeInTheDocument();
        expect(screen.getByTestId('history-tab')).toBeInTheDocument();
      });
    });
  });

  describe('Panel Transitions', () => {
    it('should handle transitions smoothly', async () => {
      // Arrange
      const user = userEvent.setup();
      render(<ConfigurationPanel {...defaultProps} />);

      // Act - trigger multiple transitions quickly
      await user.click(screen.getByText('Browse All'));

      // Immediately click back before transition completes
      const backButton = await screen.findByRole('button', { name: 'Back' });
      await user.click(backButton);

      // Assert - should handle rapid transitions without errors
      await waitFor(() => {
        expect(screen.getByTestId('provider-selector')).toBeInTheDocument();
      });
    });
  });
});
