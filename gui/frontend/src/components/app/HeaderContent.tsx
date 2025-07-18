
import { AppHeader } from '../layout/AppHeader';
import { useLayout } from '../../stores/appStore';
import { useViewportSize } from '../../hooks/useViewportSize';

export const HeaderContent = () => {
  const { isMobile } = useViewportSize();
  const { toggleSidebar, setActiveModal } = useLayout();

  const showActionButtons = isMobile; // Only show on mobile when right panel is hidden
  const appName = "Text to Speech";
  const subAppName = "";

  return (
    <AppHeader
      appName={appName}
      subAppName={subAppName}
      showNavToggle={true}
      onNavToggle={toggleSidebar}
      onSettingsClick={showActionButtons ? () => setActiveModal('settings') : undefined}
      onHistoryClick={showActionButtons ? () => setActiveModal('history') : undefined}
      showActionButtons={showActionButtons}
    />
  );
};
