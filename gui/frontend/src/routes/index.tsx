import { createFileRoute, redirect } from '@tanstack/react-router';

import { RouteError } from '@/components/errors';

export const Route = createFileRoute('/')({
  errorComponent: RouteError,
  // Redirect to the default TTS view using beforeLoad
  // This is the idiomatic way to handle redirects in TanStack Router
  beforeLoad: () => {
    throw redirect({
      to: '/tts',
    });
  },
});