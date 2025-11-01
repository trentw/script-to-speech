import type { LinkOptions } from '@tanstack/react-router';
import { motion } from 'framer-motion';
import { PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import React, { useMemo } from 'react';

import { ManualModeNavigation } from '@/components/navigation/ManualModeNavigation';
import { ProjectModeNavigation } from '@/components/navigation/ProjectModeNavigation';
import { ModeSelector } from '@/components/project/ModeSelector';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { useViewportSize } from '@/hooks/useViewportSize';
import { type RouteIds } from '@/lib/navigation';
import { buildNavigationItems } from '@/lib/navigation-builder';
import { cn } from '@/lib/utils';
import { useProject, useUIState } from '@/stores/appStore';

interface NavigationItem {
  id: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  linkOptions: LinkOptions<RouteIds, string>;
}

interface AdaptiveNavigationProps {
  items?: NavigationItem[];
  isExpanded?: boolean;
  onToggleExpanded?: () => void;
  className?: string;
}

export function AdaptiveNavigation({
  items,
  isExpanded = true,
  onToggleExpanded,
  className,
}: AdaptiveNavigationProps) {
  const { isMobile, isTablet } = useViewportSize();
  const { setError } = useUIState();
  const { mode } = useProject();

  // Generate navigation items dynamically from route metadata (lazy initialization)
  const defaultItems = useMemo(() => buildNavigationItems(), []);
  const navigationItems = items || defaultItems;

  // Handle project selection from ModeSelector
  const handleProjectSelect = (project: {
    inputPath: string;
    screenplayName: string;
  }) => {
    // Could add navigation logic here if needed
    console.log('Project selected:', project);
  };

  // Handle errors from ModeSelector
  const handleModeError = (error: string) => {
    setError(error);
  };

  return (
    <>
      {/* Mobile/Tablet Overlay */}
      {(isMobile || isTablet) && isExpanded && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-40 bg-black/80 backdrop-blur-sm"
          onClick={onToggleExpanded}
        />
      )}

      {/* Desktop/Tablet Navigation */}
      <motion.nav
        key={`nav-${isMobile ? 'mobile' : isTablet ? 'tablet' : 'desktop'}`}
        initial={
          isMobile || isTablet ? { x: -256 } : { width: isExpanded ? 256 : 64 }
        }
        animate={
          isMobile || isTablet
            ? { x: isExpanded ? 0 : -256 }
            : { width: isExpanded ? 256 : 64 }
        }
        exit={isMobile || isTablet ? { x: -256 } : { opacity: 0 }}
        transition={{
          type: 'spring',
          damping: isMobile || isTablet ? 35 : 30,
          stiffness: isMobile || isTablet ? 180 : 200,
        }}
        className={cn(
          'adaptive-navigation',
          'border-border flex h-full flex-col border-r',
          // On mobile/tablet when expanded, position as overlay with solid background
          (isMobile || isTablet) &&
            'border-border fixed inset-y-0 left-0 z-50 w-64 border-r bg-white shadow-lg',
          // Desktop background
          !(isMobile || isTablet) && 'bg-background',
          className
        )}
        style={{
          containerType: 'inline-size',
          containerName: 'navigation',
        }}
      >
        {/* Header with Mode Selector */}
        <div className="border-border flex flex-col space-y-3 border-b bg-white p-4">
          <div className="flex items-center justify-between">
            {/* Mode Selector or collapsed title */}
            <div
              className={cn(
                'flex-1',
                !isExpanded && 'w-0 overflow-hidden opacity-0'
              )}
            >
              {isExpanded && (
                <ModeSelector
                  onProjectSelect={handleProjectSelect}
                  onError={handleModeError}
                />
              )}
            </div>

            {/* Collapsed state title when not expanded */}
            {!isExpanded && (
              <h1 className="text-lg font-bold whitespace-nowrap">STS</h1>
            )}

            {onToggleExpanded && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onToggleExpanded}
                className="ml-2 h-8 w-8 flex-shrink-0 p-0"
              >
                {isExpanded ? (
                  <PanelLeftClose className="h-4 w-4" />
                ) : (
                  <PanelLeftOpen className="h-4 w-4" />
                )}
              </Button>
            )}
          </div>
        </div>

        {/* Navigation Items */}
        <div className="flex-1 bg-white p-2">
          {mode === 'manual' ? (
            <ManualModeNavigation
              items={navigationItems}
              isExpanded={isExpanded}
            />
          ) : (
            <ProjectModeNavigation isExpanded={isExpanded} />
          )}
        </div>

        {/* Footer */}
        <div className="border-border border-t bg-white p-4">
          <Separator className="mb-4" />
          <p
            className={cn(
              'text-muted-foreground overflow-hidden text-xs whitespace-nowrap',
              !isExpanded && 'w-0 opacity-0'
            )}
          >
            v0.1.0
          </p>
        </div>
      </motion.nav>
    </>
  );
}

export default AdaptiveNavigation;
