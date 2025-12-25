import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render as rtlRender, RenderOptions } from '@testing-library/react';
import React, { ReactElement } from 'react';

interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  // Future support for preloaded Zustand state
  preloadedState?: Record<string, unknown>;
}

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: Infinity,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

function customRender(
  ui: ReactElement,
  options?: CustomRenderOptions
): ReturnType<typeof rtlRender> {
  const { preloadedState: _preloadedState, ...renderOptions } = options || {};

  const queryClient = createTestQueryClient();

  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  }

  return rtlRender(ui, { wrapper: Wrapper, ...renderOptions });
}

// Re-export everything from @testing-library/react
export * from '@testing-library/react';

// Override the render method with our custom one
export { customRender as render };

// Export wrapper creator for use with renderHook
export function createWrapper(queryClient?: QueryClient) {
  const client = queryClient || createTestQueryClient();

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
}
