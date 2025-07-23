import { createFileRoute, Outlet } from '@tanstack/react-router';
import { FileText } from 'lucide-react';

import { RouteError } from '@/components/errors';
import type { RouteStaticData } from '../../types/route-metadata';

export const Route = createFileRoute('/screenplay')({
  component: ScreenplayLayout,
  errorComponent: RouteError,
  staticData: {
    title: 'Screenplay Parser',
    icon: FileText,
    description: 'Parse screenplay PDFs into structured JSON for multi-voice audio generation',
    navigation: {
      order: 2,
      showInNav: true,
    },
    ui: {
      showPanel: false,
      showFooter: false,
      mobileDrawers: [],
    },
  } satisfies RouteStaticData,
});

function ScreenplayLayout() {
  // This is a layout route that groups all screenplay-related routes together.
  // It doesn't add any visual wrapper - it simply renders child routes through Outlet.
  // Child routes include:
  // - /screenplay (index) - Upload interface
  // - /screenplay/$taskId - Task-specific status/results pages
  return <Outlet />;
}