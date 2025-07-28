import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { vi } from 'vitest';

import { FieldType } from '@/types';

import { CustomVoiceForm } from '../CustomVoiceForm';

// Mock the hook
vi.mock('@/hooks/queries/useProviderMetadata', () => ({
  useProviderMetadata: vi.fn().mockReturnValue({
    data: {
      identifier: 'openai',
      name: 'OpenAI',
      description: 'OpenAI TTS Provider',
      required_fields: [
        {
          name: 'voice',
          type: FieldType.STRING,
          required: true,
          description: 'OpenAI voice identifier',
          options: ['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'],
        },
      ],
      optional_fields: [],
      max_threads: 5,
    },
    isLoading: false,
    error: null,
  }),
}));

describe('CustomVoiceForm', () => {
  const mockOnConfigChange = vi.fn();
  const mockOnCancel = vi.fn();

  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  const renderComponent = (props = {}) => {
    return render(
      <QueryClientProvider client={queryClient}>
        <CustomVoiceForm
          provider="openai"
          onConfigChange={mockOnConfigChange}
          onCancel={mockOnCancel}
          {...props}
        />
      </QueryClientProvider>
    );
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the form with required fields', async () => {
    renderComponent();

    await waitFor(() => {
      expect(
        screen.getByText('Custom OpenAI Voice Configuration')
      ).toBeInTheDocument();
      expect(screen.getByText('Voice')).toBeInTheDocument();
      expect(screen.getByText('*')).toBeInTheDocument(); // Required indicator
    });
  });

  it('shows validation error for empty required field', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Apply Configuration')).toBeInTheDocument();
    });

    const applyButton = screen.getByText('Apply Configuration');
    fireEvent.click(applyButton);

    await waitFor(() => {
      expect(screen.getByText('This field is required')).toBeInTheDocument();
    });

    expect(mockOnConfigChange).not.toHaveBeenCalled();
  });

  it('calls onConfigChange with valid config', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Voice')).toBeInTheDocument();
    });

    // Open the select dropdown
    const trigger = screen.getByRole('combobox');
    fireEvent.click(trigger);

    // Select a voice
    await waitFor(() => {
      expect(screen.getByText('alloy')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('alloy'));

    // Submit the form
    const applyButton = screen.getByText('Apply Configuration');
    fireEvent.click(applyButton);

    expect(mockOnConfigChange).toHaveBeenCalledWith({ voice: 'alloy' });
  });

  it('calls onCancel when cancel button is clicked', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Cancel')).toBeInTheDocument();
    });

    const cancelButton = screen.getByText('Cancel');
    fireEvent.click(cancelButton);

    expect(mockOnCancel).toHaveBeenCalled();
  });

  it('initializes with current config', async () => {
    renderComponent({ currentConfig: { voice: 'nova' } });

    await waitFor(() => {
      const trigger = screen.getByRole('combobox');
      expect(trigger).toHaveTextContent('nova');
    });
  });
});
