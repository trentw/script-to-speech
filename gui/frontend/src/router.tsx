import { QueryClient } from '@tanstack/react-query';
import { createHashHistory, createRouter } from '@tanstack/react-router';

import { routeTree } from './routeTree.gen';

export interface RouterContext {
  queryClient: QueryClient;
  // Add specific configuration for QueryClient if needed
  queryDefaults?: {
    queries?: {
      staleTime?: number;
      gcTime?: number;
      refetchOnWindowFocus?: boolean;
    };
    mutations?: {
      retry?: number;
    };
  };
}

// Create a single history instance to prevent recreation
const hashHistory = createHashHistory();

export function createAppRouter(queryClient: QueryClient) {
  // Use hash-based routing for Tauri desktop compatibility
  // Hash routing (e.g., #/tts, #/screenplay) is required because:
  // 1. Tauri serves the app via file:// protocol
  // 2. Regular browser routing would fail without a server
  // 3. Hash routing works reliably across all platforms

  const router = createRouter({
    routeTree,
    history: hashHistory,
    defaultPreload: 'intent',
    context: {
      queryClient,
    },
  });

  return router;
}

// Register the router instance in your TypeScript types
declare module '@tanstack/react-router' {
  interface Register {
    router: ReturnType<typeof createAppRouter>;
  }
}
