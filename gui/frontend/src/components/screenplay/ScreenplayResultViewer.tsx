import { Card } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { FileJson, FileText, BarChart3, FileCode } from 'lucide-react';
import { appButtonVariants } from '@/components/ui/button-variants';
import { apiService } from '@/services/api';

interface ScreenplayResultViewerProps {
  result: any;
  taskId?: string;
  onDownload?: (type: 'json' | 'text') => void;
}

export function ScreenplayResultViewer({ result, taskId }: ScreenplayResultViewerProps) {
  if (!result) return null;

  const { analysis, files, screenplay_name, original_filename, log_file } = result;

  const downloadFile = (fileType: 'json' | 'text' | 'log') => {
    if (!taskId) {
      console.error('Task ID is required for downloading files');
      return;
    }
    
    // Create a download link using the centralized API service
    const link = document.createElement('a');
    link.href = apiService.getScreenplayDownloadUrl(taskId, fileType);
    link.target = '_blank'; // Open in new tab to trigger download
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card className="p-6">
        <div className="space-y-4">
          <div>
            <h3 className="text-xl font-semibold">{screenplay_name}</h3>
            <p className="text-sm text-muted-foreground mt-1">
              Original file: {original_filename}
            </p>
          </div>
          
          {/* Download buttons on new line */}
          <div className="flex flex-wrap gap-2">
            {files.json && (
              <button
                className={appButtonVariants({ variant: "secondary", size: "sm" })}
                onClick={() => downloadFile('json')}
              >
                <FileJson className="h-4 w-4 mr-2" />
                Download JSON
              </button>
            )}
            {files.text && (
              <button
                className={appButtonVariants({ variant: "secondary", size: "sm" })}
                onClick={() => downloadFile('text')}
              >
                <FileText className="h-4 w-4 mr-2" />
                Download Text
              </button>
            )}
            {log_file && (
              <button
                className={appButtonVariants({ variant: "secondary", size: "sm" })}
                onClick={() => downloadFile('log')}
              >
                <FileCode className="h-4 w-4 mr-2" />
                Download Logs
              </button>
            )}
          </div>
        </div>
      </Card>

      {/* Analysis Tabs */}
      <Tabs defaultValue="stats" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="stats">
            <BarChart3 className="h-4 w-4 mr-2" />
            Statistics
          </TabsTrigger>
          <TabsTrigger value="speakers">Speakers</TabsTrigger>
          <TabsTrigger value="chunks">Chunk Types</TabsTrigger>
        </TabsList>

        <TabsContent value="stats" className="space-y-4">
          <Card className="p-6">
            <h4 className="text-lg font-semibold mb-4">Screenplay Statistics</h4>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-muted-foreground">Total Chunks</p>
                <p className="text-2xl font-bold">{analysis.total_chunks}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Total Speakers</p>
                <p className="text-2xl font-bold">{analysis.total_distinct_speakers}</p>
              </div>
            </div>
          </Card>
        </TabsContent>

        <TabsContent value="speakers" className="space-y-4">
          <Card className="p-6">
            <h4 className="text-lg font-semibold mb-4">Speaker Line Counts</h4>
            <div className="space-y-2 max-h-[400px] overflow-y-auto pr-2">
              {Object.entries(analysis.speaker_counts)
                .sort(([, a], [, b]) => (b as number) - (a as number))
                .map(([speaker, count]) => (
                  <div key={speaker} className="flex items-center justify-between py-2 border-b last:border-0">
                    <span className="font-medium">{speaker}</span>
                    <span className="text-sm text-muted-foreground">{count as number} lines</span>
                  </div>
                ))}
            </div>
          </Card>
        </TabsContent>

        <TabsContent value="chunks" className="space-y-4">
          <Card className="p-6">
            <h4 className="text-lg font-semibold mb-4">Chunk Type Distribution</h4>
            <div className="space-y-2">
              {Object.entries(analysis.chunk_type_counts)
                .sort(([, a], [, b]) => (b as number) - (a as number))
                .map(([type, count]) => (
                  <div key={type} className="flex items-center justify-between py-2 border-b last:border-0">
                    <span className="font-medium capitalize">{type.replace('_', ' ')}</span>
                    <span className="text-sm text-muted-foreground">{count as number}</span>
                  </div>
                ))}
            </div>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}