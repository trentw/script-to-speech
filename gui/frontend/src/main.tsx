import './index.css';

import { QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { enableMapSet } from 'immer';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import App from './App.tsx';
import { queryClient } from './lib/queryClient';
import { logFeatureFlags } from './lib/featureFlags';

// Enable Map/Set support for immer (required for Zustand store)
enableMapSet();

// Log feature flags in development
logFeatureFlags();

const rootElement = document.getElementById('root');

if (!rootElement) {
  throw new Error(
    "Failed to find the root element. The 'root' div is missing from index.html."
  );
}

// Check if we're in development mode
const isDevelopment = import.meta.env.MODE === 'development';

createRoot(rootElement).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
      {/* React Query DevTools - only in development */}
      {isDevelopment && (
        <ReactQueryDevtools 
          initialIsOpen={false}
          position="bottom-right"
          buttonPosition="bottom-right"
        />
      )}
    </QueryClientProvider>
  </StrictMode>
);
