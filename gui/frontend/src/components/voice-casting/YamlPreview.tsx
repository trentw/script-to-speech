import {
  AlertCircle,
  ArrowLeft,
  Check,
  Copy,
  Download,
  Loader2,
} from 'lucide-react';
import { useState } from 'react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { appButtonVariants } from '@/components/ui/button-variants';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useSessionAssignments } from '@/hooks/queries/useSessionAssignments';
import { downloadText } from '@/utils/downloadService';

interface YamlPreviewProps {
  sessionId: string;
  onBack: () => void;
  onExport?: () => void;
}

export function YamlPreview({ sessionId, onBack, onExport }: YamlPreviewProps) {
  const [copied, setCopied] = useState(false);
  const { data: sessionData, isLoading } = useSessionAssignments(sessionId);

  // Use the existing YAML content from session (source of truth)
  const yamlContent =
    sessionData?.yamlContent || '# No voice assignments configured\n';

  const handleCopy = () => {
    navigator.clipboard.writeText(yamlContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = async () => {
    const filename = `${sessionData?.session.screenplay_name || 'voice_config'}.yaml`;
    await downloadText(yamlContent, filename, 'text/yaml');
  };

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="flex flex-col items-center gap-2">
          <Loader2 className="text-primary h-8 w-8 animate-spin" />
          <span className="text-muted-foreground text-sm">Loading YAML...</span>
        </div>
      </div>
    );
  }

  // Calculate stats
  const stats = {
    totalCharacters: sessionData?.characters?.size || 0,
    assignedCount: sessionData?.assignedCount || 0,
    providers: new Set(
      Array.from(sessionData?.assignments?.values() || [])
        .filter((a) => a.provider)
        .map((a) => a.provider)
    ).size,
  };

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              className={appButtonVariants({
                variant: 'secondary',
                size: 'sm',
              })}
              onClick={onBack}
            >
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back
            </button>
            <div>
              <h1 className="text-lg font-semibold">YAML Configuration</h1>
              <p className="text-muted-foreground text-sm">
                Preview and export voice casting configuration
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleCopy}
              className="gap-2"
            >
              {copied ? (
                <Check className="h-4 w-4" />
              ) : (
                <Copy className="h-4 w-4" />
              )}
              {copied ? 'Copied!' : 'Copy'}
            </Button>
            <Button
              variant="default"
              size="sm"
              onClick={onExport || handleDownload}
              className="gap-2"
            >
              <Download className="h-4 w-4" />
              Download
            </Button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-hidden px-6 py-4">
        <Tabs defaultValue="yaml" className="flex h-full flex-col">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="yaml">YAML</TabsTrigger>
            <TabsTrigger value="summary">Summary</TabsTrigger>
          </TabsList>

          <TabsContent value="yaml" className="mt-4 flex-1 overflow-hidden">
            <Card className="h-full">
              <CardHeader>
                <CardTitle className="text-base">Configuration File</CardTitle>
                <CardDescription>
                  Voice casting configuration in YAML format
                </CardDescription>
              </CardHeader>
              <CardContent className="h-[calc(100%-5rem)]">
                <ScrollArea className="bg-muted/50 h-full rounded-md border p-4">
                  <pre className="text-sm">
                    <code>{yamlContent}</code>
                  </pre>
                </ScrollArea>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="summary" className="mt-4 flex-1 overflow-hidden">
            <div className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">
                    Assignment Summary
                  </CardTitle>
                  <CardDescription>
                    Overview of voice casting configuration
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">
                        Total Characters:
                      </span>
                      <span className="font-medium">
                        {stats.totalCharacters}
                      </span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">
                        Assigned Voices:
                      </span>
                      <span className="font-medium">{stats.assignedCount}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">
                        Voice Providers:
                      </span>
                      <span className="font-medium">{stats.providers}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {stats.assignedCount === 0 && (
                <Alert>
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    No voices have been assigned yet. Go back to assign voices
                    to characters.
                  </AlertDescription>
                </Alert>
              )}
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
