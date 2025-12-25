import React from 'react';

import { cn } from '@/lib/utils';

interface ContentWrapperProps {
  children: React.ReactNode;
  className?: string;
  /**
   * Whether to add padding to the content
   * @default true
   */
  padded?: boolean;
}

/**
 * ContentWrapper provides a standardized container for route content
 * that ensures proper scrolling behavior within the AppShell layout.
 *
 * All route components should wrap their content with this component
 * to maintain consistent layout and prevent content from breaking
 * the fixed header/navigation structure.
 */
export function ContentWrapper({
  children,
  className,
  padded = true,
}: ContentWrapperProps) {
  return (
    <div
      className={cn(
        'h-full w-full',
        'flex flex-col',
        'overflow-x-hidden', // Prevent horizontal scroll
        padded && 'p-6',
        className
      )}
    >
      {children}
    </div>
  );
}
