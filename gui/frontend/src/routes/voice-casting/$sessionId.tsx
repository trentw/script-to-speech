import { createFileRoute, Outlet } from '@tanstack/react-router';

import { RouteError } from '@/components/errors';
import type { RouteStaticData } from '@/types/route-metadata';

export const Route = createFileRoute('/voice-casting/$sessionId')({
  component: VoiceCastingLayout,
  errorComponent: RouteError,
  staticData: {
    title: 'Voice Casting Session',
    description: 'Assign voices to screenplay characters',
    ui: {
      showPanel: false,
      showFooter: false,
      mobileDrawers: [],
    },
  } satisfies RouteStaticData,
});

function VoiceCastingLayout() {
  // This component serves as a layout wrapper
  // The index route handles the main session content
  // Child routes (assign, preview, import, notes, library) render through the outlet
  return <Outlet />;
}
