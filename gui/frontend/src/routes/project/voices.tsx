import { useQuery } from '@tanstack/react-query';
import { createFileRoute, Navigate, useNavigate } from '@tanstack/react-router';
import { Link } from '@tanstack/react-router';
import { AlertCircle, Loader2 } from 'lucide-react';
import { useEffect } from 'react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { API_BASE_URL } from '@/config/api';
import { useProjectStatus } from '@/hooks/queries/useProjectStatus';
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

export const Route = createFileRoute('/project/voices')({
  component: ProjectVoiceCasting,
  staticData,
});

function ProjectVoiceCasting() {
  const projectState = useProject();
  const navigate = useNavigate();

  // Get values before any conditional logic
  const inputPath =
    projectState.mode === 'project'
      ? projectState.project.inputPath
      : undefined;
  const screenplayName =
    projectState.mode === 'project'
      ? projectState.project.screenplayName
      : undefined;

  const {
    status,
    isLoading: statusLoading,
    error: statusError,
  } = useProjectStatus(inputPath);

  // Create or retrieve voice casting session
  const {
    data: session,
    isLoading: sessionLoading,
    error: sessionError,
  } = useQuery({
    queryKey: ['project-voice-session', inputPath, screenplayName],
    queryFn: async () => {
      if (!inputPath || !screenplayName) return null;

      const response = await fetch(
        `${API_BASE_URL}/voice-casting/create-session-from-project`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            input_path: inputPath,
            screenplay_name: screenplayName,
          }),
        }
      );

      if (!response.ok) {
        throw new Error('Failed to create/retrieve session');
      }

      return response.json();
    },
    enabled: !!status?.hasJson && !!inputPath && !!screenplayName,
    refetchOnWindowFocus: true,
    staleTime: 5000,
  });

  // Once we have a session, navigate to the existing voice casting route
  useEffect(() => {
    if (session?.session_id) {
      navigate({
        to: '/voice-casting/$sessionId',
        params: { sessionId: session.session_id },
        replace: true,
      });
    }
  }, [session, navigate]);

  // Type guard and redirect if not in project mode (after all hooks)
  if (projectState.mode !== 'project') {
    return <Navigate to="/" replace />;
  }

  // Error states
  if (statusError || sessionError) {
    return (
      <div className="container mx-auto max-w-4xl px-6 py-8">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Failed to load voice casting:{' '}
            {(statusError || sessionError)?.message}
          </AlertDescription>
        </Alert>
        <Button asChild variant="outline" className="mt-4">
          <Link to="/project">Back to Overview</Link>
        </Button>
      </div>
    );
  }

  // Check if screenplay is parsed
  if (!statusLoading && !status?.hasJson) {
    return (
      <div className="container mx-auto max-w-4xl px-6 py-8">
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Please parse your screenplay first before casting voices.
            <Button asChild variant="link" className="ml-2 h-auto p-0">
              <Link to="/project">Go to Overview</Link>
            </Button>
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  // Loading state while creating/retrieving session
  if (statusLoading || sessionLoading) {
    return (
      <div className="container mx-auto max-w-4xl px-6 py-8">
        <Card>
          <CardContent className="p-12">
            <div className="flex flex-col items-center justify-center space-y-4">
              <Loader2 className="text-muted-foreground h-8 w-8 animate-spin" />
              <p className="text-muted-foreground">
                {sessionLoading
                  ? 'Setting up voice casting session...'
                  : 'Loading project status...'}
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // This should rarely be shown as we redirect immediately when session is created
  return (
    <div className="container mx-auto max-w-4xl px-6 py-8">
      <Card>
        <CardContent className="p-12">
          <div className="flex flex-col items-center justify-center space-y-4">
            <Loader2 className="text-muted-foreground h-8 w-8 animate-spin" />
            <p className="text-muted-foreground">
              Redirecting to voice casting...
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
