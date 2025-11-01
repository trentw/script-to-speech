import { createFileRoute, Navigate } from '@tanstack/react-router';
import { Link } from '@tanstack/react-router';
import {
  AlertCircle,
  ArrowLeft,
  FileText,
  Hash,
  Settings2,
  Type,
  Wand2,
} from 'lucide-react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
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

  return (
    <div className="container mx-auto max-w-4xl px-6 py-8">
      {/* Header */}
      <div className="mb-6">
        <div className="mb-4 flex items-center gap-4">
          <Button variant="ghost" size="sm" asChild>
            <Link to="/project">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Overview
            </Link>
          </Button>
        </div>

        <div className="flex items-center gap-3">
          <h1 className="text-3xl font-bold tracking-tight">Text Processing</h1>
          <Badge variant="secondary">Coming Soon</Badge>
        </div>
        <p className="text-muted-foreground mt-2">
          Configure text transformations and preprocessing for your screenplay.
        </p>
      </div>

      {/* Coming Soon Content */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings2 className="h-5 w-5" />
            Text Processing Configuration
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="py-8 text-center">
            <Settings2 className="text-muted-foreground mx-auto mb-4 h-12 w-12" />
            <h3 className="mb-2 text-lg font-semibold">Feature Coming Soon</h3>
            <p className="text-muted-foreground mx-auto max-w-md">
              Text processing configuration will allow you to set up custom
              transformations, substitutions, and formatting rules for your
              screenplay before audio generation.
            </p>
            <div className="mt-6">
              <Button asChild>
                <Link to="/project">Return to Overview</Link>
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Detailed Features Preview */}
      <div className="mt-6 grid gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Type className="h-5 w-5" />
              Text Substitutions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground mb-3 text-sm">
              Define custom word and phrase replacements to improve
              pronunciation and consistency.
            </p>
            <div className="bg-muted rounded-md p-3 font-mono text-xs">
              <div className="text-green-600"># Example substitutions</div>
              <div>Dr. → Doctor</div>
              <div>NYC → New York City</div>
              <div>ASAP → as soon as possible</div>
              <div>1984 → nineteen eighty-four</div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Wand2 className="h-5 w-5" />
              Smart Processing
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground mb-3 text-sm">
              Intelligent text transformations that understand screenplay
              context.
            </p>
            <ul className="space-y-2 text-sm">
              <li className="flex items-start gap-2">
                <Hash className="text-muted-foreground mt-0.5 h-4 w-4" />
                <div>
                  <strong>Number Formatting:</strong> Convert numbers to spoken
                  form based on context (years, addresses, phone numbers)
                </div>
              </li>
              <li className="flex items-start gap-2">
                <FileText className="text-muted-foreground mt-0.5 h-4 w-4" />
                <div>
                  <strong>Stage Directions:</strong> Remove or process
                  parenthetical directions like "(sarcastically)" or
                  "(whispering)"
                </div>
              </li>
              <li className="flex items-start gap-2">
                <Settings2 className="text-muted-foreground mt-0.5 h-4 w-4" />
                <div>
                  <strong>Character Rules:</strong> Apply different processing
                  rules per character (accents, speaking styles, vocabulary)
                </div>
              </li>
            </ul>
          </CardContent>
        </Card>

        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            <strong>Available via CLI:</strong> Text processing is currently
            configurable through the command line using{' '}
            <code className="bg-muted mx-1 rounded px-1 py-0.5 text-xs">
              sts-generate-audio --text-processor-config
            </code>
            . The GUI interface will make these powerful features more
            accessible.
          </AlertDescription>
        </Alert>
      </div>
    </div>
  );
}
