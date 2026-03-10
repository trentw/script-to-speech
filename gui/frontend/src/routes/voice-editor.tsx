import { createFileRoute } from '@tanstack/react-router';
import { Library } from 'lucide-react';

import { RouteError } from '@/components/errors';

import { VoiceEditorView } from '../components/voice-editor/VoiceEditorView';
import type { RouteStaticData } from '../types/route-metadata';

export const Route = createFileRoute('/voice-editor')({
  component: VoiceEditorView,
  errorComponent: RouteError,
  staticData: {
    title: 'Voice Editor',
    icon: Library,
    description: 'Edit voice library properties, descriptions, and tags',
    navigation: {
      order: 2,
      showInNav: true,
    },
    ui: {
      showPanel: true,
      showFooter: true,
      appSection: 'voice-editor',
    },
  } satisfies RouteStaticData,
});
