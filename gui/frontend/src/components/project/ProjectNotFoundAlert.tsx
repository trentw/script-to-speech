import { useNavigate } from '@tanstack/react-router';
import { AlertTriangle, Home } from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { useProject } from '@/stores/appStore';

export function ProjectNotFoundAlert() {
  const navigate = useNavigate();
  const { setMode } = useProject();

  const handleReturnHome = () => {
    setMode('manual');
    navigate({ to: '/', replace: true });
  };

  return (
    <div className="container mx-auto max-w-2xl px-6 py-8">
      <Alert variant="destructive">
        <AlertTriangle className="h-4 w-4" />
        <AlertTitle>Project Not Found</AlertTitle>
        <AlertDescription className="space-y-4">
          <p>
            The project directory could not be found. This might happen if the
            project was moved, deleted, or if there's an issue with the file
            system.
          </p>

          <div className="flex gap-2">
            <Button onClick={handleReturnHome} variant="outline" size="sm">
              <Home className="mr-2 h-4 w-4" />
              Return to Manual Mode
            </Button>
          </div>
        </AlertDescription>
      </Alert>
    </div>
  );
}
