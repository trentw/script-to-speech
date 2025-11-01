import { createFileRoute, Outlet, useLocation } from '@tanstack/react-router';
import { motion } from 'framer-motion';
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
  const location = useLocation();
  const pageVariants = {
    initial: { opacity: 0, x: -20 },
    animate: { opacity: 1, x: 0 },
  };

  return (
    <motion.div
      key={location.pathname}
      initial="initial"
      animate="animate"
      variants={pageVariants}
      transition={{ duration: 0.3, ease: 'easeInOut' }}
    >
      <Outlet />
    </motion.div>
  );
}
