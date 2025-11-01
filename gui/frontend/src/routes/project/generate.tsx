import { createFileRoute, Navigate } from '@tanstack/react-router';
import { Link } from '@tanstack/react-router';
import {
  AlertCircle,
  ArrowLeft,
  Cpu,
  HardDrive,
  Music,
  Play,
  RefreshCw,
  Volume2,
  Zap,
} from 'lucide-react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
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

export const Route = createFileRoute('/project/generate')({
  component: ProjectAudioGeneration,
  staticData,
});

function ProjectAudioGeneration() {
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
          <h1 className="text-3xl font-bold tracking-tight">Generate Audio</h1>
          <Badge variant="secondary">Coming Soon</Badge>
        </div>
        <p className="text-muted-foreground mt-2">
          Generate the final multi-voiced audiobook from your screenplay and
          voice casting.
        </p>
      </div>

      {/* Coming Soon Content */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Volume2 className="h-5 w-5" />
            Audio Generation for {store.project.screenplayName}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="py-8 text-center">
            <Play className="text-muted-foreground mx-auto mb-4 h-12 w-12" />
            <h3 className="mb-2 text-lg font-semibold">Feature Coming Soon</h3>
            <p className="text-muted-foreground mx-auto max-w-md">
              Audio generation will convert your cast screenplay into a complete
              audiobook with multi-threaded TTS processing and intelligent
              caching.
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
              <Cpu className="h-5 w-5" />
              Multi-Threaded Processing
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground mb-4 text-sm">
              Parallel audio generation using separate thread pools for each TTS
              provider, dramatically reducing generation time for long
              screenplays.
            </p>
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <Zap className="h-4 w-4 text-yellow-500" />
                <span className="text-sm">
                  <strong>10x faster</strong> generation with concurrent
                  processing
                </span>
              </div>
              <div className="flex items-center gap-3">
                <RefreshCw className="h-4 w-4 text-blue-500" />
                <span className="text-sm">
                  Automatic retry on API failures with exponential backoff
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <HardDrive className="h-5 w-5" />
              Smart Caching System
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground mb-4 text-sm">
              Intelligent caching based on content hash, speaker, and voice
              configuration. Resume generation exactly where you left off, even
              after interruptions.
            </p>
            <div className="bg-muted rounded-md p-3">
              <div className="space-y-1 font-mono text-xs">
                <div className="text-green-600"># Cache structure</div>
                <div>output/my_screenplay/cache/</div>
                <div className="pl-4">├── alice_echo_a7b9c2.mp3</div>
                <div className="pl-4">├── bob_onyx_f3d4e1.mp3</div>
                <div className="pl-4">└── narrator_nova_8c2a9f.mp3</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Music className="h-5 w-5" />
              Audio Post-Processing
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground mb-4 text-sm">
              Automatic audio concatenation with intelligent silence detection
              and ID3 metadata.
            </p>
            <ul className="space-y-2 text-sm">
              <li className="flex items-start gap-2">
                <span className="text-muted-foreground">•</span>
                <div>
                  <strong>Silence Removal:</strong> Trim excessive pauses
                  between dialogue
                </div>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-muted-foreground">•</span>
                <div>
                  <strong>Chapter Markers:</strong> Add scene-based chapter
                  points
                </div>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-muted-foreground">•</span>
                <div>
                  <strong>ID3 Tags:</strong> Title, author, genre, and cover art
                  metadata
                </div>
              </li>
            </ul>
          </CardContent>
        </Card>

        {/* Progress Example (Mock) */}
        <Card className="opacity-60">
          <CardHeader>
            <CardTitle>Generation Progress (Preview)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <div className="mb-2 flex justify-between text-sm">
                  <span>Overall Progress</span>
                  <span className="text-muted-foreground">
                    234 / 512 chunks
                  </span>
                </div>
                <Progress value={45} className="h-2" />
              </div>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-muted-foreground">Time Elapsed:</span>
                  <span className="ml-2">12:34</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Est. Remaining:</span>
                  <span className="ml-2">15:20</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Cache Hits:</span>
                  <span className="ml-2 text-green-600">89 (34%)</span>
                </div>
                <div>
                  <span className="text-muted-foreground">API Calls:</span>
                  <span className="ml-2">145</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            <strong>Available via CLI:</strong> Audio generation is currently
            available through the command line using{' '}
            <code className="bg-muted mx-1 rounded px-1 py-0.5 text-xs">
              sts-generate-audio
            </code>
            . The GUI will provide real-time progress tracking, error recovery,
            and a more intuitive generation experience.
          </AlertDescription>
        </Alert>
      </div>
    </div>
  );
}
