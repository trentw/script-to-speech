import type { LinkOptions } from '@tanstack/react-router';
import { motion } from 'framer-motion';
import { PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import React, { useMemo } from 'react';

import { ManualModeNavigation } from '@/components/navigation/ManualModeNavigation';
import { ProjectModeNavigation } from '@/components/navigation/ProjectModeNavigation';
import { ManualModeToggle } from '@/components/project/ManualModeToggle';
import { ProjectControls } from '@/components/project/ProjectControls';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
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
        {/* Header with Project Controls */}
        <div
          className={cn(
            'border-border relative flex flex-col border-b bg-white',
            isExpanded ? 'space-y-3 p-4' : 'items-center justify-center p-2'
          )}
        >
          {isExpanded ? (
            <div className="flex items-center justify-between">
              {/* Project Controls */}
              <div className="flex-1">
                <ProjectControls
                  onProjectSelect={handleProjectSelect}
                  onError={handleModeError}
                />
              </div>

              {/* Toggle button when expanded */}
              {onToggleExpanded && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={onToggleExpanded}
                      className="ml-2 flex-shrink-0 hover:bg-gray-100 hover:shadow-md active:scale-95 active:shadow-inner"
                      aria-label="Collapse sidebar"
                    >
                      <PanelLeftClose className="h-4 w-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="right">Collapse sidebar</TooltipContent>
                </Tooltip>
              )}
            </div>
          ) : (
            /* Toggle button when collapsed - centered */
            onToggleExpanded && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={onToggleExpanded}
                    className="hover:bg-gray-100 hover:shadow-md active:scale-95 active:shadow-inner"
                    aria-label="Expand sidebar"
                  >
                    <PanelLeftOpen className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="right">Expand sidebar</TooltipContent>
              </Tooltip>
            )
          )}
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

          {/* Manual Mode Toggle */}
          {isExpanded && (
            <div className="mb-4">
              <ManualModeToggle />
            </div>
          )}

          {/* Version Info and Debug Controls */}
          <div
            className={cn(
              'flex flex-col gap-2',
              !isExpanded && 'w-0 overflow-hidden opacity-0'
            )}
          >
            {/* Version */}
            <p className="text-muted-foreground text-xs whitespace-nowrap">
              v{__APP_VERSION__}
            </p>
          </div>
        </div>
      </motion.nav>
    </>
  );
}

export default AdaptiveNavigation;
