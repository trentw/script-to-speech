import { Plus } from 'lucide-react';

import { useViewportSize } from '../../hooks/useViewportSize';
import { useLayout } from '../../stores/appStore';
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

  // Only show action buttons on mobile for TTS view
  const showActionButtons = isMobile && activeView === 'tts';

  // Set title based on active view
  const appName =
    activeView === 'screenplay' ? 'Screenplay Parser' : 'Text to Speech';
  const subAppName = '';

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
