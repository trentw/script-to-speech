// Re-export everything from render utility
export * from './utils/render';

// Re-export test data
export * from './utils/test-data';

// Re-export store utilities
export { createStore } from './utils/createStore';

// Re-export MSW server for direct use in tests
export { server } from './mocks/server';

// Helper to create wrapper for hooks that need providers
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

export function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
    logger: {
      log: console.log,
      warn: console.warn,
      error: () => {}, // Silence errors in tests
    },
  });

  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}
