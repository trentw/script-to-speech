import { useEffect } from 'react';

import { useLayout } from '@/stores/appStore';
import { motionTokens } from '@/utils/motionTokens';

const BREAKPOINTS = {
  mobile: 767,
  tablet: 1199,
};

export function useViewportSize() {
  const {
    viewportSize,
    setViewportSize,
    setSidebarExpanded,
    setRightPanelExpanded,
  } = useLayout();

  useEffect(() => {
    function updateViewportSize() {
      const width = window.innerWidth;

      let newSize: 'mobile' | 'tablet' | 'desktop';
      if (width <= BREAKPOINTS.mobile) {
        newSize = 'mobile';
      } else if (width <= BREAKPOINTS.tablet) {
        newSize = 'tablet';
      } else {
        newSize = 'desktop';
      }

      if (newSize !== viewportSize) {
        const previousSize = viewportSize;
        setViewportSize(newSize);

        // Coordinated responsive animations with staggered timing
        // This creates smooth sequences instead of jarring simultaneous changes

        // Auto-close sidebar when switching to mobile/tablet from desktop
        if (
          (newSize === 'mobile' || newSize === 'tablet') &&
          previousSize === 'desktop'
        ) {
          // Grid layout changes immediately (smooth via CSS transitions)
          // Sidebar closes immediately to prevent flash during re-mount
          setSidebarExpanded(false);
        }
        // Auto-open sidebar when switching back to desktop from mobile/tablet
        else if (
          newSize === 'desktop' &&
          (previousSize === 'mobile' || previousSize === 'tablet')
        ) {
          // Stagger sidebar animation to avoid competing with grid layout change
          setTimeout(
            () => setSidebarExpanded(true),
            motionTokens.responsiveSidebar.stagger * 1000
          );
        }

        // Auto-hide right panel when switching to mobile
        if (newSize === 'mobile' && previousSize !== 'mobile') {
          // Right panel closes first, then layout reorganizes
          setRightPanelExpanded(false);
        }
        // Auto-show right panel when switching to desktop/tablet from mobile
        else if (
          (newSize === 'desktop' || newSize === 'tablet') &&
          previousSize === 'mobile'
        ) {
          // Layout reorganizes first, then right panel slides in
          setTimeout(
            () => setRightPanelExpanded(true),
            motionTokens.panelTransition.stagger * 1000
          );
        }
      }
    }

    // Set initial size
    updateViewportSize();

    // Listen for resize events
    window.addEventListener('resize', updateViewportSize);

    // Cleanup
    return () => window.removeEventListener('resize', updateViewportSize);
  }, [
    viewportSize,
    setViewportSize,
    setSidebarExpanded,
    setRightPanelExpanded,
  ]);

  return {
    viewportSize,
    isMobile: viewportSize === 'mobile',
    isTablet: viewportSize === 'tablet',
    isDesktop: viewportSize === 'desktop',
    breakpoints: BREAKPOINTS,
  };
}
