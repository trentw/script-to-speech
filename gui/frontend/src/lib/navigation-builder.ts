import type { LinkOptions } from '@tanstack/react-router';
import { FileText, Mic } from 'lucide-react';

import type { RouteIds } from './navigation';

export interface NavigationItem {
  id: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  linkOptions: LinkOptions<RouteIds, string>;
}

/**
 * Builds navigation items for the manual mode navigation
 * These are the main top-level navigation items
 */
export function buildNavigationItems(): NavigationItem[] {
  return [
    {
      id: 'tts',
      label: 'Text to Speech',
      icon: Mic,
      linkOptions: {
        to: '/tts',
      } as LinkOptions<RouteIds, string>,
    },
    {
      id: 'screenplay',
      label: 'Screenplay Parser',
      icon: FileText,
      linkOptions: {
        to: '/screenplay',
      } as LinkOptions<RouteIds, string>,
    },
  ];
}
