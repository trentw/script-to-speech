import React from 'react';

import { cn } from '@/lib/utils';

interface AppShellProps {
  navigation?: React.ReactNode;
  header?: React.ReactNode;
  main: React.ReactNode;
  panel?: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
}

export function AppShell({
  navigation,
  header,
  main,
  panel,
  footer,
  className,
}: AppShellProps) {
  const hasNav = !!navigation;
  const hasPanel = !!panel;

  return (
    <div
      className={cn(
        'app-shell',
        'h-screen overflow-hidden', // Ensure shell is exactly viewport height with no scrolling
        hasNav && 'has-nav',
        hasPanel && 'has-panel',
        className
      )}
    >
      {navigation && (
        <aside className="grid-area-nav border-border bg-background flex flex-col overflow-hidden border-r">
          {navigation}
        </aside>
      )}

      {header && (
        <header className="grid-area-header border-border bg-background flex-shrink-0 border-b">
          {header}
        </header>
      )}

      <main className="grid-area-main overflow-auto">{main}</main>

      {panel && (
        <aside className="grid-area-panel border-border bg-background flex flex-col overflow-hidden border-l">
          {panel}
        </aside>
      )}

      {footer && (
        <footer className="grid-area-footer border-border bg-background flex-shrink-0 border-t">
          {footer}
        </footer>
      )}
    </div>
  );
}
