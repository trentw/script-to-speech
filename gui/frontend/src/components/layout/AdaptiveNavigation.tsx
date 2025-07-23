import type { LinkOptions } from '@tanstack/react-router';
import { Link } from '@tanstack/react-router';
import { motion } from 'framer-motion';
import { PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import React, { useMemo } from 'react';

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

  // Generate navigation items dynamically from route metadata (lazy initialization)
  const defaultItems = useMemo(() => buildNavigationItems(), []);
  const navigationItems = items || defaultItems;

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
        {/* Header */}
        <div className="border-border flex items-center justify-between border-b bg-white p-4">
          <h1
            className={cn(
              'overflow-hidden text-lg font-bold whitespace-nowrap',
              !isExpanded && 'w-0 opacity-0'
            )}
          >
            Script to Speech
          </h1>

          {onToggleExpanded && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onToggleExpanded}
              className="h-8 w-8 flex-shrink-0 p-0"
            >
              {isExpanded ? (
                <PanelLeftClose className="h-4 w-4" />
              ) : (
                <PanelLeftOpen className="h-4 w-4" />
              )}
            </Button>
          )}
        </div>

        {/* Navigation Items */}
        <div className="flex-1 space-y-1 bg-white p-2">
          {navigationItems.map((item) => {
            const IconComponent = item.icon;
            const linkContent = (
              <Link
                key={item.id}
                {...item.linkOptions}
                activeProps={{
                  className: 'bg-primary text-primary-foreground hover:bg-primary/90',
                }}
                className={cn(
                  'flex w-full items-center justify-start rounded-md px-3 py-2 text-sm font-medium transition-colors',
                  'hover:bg-accent hover:text-accent-foreground',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
                  !isExpanded && 'px-2'
                )}
              >
                <IconComponent className="h-4 w-4 flex-shrink-0" />
                <span
                  className={cn(
                    'ml-2 overflow-hidden whitespace-nowrap',
                    !isExpanded && 'w-0 opacity-0'
                  )}
                >
                  {item.label}
                </span>
              </Link>
            );

            if (!isExpanded) {
              return (
                <Tooltip key={item.id}>
                  <TooltipTrigger asChild>{linkContent}</TooltipTrigger>
                  <TooltipContent side="right">{item.label}</TooltipContent>
                </Tooltip>
              );
            }

            return linkContent;
          })}
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
