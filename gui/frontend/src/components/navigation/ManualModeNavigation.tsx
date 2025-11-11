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
import { getNavigationItemClassName } from '@/lib/navigation-styles';
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
              className: getNavigationItemClassName({
                isActive: true,
                isCollapsed: !isExpanded,
              }),
            }}
            inactiveProps={{
              className: getNavigationItemClassName({
                isActive: false,
                isCollapsed: !isExpanded,
              }),
            }}
            aria-label={item.label}
            aria-current={
              item.linkOptions.to === window.location.hash.slice(1)
                ? 'page'
                : undefined
            }
          >
            <IconComponent className="h-4 w-4 flex-shrink-0" />
            {isExpanded && (
              <span className="ml-2 overflow-hidden whitespace-nowrap">
                {item.label}
              </span>
            )}
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
