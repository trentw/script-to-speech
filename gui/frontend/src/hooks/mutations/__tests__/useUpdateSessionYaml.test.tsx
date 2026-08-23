import { QueryClient } from '@tanstack/react-query';
import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { createWrapper } from '@/test/utils/render';

import { useUpdateSessionYaml } from '../useUpdateSessionYaml';

const apiMocks = vi.hoisted(() => ({
  updateSessionYaml: vi.fn(),
}));

vi.mock('@/services/api', () => ({
  apiService: {
    updateSessionYaml: apiMocks.updateSessionYaml,
  },
}));

describe('useUpdateSessionYaml', () => {
  beforeEach(() => {
    apiMocks.updateSessionYaml.mockReset();
    apiMocks.updateSessionYaml.mockResolvedValue({
      data: { session: { screenplay_name: 'demo' }, warnings: [] },
    });
  });

  it("invalidates the project's chunk inventory after the YAML is exported", async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const invalidate = vi.spyOn(queryClient, 'invalidateQueries');
    const { result } = renderHook(() => useUpdateSessionYaml(), {
      wrapper: createWrapper(queryClient),
    });

    await act(async () => {
      await result.current.mutateAsync({
        sessionId: 'session-1',
        yamlContent: 'JOHN:\n  provider: openai\n',
        versionId: 3,
      });
    });

    // Scoped to the session's project - other projects' inventories are
    // expensive server-side recomputes and must not be dropped
    expect(invalidate).toHaveBeenCalledWith({
      queryKey: ['review', 'chunk-inventory', 'demo'],
    });
  });
});
