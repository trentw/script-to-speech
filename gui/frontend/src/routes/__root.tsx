import { createRootRouteWithContext, Outlet, useNavigate, useRouterState } from '@tanstack/react-router';
import type { AnyRoute } from '@tanstack/react-router';
import { useCallback, useEffect, useState } from 'react';

import { AppLoading, AppStatus } from '../components/app/AppStatus';
import { ErrorDisplay } from '../components/app/ErrorDisplay';
import { FooterContent } from '../components/app/FooterContent';
import { HeaderContent } from '../components/app/HeaderContent';
import { HistoryContent } from '../components/app/HistoryContent';
import { PanelContent } from '../components/app/PanelContent';
import { SettingsContent } from '../components/app/SettingsContent';
import { RouteError } from '@/components/errors';
import {
  AdaptiveNavigation,
  AppShell,
  MobileDrawer,
  ResponsivePanel,
} from '../components/layout';
import { useAllVoiceCounts } from '../hooks/queries/useAllVoiceCounts';
import { useBackendStatus } from '../hooks/queries/useBackendStatus';
import { useProviders } from '../hooks/queries/useProviders';
import { useVoiceLibrary } from '../hooks/queries/useVoiceLibrary';
import { useViewportSize } from '../hooks/useViewportSize';
import type { RouterContext } from '../router';
import {
  useConfiguration,
  useLayout,
  useScreenplay,
  useUIState,
} from '../stores/appStore';
import type { VoiceEntry } from '../types';
import type { RouteStaticData } from '../types/route-metadata';

// Create the root route with context
export const Route = createRootRouteWithContext<RouterContext>()({
  component: RootComponent,
  errorComponent: RouteError,
});

function RootComponent() {
  // Hooks
  const { isMobile } = useViewportSize();
  const routerState = useRouterState();
  const navigate = useNavigate();

  // Use Layout state for responsive behavior
  const { sidebarExpanded, activeModal, toggleSidebar, closeModal } =
    useLayout();

  // Use Screenplay state
  const { resetScreenplayState } = useScreenplay();

  // Get current pathname to determine active view
  // With TanStack Router hash history, the route is in the pathname
  const pathname = routerState.location.pathname;
  const activeView = pathname.includes('screenplay') ? 'screenplay' : 'tts';

  // Get current route's staticData for UI flags
  const currentMatch = routerState.matches[routerState.matches.length - 1];
  const currentStaticData = currentMatch?.staticData as RouteStaticData | undefined;

  // Use Screenplay state to get the current view mode
  const { viewMode: screenplayViewMode } = useScreenplay();

  // Use Zustand store hooks for client state
  const {
    selectedProvider,
    selectedVoice,
    currentConfig,
    setSelectedProvider,
    setSelectedVoice,
    setCurrentConfig,
  } = useConfiguration();
  const { setError, clearError } = useUIState();

  // Use TanStack Query hooks for server state
  const { data: backendStatus } = useBackendStatus();
  const {
    data: providers,
    isPending: providersLoading,
    error: providersError,
  } = useProviders();
  const { data: voiceLibraryData } = useVoiceLibrary(selectedProvider || '');

  // Get voice counts for all providers dynamically
  const { voiceCounts, providerErrors } = useAllVoiceCounts(providers || []);

  // Adapt voice library data to expected format
  const voiceLibrary: Record<string, VoiceEntry[]> =
    selectedProvider && voiceLibraryData
      ? { [selectedProvider]: voiceLibraryData }
      : {};

  // Navigation items are now generated at module level in AdaptiveNavigation

  useEffect(() => {
    if (providersError) {
      setError(providersError.message);
    }
  }, [providersError]);

  const handleProviderChange = (provider: string) => {
    clearError(); // Clear any existing errors
    setSelectedProvider(provider);
    setCurrentConfig({});
    setSelectedVoice(undefined);
  };

  const handleVoiceSelect = (voice: VoiceEntry) => {
    setSelectedVoice(voice);
    setCurrentConfig({ ...voice.config, sts_id: voice.sts_id });
  };

  const handleConfigChange = (config: Record<string, unknown>) => {
    setCurrentConfig(config);
  };

  // Handler for Parse New Screenplay button
  const handleParseNew = () => {
    resetScreenplayState();
    navigate({ to: '/screenplay' });
  };

  if (!backendStatus) {
    return <AppLoading />;
  }

  if (!backendStatus.connected) {
    return <AppStatus connected={false} />;
  }

  return (
    <>
      <AppShell
        navigation={
          <AdaptiveNavigation
            isExpanded={sidebarExpanded}
            onToggleExpanded={toggleSidebar}
          />
        }
        header={
          <HeaderContent
            activeView={activeView}
            onParseNew={handleParseNew}
            showParseNewButton={screenplayViewMode === 'result'}
          />
        }
        main={<Outlet />}
        panel={
          !isMobile && currentStaticData?.ui?.showPanel ? (
            <ResponsivePanel>
              <PanelContent
                providers={providers || []}
                voiceLibrary={voiceLibrary}
                voiceCounts={voiceCounts}
                providerErrors={providerErrors}
                loading={providersLoading}
                onProviderChange={handleProviderChange}
                onVoiceSelect={handleVoiceSelect}
                onConfigChange={handleConfigChange}
              />
            </ResponsivePanel>
          ) : undefined
        }
        footer={currentStaticData?.ui?.showFooter ? <FooterContent /> : undefined}
      />

      {/* Mobile Drawers - only show if configured in route staticData */}
      {isMobile && currentStaticData?.ui?.mobileDrawers?.includes('settings') && (
        <MobileDrawer
          title="Settings"
          isOpen={activeModal === 'settings'}
          onClose={closeModal}
        >
          <SettingsContent
            providers={providers || []}
            voiceLibrary={voiceLibrary}
            voiceCounts={voiceCounts}
            providerErrors={providerErrors}
            loading={providersLoading}
            onProviderChange={handleProviderChange}
            onVoiceSelect={handleVoiceSelect}
            onConfigChange={handleConfigChange}
          />
        </MobileDrawer>
      )}

      {isMobile && currentStaticData?.ui?.mobileDrawers?.includes('history') && (
        <MobileDrawer
          title="History"
          isOpen={activeModal === 'history'}
          onClose={closeModal}
        >
          <HistoryContent />
        </MobileDrawer>
      )}

      <ErrorDisplay />
    </>
  );
}