import {
  createFileRoute,
  Outlet,
  redirect,
  useLocation,
} from '@tanstack/react-router';
import { motion } from 'framer-motion';

import { RouteError } from '@/components/errors';
import { ProjectNotFoundAlert } from '@/components/project/ProjectNotFoundAlert';
import { useProjectStatus } from '@/hooks/queries/useProjectStatus';
import useAppStore, { useProject } from '@/stores/appStore';
import type { ProjectStatus } from '@/types/project';

// Define project route context interface
export interface ProjectRouteContext {
  project: import('@/stores/appStore').ProjectMeta | null;
  status?: ProjectStatus; // From backend API
}

export const Route = createFileRoute('/project')({
  component: ProjectLayout,
  errorComponent: RouteError,
  beforeLoad: ({ location }) => {
    // Access Zustand store state synchronously
    const projectState = useAppStore.getState().projectState;

    // Only enforce mode validation when navigating TO project routes
    // Don't interfere when navigating AWAY from project routes
    const isNavigatingToProject = location.pathname.startsWith('/project');
    if (!isNavigatingToProject) {
      return; // Allow leaving project routes without validation
    }

    // Not in project mode - redirect to TTS
    if (projectState.mode !== 'project') {
      throw redirect({ to: '/tts', replace: true });
    }

    // In project mode but no project loaded - only allow /project/welcome
    if (
      projectState.project === null &&
      location.pathname !== '/project/welcome'
    ) {
      throw redirect({ to: '/project/welcome', replace: true });
    }
  },
});

function ProjectLayout() {
  const projectState = useProject();
  const location = useLocation();

  // Get inputPath
  const inputPath =
    projectState.mode === 'project' && projectState.project
      ? projectState.project.inputPath
      : undefined;

  // Use the project status hook
  const { status, error } = useProjectStatus(inputPath);

  // No mode checking needed - beforeLoad handles it
  // Render welcome screen if no project loaded
  if (projectState.project === null) {
    return <Outlet />;
  }

  // Handle project not found (fixed error detection)
  if (error instanceof Error && /not found/i.test(error.message)) {
    return <ProjectNotFoundAlert />;
  }

  // Pass project and status via route context
  const context: ProjectRouteContext = {
    project: projectState.project,
    status,
  };

  // Animation variants matching voice-casting route
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
      <Outlet context={context} />
    </motion.div>
  );
}
