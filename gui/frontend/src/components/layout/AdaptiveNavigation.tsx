import { motion } from 'framer-motion';
import { Mic, PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import React from 'react';

import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { useViewportSize } from '@/hooks/useViewportSize';
import { cn } from '@/lib/utils';

interface NavigationItem {
  id: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  onClick?: () => void;
  isActive?: boolean;
}

interface AdaptiveNavigationProps {
  items?: NavigationItem[];
  isExpanded?: boolean;
  onToggleExpanded?: () => void;
  className?: string;
}

const defaultItems: NavigationItem[] = [
  {
    id: 'tts',
    label: 'Text to Speech',
    icon: Mic,
    isActive: true,
  },
];

export function AdaptiveNavigation({
  items = defaultItems,
  isExpanded = true,
  onToggleExpanded,
  className,
}: AdaptiveNavigationProps) {
  const { isMobile, isTablet } = useViewportSize();

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
          {items.map((item) => {
            const IconComponent = item.icon;
            const button = (
              <Button
                key={item.id}
                variant={item.isActive ? 'default' : 'ghost'}
                className={cn('w-full justify-start', !isExpanded && 'px-2')}
                onClick={item.onClick}
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
              </Button>
            );

            if (!isExpanded) {
              return (
                <Tooltip key={item.id}>
                  <TooltipTrigger asChild>{button}</TooltipTrigger>
                  <TooltipContent side="right">{item.label}</TooltipContent>
                </Tooltip>
              );
            }

            return button;
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
