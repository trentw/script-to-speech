import { useNavigate } from '@tanstack/react-router';
import { AlertCircle, Home, RefreshCw, WifiOff } from 'lucide-react';

import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';

interface RouteErrorProps {
  error: Error;
  reset: () => void;
}

export function RouteError({ error, reset }: RouteErrorProps) {
  const navigate = useNavigate();
  const isDevelopment = import.meta.env.DEV;

  // Determine error type and appropriate messaging
  const getErrorInfo = () => {
    const errorMessage = error.message || 'An unexpected error occurred';

    // Check for network errors
    if (
      errorMessage.includes('fetch') ||
      errorMessage.includes('network') ||
      errorMessage.includes('Failed to fetch') ||
      error.name === 'NetworkError'
    ) {
      return {
        icon: WifiOff,
        title: 'Connection Error',
        description:
          'Unable to connect to the server. Please check your internet connection and try again.',
        iconColor: 'text-orange-500',
      };
    }

    // Check for route not found errors
    if (
      errorMessage.includes('route') ||
      errorMessage.includes('404') ||
      error.name === 'NotFoundError'
    ) {
      return {
        icon: AlertCircle,
        title: 'Page Not Found',
        description:
          'The page you are looking for does not exist or has been moved.',
        iconColor: 'text-yellow-500',
      };
    }

    // General JavaScript errors
    return {
      icon: AlertCircle,
      title: 'Something went wrong',
      description:
        'An unexpected error has occurred. Please try refreshing the page or contact support if the problem persists.',
      iconColor: 'text-destructive',
    };
  };

  const errorInfo = getErrorInfo();
  const ErrorIcon = errorInfo.icon;

  const handleGoHome = () => {
    navigate({ to: '/', replace: true });
  };

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="bg-muted mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full">
            <ErrorIcon className={`h-6 w-6 ${errorInfo.iconColor}`} />
          </div>
          <CardTitle className="text-xl">{errorInfo.title}</CardTitle>
          <CardDescription className="mt-2">
            {errorInfo.description}
          </CardDescription>
        </CardHeader>

        {isDevelopment && (
          <CardContent>
            <div className="bg-muted rounded-md p-4">
              <p className="text-muted-foreground mb-2 text-sm font-medium">
                Error Details (Development Mode)
              </p>
              <div className="space-y-1">
                <p className="text-muted-foreground text-xs">
                  <span className="font-medium">Name:</span> {error.name}
                </p>
                <p className="text-muted-foreground text-xs">
                  <span className="font-medium">Message:</span> {error.message}
                </p>
                {error.stack && (
                  <details className="mt-2">
                    <summary className="text-muted-foreground hover:text-foreground cursor-pointer text-xs font-medium">
                      Stack Trace
                    </summary>
                    <pre className="bg-background mt-2 max-h-48 overflow-auto rounded p-2 text-xs">
                      {error.stack}
                    </pre>
                  </details>
                )}
              </div>
            </div>
          </CardContent>
        )}

        <CardFooter className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleGoHome}
            className="flex-1"
          >
            <Home className="mr-2 h-4 w-4" />
            Go Home
          </Button>
          <Button
            variant="default"
            size="sm"
            onClick={reset}
            className="flex-1"
          >
            <RefreshCw className="mr-2 h-4 w-4" />
            Try Again
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}
