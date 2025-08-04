import { createFileRoute, Outlet } from '@tanstack/react-router';
import { Wand2 } from 'lucide-react';

import { RouteError } from '@/components/errors';
import type { RouteStaticData } from '@/types/route-metadata';

export const Route = createFileRoute('/voice-casting')({
  component: VoiceCastingLayout,
  errorComponent: RouteError,
  staticData: {
    title: 'Voice Casting',
    icon: Wand2,
    description: 'Assign voices to screenplay characters',
    navigation: {
      order: 3,
      showInNav: true,
    },
    ui: {
      showPanel: false,
      showFooter: false,
      mobileDrawers: [],
    },
    helpText:
      'Interactively assign TTS provider voices to each character in your screenplay. Preview voices and generate YAML configuration files.',
  } satisfies RouteStaticData,
});

function VoiceCastingLayout() {
  return <Outlet />;
}
