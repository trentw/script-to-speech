import { useRouterState } from '@tanstack/react-router';
import { Plus } from 'lucide-react';

import { useViewportSize } from '../../hooks/useViewportSize';
import { useLayout } from '../../stores/appStore';
import type { RouteStaticData } from '../../types/route-metadata';
import { AppHeader } from '../layout/AppHeader';
import { appButtonVariants } from '../ui/button-variants';

interface HeaderContentProps {
  activeView: 'tts' | 'screenplay';
  onParseNew?: () => void;
  showParseNewButton?: boolean;
}

export const HeaderContent = ({
  activeView,
  onParseNew,
  showParseNewButton,
}: HeaderContentProps) => {
  const { isMobile } = useViewportSize();
  const { toggleSidebar, setActiveModal } = useLayout();
  const routerState = useRouterState();

  // Get title from current route's staticData, checking parent routes if needed
  const getRouteTitle = (): string => {
    // Walk backwards through the route matches to find the first available title
    for (let i = routerState.matches.length - 1; i >= 0; i--) {
      const match = routerState.matches[i];
      const staticData = match?.staticData as RouteStaticData | undefined;
      if (staticData?.title) {
        return staticData.title;
      }
    }
    // Fall back to default if no route has a title
    return 'Script to Speech';
  };
  
  const appName = getRouteTitle();
  const subAppName = '';

  // Only show action buttons on mobile for TTS view
  const showActionButtons = isMobile && activeView === 'tts';

  return (
    <AppHeader
      appName={appName}
      subAppName={subAppName}
      showNavToggle={true}
      onNavToggle={toggleSidebar}
      onSettingsClick={
        showActionButtons ? () => setActiveModal('settings') : undefined
      }
      onHistoryClick={
        showActionButtons ? () => setActiveModal('history') : undefined
      }
      showActionButtons={showActionButtons}
    >
      {/* Parse New Screenplay Button - Right aligned */}
      {activeView === 'screenplay' && showParseNewButton && onParseNew && (
        <button
          className={
            appButtonVariants({ variant: 'primary', size: 'sm' }) + ' mr-4'
          }
          onClick={onParseNew}
        >
          <Plus className="mr-2 h-4 w-4" />
          Parse New Screenplay
        </button>
      )}
    </AppHeader>
  );
};
