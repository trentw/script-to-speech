import { createFileRoute, Navigate } from '@tanstack/react-router';

import { TextProcessorPipelineEditor } from '@/components/text-processing/TextProcessorPipelineEditor';
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

export const Route = createFileRoute('/project/processing')({
  component: ProjectTextProcessing,
  staticData,
});

function ProjectTextProcessing() {
  const projectState = useProject();

  // Type guard and redirect if not in project mode
  if (projectState.mode !== 'project') {
    return <Navigate to="/" replace />;
  }

  const inputPath = projectState.project?.inputPath;

  return (
    <div className="container mx-auto max-w-4xl px-6 py-8">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold tracking-tight">Text Processing</h1>
        <p className="text-muted-foreground mt-2">
          Customize how your screenplay's text is transformed before audio
          generation. Changes are saved to this project's config file and used
          by both the app and the CLI.
        </p>
      </div>

      {inputPath ? (
        <TextProcessorPipelineEditor inputPath={inputPath} />
      ) : (
        <p className="text-muted-foreground">
          Select or create a project first.
        </p>
      )}
    </div>
  );
}
