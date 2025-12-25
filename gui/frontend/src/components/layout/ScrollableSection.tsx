import React from 'react';

import { cn } from '@/lib/utils';

interface ScrollableSectionProps {
  children: React.ReactNode;
  className?: string;
  /**
   * Maximum height for the scrollable area
   * @default '400px'
   */
  maxHeight?: string;
}

/**
 * ScrollableSection provides a container for content that needs
 * its own scroll area within the main content area.
 *
 * Use this sparingly - prefer letting the main content area scroll
 * when possible. Only use for specific UI patterns like long lists
 * within tabs or cards.
 */
export function ScrollableSection({
  children,
  className,
  maxHeight = '400px',
}: ScrollableSectionProps) {
  return (
    <div
      className={cn(
        'overflow-y-auto',
        'overflow-x-hidden',
        'border-border rounded-md border',
        className
      )}
      style={{ maxHeight }}
    >
      {children}
    </div>
  );
}
