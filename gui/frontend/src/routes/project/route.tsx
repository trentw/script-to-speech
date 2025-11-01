import {
  createFileRoute,
  Outlet,
  useLocation,
  useNavigate,
} from '@tanstack/react-router';
import { motion } from 'framer-motion';
import { useEffect } from 'react';

import { RouteError } from '@/components/errors';
import { ProjectNotFoundAlert } from '@/components/project/ProjectNotFoundAlert';
import { useProjectStatus } from '@/hooks/queries/useProjectStatus';
import { useProject } from '@/stores/appStore';
import type { ProjectStatus } from '@/types/project';

// Define project route context interface
export interface ProjectRouteContext {
  project: import('@/stores/appStore').ProjectMeta;
  status?: ProjectStatus; // From backend API
}

export const Route = createFileRoute('/project')({
  component: ProjectLayout,
  errorComponent: RouteError,
});

function ProjectLayout() {
  const projectState = useProject();
  const navigate = useNavigate();
  const location = useLocation();

  // Get inputPath before conditional logic (hooks must be called unconditionally)
  const inputPath =
    projectState.mode === 'project'
      ? projectState.project.inputPath
      : undefined;

  // Use the project status hook (must be called unconditionally)
  const { status, error } = useProjectStatus(inputPath);

  // Route guard: Redirect to home if not in project mode
  useEffect(() => {
    if (projectState.mode !== 'project') {
      navigate({ to: '/', replace: true });
    }
  }, [projectState.mode, navigate]);

  // Don't render anything if not in project mode
  if (projectState.mode !== 'project') {
    return null;
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
