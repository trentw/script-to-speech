import type { LinkOptions } from '@tanstack/react-router';
import { Link } from '@tanstack/react-router';
import React, { useMemo } from 'react';

import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { type RouteIds } from '@/lib/navigation';
import { buildNavigationItems } from '@/lib/navigation-builder';
import { cn } from '@/lib/utils';

interface NavigationItem {
  id: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  linkOptions: LinkOptions<RouteIds, string>;
}

interface ManualModeNavigationProps {
  items?: NavigationItem[];
  isExpanded?: boolean;
  className?: string;
}

export function ManualModeNavigation({
  items,
  isExpanded = true,
  className,
}: ManualModeNavigationProps) {
  // Generate navigation items dynamically from route metadata (lazy initialization)
  const defaultItems = useMemo(() => buildNavigationItems(), []);
  const navigationItems = items || defaultItems;

  return (
    <div className={cn('space-y-1', className)}>
      {navigationItems.map((item) => {
        const IconComponent = item.icon;
        const linkContent = (
          <Link
            key={item.id}
            {...item.linkOptions}
            activeProps={{
              className: cn(
                // Bold inverted style: black background with white text/icon
                'bg-gray-900 text-white hover:bg-gray-800 shadow-md',
                // Rounded corners for more prominent appearance
                'rounded-lg'
              ),
            }}
            className={cn(
              'flex w-full items-center justify-start rounded-md px-3 py-2 text-sm font-medium transition-colors',
              'hover:bg-accent hover:text-accent-foreground',
              'focus-visible:ring-ring focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none',
              !isExpanded && 'justify-center px-2'
            )}
            aria-label={item.label}
            aria-current={
              item.linkOptions.to === window.location.hash.slice(1)
                ? 'page'
                : undefined
            }
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
  );
}
