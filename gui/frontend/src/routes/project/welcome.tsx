import { createFileRoute } from '@tanstack/react-router';

import { ProjectWelcomeScreen } from '@/components/project/ProjectWelcomeScreen';

export const Route = createFileRoute('/project/welcome')({
  component: ProjectWelcomeScreen,
});
