import { motion } from 'framer-motion';
import React from 'react';

import { cn } from '@/lib/utils';
import { useLayout } from '@/stores/appStore';
import { motionTokens } from '@/utils/motionTokens';

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
  const { rightPanelExpanded } = useLayout();
  const hasNav = !!navigation;
  const hasPanel = !!panel;

  return (
    <div
      className={cn(
        'app-shell',
        hasNav && 'has-nav',
        hasPanel && 'has-panel',
        className
      )}
    >
      {navigation && (
        <aside className="grid-area-nav border-border bg-background border-r">
          {navigation}
        </aside>
      )}

      {header && (
        <header className="grid-area-header border-border bg-background border-b">
          {header}
        </header>
      )}

      <main className="grid-area-main overflow-hidden">{main}</main>

      {panel && (
        <motion.aside
          className="grid-area-panel border-border bg-muted/30 border-l"
          initial={{ width: rightPanelExpanded ? 500 : 0 }}
          animate={{
            width: rightPanelExpanded ? 500 : 0,
            opacity: rightPanelExpanded ? 1 : 0,
          }}
          transition={{
            ...motionTokens.panelTransition.spring,
            opacity: motionTokens.panelTransition.opacity,
          }}
          style={{ overflow: 'hidden' }}
        >
          {panel}
        </motion.aside>
      )}

      {footer && (
        <footer className="grid-area-footer border-border bg-background border-t">
          {footer}
        </footer>
      )}
    </div>
  );
}
