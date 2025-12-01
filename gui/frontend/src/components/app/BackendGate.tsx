import { onlineManager, useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef } from 'react';

import { useBackendStatus } from '@/hooks/queries/useBackendStatus';

import { AppLoading, AppStatus } from './AppStatus';

interface BackendGateProps {
  children: React.ReactNode;
}

/**
 * Backend Gate - Controls app readiness based on backend connection status
 *
 * Key design decisions:
 * 1. RouterProvider stays ALWAYS mounted to preserve TanStack Query cache
 *    during brief disconnections (e.g., dev restarts).
 * 2. Uses onlineManager to pause/resume ALL queries globally when backend
 *    is not ready - no per-query coupling needed.
 * 3. Shows overlay via Portal (in AppStatus/AppLoading) to appear above
 *    all content including Radix dialogs.
 *
 * This prevents jarring unmount/remount cycles and maintains UI state.
 */
export function BackendGate({ children }: BackendGateProps) {
  const { data: backendStatus } = useBackendStatus();
  const queryClient = useQueryClient();
  const wasConnected = useRef(false);

  const isReady = backendStatus?.connected && !backendStatus?.isStarting;

  useEffect(() => {
    // Toggle TanStack Query's online status based on backend readiness
    // When "offline", all queries pause. When "online", they resume/execute.
    onlineManager.setOnline(isReady ?? false);

    // Track connection state for reconnection detection
    if (isReady && !wasConnected.current) {
      // Just connected/reconnected - invalidate queries to fetch fresh data
      queryClient.invalidateQueries();
      wasConnected.current = true;
    } else if (!isReady) {
      wasConnected.current = false;
    }
  }, [isReady, queryClient]);

  // Always render children (keeps router/cache mounted)
  // Show overlay when not ready (rendered via Portal in AppStatus/AppLoading)
  return (
    <>
      {children}
      {(!backendStatus || backendStatus.isStarting) && <AppLoading />}
      {backendStatus &&
        !backendStatus.isStarting &&
        !backendStatus.connected && <AppStatus connected={false} />}
    </>
  );
}
