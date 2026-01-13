import {
  createRootRouteWithContext,
  Outlet,
  useNavigate,
  useRouterState,
  useSearch,
} from '@tanstack/react-router';
import { useEffect } from 'react';

import { RouteError } from '@/components/errors';
import { Toaster } from '@/components/ui/sonner';
import type { SettingsSection } from '@/stores/appStore';

import { ErrorDisplay } from '../components/app/ErrorDisplay';
import { FooterContent } from '../components/app/FooterContent';
import { HeaderContent } from '../components/app/HeaderContent';
import { HistoryContent } from '../components/app/HistoryContent';
import { PanelContent } from '../components/app/PanelContent';
import { SettingsContent } from '../components/app/SettingsContent';
import {
  AdaptiveNavigation,
  AppShell,
  MobileDrawer,
  ResponsivePanel,
} from '../components/layout';
import { UploadProgressDialog } from '../components/project/UploadProgressDialog';
import { SettingsDialog } from '../components/settings/SettingsDialog';
import { useAllVoiceCounts } from '../hooks/queries/useAllVoiceCounts';
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

// Search params type for settings deep linking
type RootSearchParams = {
  settings?: SettingsSection;
};

// Valid settings sections for URL validation
const VALID_SETTINGS_SECTIONS: SettingsSection[] = ['api-keys', 'debug'];

// Create the root route with context
export const Route = createRootRouteWithContext<RouterContext>()({
  component: RootComponent,
  errorComponent: RouteError,
  validateSearch: (search: Record<string, unknown>): RootSearchParams => {
    const settings = search.settings;
    if (
      typeof settings === 'string' &&
      VALID_SETTINGS_SECTIONS.includes(settings as SettingsSection)
    ) {
      return { settings: settings as SettingsSection };
    }
    return {};
  },
});

function RootComponent() {
  // Hooks
  const { isMobile } = useViewportSize();
  const routerState = useRouterState();
  const navigate = useNavigate();
  const { settings: settingsParam } = useSearch({ from: '__root__' });

  // Use Layout state for responsive behavior
  const {
    sidebarExpanded,
    activeModal,
    toggleSidebar,
    openSettings,
    closeModal,
  } = useLayout();

  // Bidirectional sync between URL search params and store
  // 1. URL -> Store: Open settings when URL has settings param
  useEffect(() => {
    if (settingsParam && activeModal?.type !== 'settings') {
      openSettings(settingsParam);
    }
  }, [settingsParam, activeModal, openSettings]);

  // 2. Store -> URL: Update URL when settings modal closes
  useEffect(() => {
    // If settings modal was closed but URL still has settings param, clear it
    if (activeModal?.type !== 'settings' && settingsParam) {
      navigate({ search: {}, replace: true });
    }
  }, [activeModal, settingsParam, navigate]);

  // Use Screenplay state
  const { resetScreenplayState } = useScreenplay();

  // Get current pathname to determine active view
  // With TanStack Router hash history, the route is in the pathname
  const pathname = routerState.location.pathname;
  const activeView = pathname.includes('screenplay') ? 'screenplay' : 'tts';

  // Get current route's staticData for UI flags
  const currentMatch = routerState.matches[routerState.matches.length - 1];
  const currentStaticData = currentMatch?.staticData as
    | RouteStaticData
    | undefined;

  // Use Screenplay state to get the current view mode
  const { viewMode: screenplayViewMode } = useScreenplay();

  // Use Zustand store hooks for client state
  const {
    selectedProvider,
    setSelectedProvider,
    setSelectedVoice,
    setCurrentConfig,
  } = useConfiguration();
  const { clearError } = useUIState();

  // Use TanStack Query hooks for server state
  // Note: Queries are paused by onlineManager until backend is ready,
  // so we don't need to handle startup errors here.
  const { data: providers, isPending: providersLoading } = useProviders();
  const { data: voiceLibraryData } = useVoiceLibrary(selectedProvider || '');

  // Get voice counts for all providers dynamically
  const { voiceCounts, providerErrors } = useAllVoiceCounts(providers || []);

  // Adapt voice library data to expected format
  const voiceLibrary: Record<string, VoiceEntry[]> =
    selectedProvider && voiceLibraryData
      ? { [selectedProvider]: voiceLibraryData }
      : {};

  // Navigation items are now generated at module level in AdaptiveNavigation

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

  // Backend status checks are now handled by BackendGate in App.tsx
  // This component can assume backend is ready

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
        footer={
          currentStaticData?.ui?.showFooter ? <FooterContent /> : undefined
        }
      />

      {/* Mobile Drawers - only show if configured in route staticData */}
      {isMobile &&
        currentStaticData?.ui?.mobileDrawers?.includes('settings') && (
          <MobileDrawer
            title="Settings"
            isOpen={activeModal?.type === 'settings'}
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

      {isMobile &&
        currentStaticData?.ui?.mobileDrawers?.includes('history') && (
          <MobileDrawer
            title="History"
            isOpen={activeModal?.type === 'history'}
            onClose={closeModal}
          >
            <HistoryContent />
          </MobileDrawer>
        )}

      {/* Settings Dialog - works on all platforms */}
      <SettingsDialog />

      {/* Upload Progress Dialog - global dialog for screenplay upload feedback */}
      <UploadProgressDialog />

      <ErrorDisplay />
      <Toaster />
    </>
  );
}
