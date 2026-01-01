import { createFileRoute, Navigate } from '@tanstack/react-router';

import { ConfigureParsingView } from '@/components/screenplay/ConfigureParsingView';
import { useProject } from '@/stores/appStore';
import type { RouteStaticData } from '@/types/route-metadata';

// Static metadata for this route
const staticData: RouteStaticData = {
  ui: {
    showPanel: false,
    showFooter: false,
    mobileDrawers: [],
  },
};

export const Route = createFileRoute('/project/screenplay/configure')({
  component: ProjectScreenplayConfigure,
  staticData,
});

function ProjectScreenplayConfigure() {
  const projectState = useProject();

  // Type guard and redirect if not in project mode
  if (projectState.mode !== 'project') {
    return <Navigate to="/" replace />;
  }

  const { project } = projectState;

  // Build the PDF path from project data
  // The PDF should be in the input directory with .pdf extension
  const pdfPath = `${project.inputPath}/${project.screenplayName}.pdf`;

  return (
    <ConfigureParsingView
      inputPath={project.inputPath}
      screenplayName={project.screenplayName}
      pdfPath={pdfPath}
    />
  );
}
