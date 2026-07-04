import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { render, screen, waitFor } from '@/test/utils/render';
import type {
  TextProcessorConfig,
  TextProcessorRegistry,
} from '@/types/text-processing';

import { TextProcessorPipelineEditor } from '../TextProcessorPipelineEditor';

// The editor guards navigation with useBlocker, which needs a live router;
// tests render the component bare, so stub the hook as idle.
vi.mock('@tanstack/react-router', async (importOriginal) => {
  const actual =
    await importOriginal<typeof import('@tanstack/react-router')>();
  return {
    ...actual,
    useBlocker: vi.fn(() => ({
      status: 'idle',
      current: undefined,
      next: undefined,
      action: undefined,
      proceed: undefined,
      reset: undefined,
    })),
  };
});

vi.mock('../../../services/textProcessorApi', () => {
  return {
    TextProcessorApiError: class TextProcessorApiError extends Error {
      status: number;
      constructor(message: string, status: number) {
        super(message);
        this.status = status;
      }
    },
    textProcessorApi: {
      getRegistry: vi.fn(),
      getConfig: vi.fn(),
      updateConfig: vi.fn(),
      validateEntries: vi.fn(),
      previewConfig: vi.fn(),
      previewDiff: vi.fn(),
      convertConfig: vi.fn(),
      resetConfig: vi.fn(),
      getGlobalDefault: vi.fn(),
      updateGlobalDefault: vi.fn(),
      deleteGlobalDefault: vi.fn(),
    },
  };
});

import { textProcessorApi } from '../../../services/textProcessorApi';

const mockedApi = vi.mocked(textProcessorApi);

const REGISTRY: TextProcessorRegistry = {
  preprocessors: [
    {
      name: 'skip_and_merge',
      kind: 'preprocessor',
      label: 'Skip and Merge',
      description: 'Remove chunks of specific types.',
      multi_config_mode: 'chain',
      schema: {
        label: 'Skip and Merge',
        description: 'Remove chunks of specific types.',
        fields: [
          {
            name: 'skip_types',
            type: 'list',
            required: true,
            label: 'Chunk types to remove',
            item_schema: { type: 'string', suggestions_ref: 'chunk_types' },
          },
        ],
      },
    },
  ],
  processors: [
    {
      name: 'text_substitution',
      kind: 'processor',
      label: 'Text Substitution',
      description: 'Replace exact text.',
      multi_config_mode: 'chain',
      schema: {
        label: 'Text Substitution',
        description: 'Replace exact text.',
        fields: [
          {
            name: 'substitutions',
            type: 'list',
            required: true,
            label: 'Substitutions',
            item_schema: {
              type: 'object',
              fields: [
                {
                  name: 'from',
                  type: 'string',
                  required: true,
                  label: 'Replace',
                },
                { name: 'to', type: 'string', required: true, label: 'With' },
              ],
            },
          },
        ],
      },
    },
  ],
  chunk_types: ['dialogue', 'page_number'],
  chunk_fields: ['type', 'speaker', 'text', 'raw_text'],
};

const CONFIG: TextProcessorConfig = {
  path: '/workspace/input/demo/demo_text_processor_config.yaml',
  yaml_text: 'processors: []\n',
  file_hash: 'hash-1',
  entries: [
    {
      kind: 'preprocessor',
      name: 'skip_and_merge',
      known: true,
      config: { skip_types: ['page_number'] },
      config_yaml: 'skip_types:\n  - page_number\n',
    },
    {
      kind: 'processor',
      name: 'text_substitution',
      known: true,
      config: { substitutions: [{ from: 'INT.', to: 'INTERIOR' }] },
      config_yaml: 'substitutions:\n  - from: INT.\n    to: INTERIOR\n',
    },
    {
      kind: 'processor',
      name: 'my_custom_step',
      known: false,
      config: { anything: true },
      config_yaml: 'anything: true\n',
    },
  ],
  metadata: { mode: 'standalone', seeded_by_version: '2.1.0' },
  stale: false,
  is_legacy_additive: false,
  current_default_hash: 'default-hash',
};

beforeEach(() => {
  vi.clearAllMocks();
  mockedApi.getRegistry.mockResolvedValue(REGISTRY);
  mockedApi.getConfig.mockResolvedValue(CONFIG);
  mockedApi.getGlobalDefault.mockResolvedValue({
    exists: false,
    path: '/workspace/text_processors/configs/user_default.yaml',
  });
  mockedApi.validateEntries.mockResolvedValue({
    valid: true,
    errors: [],
    warnings: [],
  });
});

describe('TextProcessorPipelineEditor', () => {
  it('renders the pipeline entries from the config', async () => {
    const user = userEvent.setup();
    render(<TextProcessorPipelineEditor inputPath="/workspace/input/demo" />);

    expect(await screen.findByText('Text Substitution')).toBeInTheDocument();

    // The Structure section starts collapsed behind the twirl-down
    expect(screen.queryByText('Skip and Merge')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Expand Structure' }));
    expect(await screen.findByText('Skip and Merge')).toBeInTheDocument();
    // Known entries render structured form fields from the schema
    expect(screen.getByText('Chunk types to remove')).toBeInTheDocument();
  });

  it('renders unknown processors with the raw YAML editor', async () => {
    render(<TextProcessorPipelineEditor inputPath="/workspace/input/demo" />);

    const occurrences = await screen.findAllByText('my_custom_step');
    expect(occurrences.length).toBeGreaterThan(0);
    expect(screen.getByText('unknown')).toBeInTheDocument();
    expect(screen.getByDisplayValue(/anything: true/)).toBeInTheDocument();
  });

  it('saves edits with the base file hash for optimistic locking', async () => {
    const user = userEvent.setup();
    mockedApi.updateConfig.mockResolvedValue({
      ...CONFIG,
      file_hash: 'hash-2',
    });

    render(<TextProcessorPipelineEditor inputPath="/workspace/input/demo" />);

    // Make an edit: change a substitution's "Replace" field
    const replaceInput = await screen.findByDisplayValue('INT.');
    await user.clear(replaceInput);
    await user.type(replaceInput, 'EXT.');

    const saveButton = screen.getByRole('button', { name: /save all/i });
    await waitFor(() =>
      expect(saveButton).not.toHaveAttribute('aria-disabled', 'true')
    );
    await user.click(saveButton);

    await waitFor(() => expect(mockedApi.updateConfig).toHaveBeenCalled());
    const [inputPath, entries, baseFileHash] =
      mockedApi.updateConfig.mock.calls[0]!;
    expect(inputPath).toBe('/workspace/input/demo');
    expect(baseFileHash).toBe('hash-1');
    // The edited entry's config became authoritative (config_yaml cleared)
    const edited = entries.find((e) => e.name === 'text_substitution');
    expect(edited?.config_yaml).toBeNull();
  });

  it('commits a single change inline: on-disk entries plus only that edit', async () => {
    const user = userEvent.setup();
    mockedApi.updateConfig.mockImplementation((_inputPath, entries) =>
      Promise.resolve({
        ...CONFIG,
        file_hash: 'hash-2',
        entries: entries.map((e) => ({ ...e })),
      })
    );

    render(<TextProcessorPipelineEditor inputPath="/workspace/input/demo" />);

    const replaceInput = await screen.findByDisplayValue('INT.');
    await user.clear(replaceInput);
    await user.type(replaceInput, 'EXT.');

    // The dirty card exposes an inline commit button
    expect(screen.getByText('modified')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Save this change' }));

    await waitFor(() => expect(mockedApi.updateConfig).toHaveBeenCalled());
    const [, entries, baseFileHash] = mockedApi.updateConfig.mock.calls[0]!;
    expect(baseFileHash).toBe('hash-1');
    expect(entries).toHaveLength(CONFIG.entries.length);
    // Only the committed entry differs from what's on disk
    const committed = entries.find((e) => e.name === 'text_substitution');
    expect(committed?.config).toEqual({
      substitutions: [{ from: 'EXT.', to: 'INTERIOR' }],
    });
    const untouched = entries.find((e) => e.name === 'skip_and_merge');
    expect(untouched?.config_yaml).toBe(CONFIG.entries[0]!.config_yaml);

    // After the commit the entry re-baselines to clean
    await waitFor(() =>
      expect(screen.queryByText('modified')).not.toBeInTheDocument()
    );
  });

  it('returns to a clean state when an edit is reverted by hand', async () => {
    const user = userEvent.setup();

    render(<TextProcessorPipelineEditor inputPath="/workspace/input/demo" />);

    const replaceInput = await screen.findByDisplayValue('INT.');
    await user.clear(replaceInput);
    await user.type(replaceInput, 'EXT.');
    expect(screen.getByText('modified')).toBeInTheDocument();

    await user.clear(replaceInput);
    await user.type(replaceInput, 'INT.');

    await waitFor(() =>
      expect(screen.queryByText('modified')).not.toBeInTheDocument()
    );
    expect(screen.getByRole('button', { name: /save all/i })).toHaveAttribute(
      'aria-disabled',
      'true'
    );
  });
});
