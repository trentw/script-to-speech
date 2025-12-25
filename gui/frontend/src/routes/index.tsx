import { createFileRoute, redirect } from '@tanstack/react-router';

import { RouteError } from '@/components/errors';
import useAppStore from '@/stores/appStore';

export const Route = createFileRoute('/')({
  errorComponent: RouteError,
  // Redirect to project welcome screen and ensure project mode is set
  beforeLoad: () => {
    // Ensure we're in project mode (this sets mode='project', project=null)
    const { projectState, setMode } = useAppStore.getState();
    if (projectState.mode !== 'project') {
      setMode('project');
    }

    // Always go to welcome screen on app start
    throw redirect({ to: '/project/welcome', replace: true });
  },
});
