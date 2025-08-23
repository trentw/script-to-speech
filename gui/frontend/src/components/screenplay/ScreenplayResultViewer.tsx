import { BarChart3, FileCode, FileJson, FileText } from 'lucide-react';

import { appButtonVariants } from '@/components/ui/button-variants';
import { Card } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { apiService } from '@/services/api';
import type { ScreenplayResult } from '@/types';
import { downloadFile } from '@/utils/downloadService';

interface ScreenplayResultViewerProps {
  result: ScreenplayResult | null;
  taskId?: string;
  onDownload?: (type: 'json' | 'text') => void;
}

export function ScreenplayResultViewer({
  result,
  taskId,
}: ScreenplayResultViewerProps) {
  if (!result) return null;

  const { analysis, files, screenplay_name, original_filename, log_file } =
    result;

  const handleDownload = async (fileType: 'json' | 'text' | 'log') => {
    if (!taskId) {
      console.error('Task ID is required for downloading files');
      return;
    }

    // Generate appropriate filename
    const fileExtension =
      fileType === 'log' ? 'log' : fileType === 'json' ? 'json' : 'txt';
    const filename = `${screenplay_name || 'screenplay'}_${fileType}.${fileExtension}`;

    // Get download URL from API service
    const url = apiService.getScreenplayDownloadUrl(taskId, fileType);

    // Use centralized download service
    await downloadFile(url, filename, {
      showDialog: true,
      defaultPath: filename,
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card className="p-6">
        <div className="space-y-4">
          <div>
            <h3 className="text-xl font-semibold">{screenplay_name}</h3>
            <p className="text-muted-foreground mt-1 text-sm">
              Original file: {original_filename}
            </p>
          </div>

          {/* Download buttons on new line */}
          <div className="flex flex-wrap gap-2">
            {files.json && (
              <button
                className={appButtonVariants({
                  variant: 'secondary',
                  size: 'sm',
                })}
                onClick={() => handleDownload('json')}
              >
                <FileJson className="mr-2 h-4 w-4" />
                Download JSON
              </button>
            )}
            {files.text && (
              <button
                className={appButtonVariants({
                  variant: 'secondary',
                  size: 'sm',
                })}
                onClick={() => handleDownload('text')}
              >
                <FileText className="mr-2 h-4 w-4" />
                Download Text
              </button>
            )}
            {log_file && (
              <button
                className={appButtonVariants({
                  variant: 'secondary',
                  size: 'sm',
                })}
                onClick={() => handleDownload('log')}
              >
                <FileCode className="mr-2 h-4 w-4" />
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
            <BarChart3 className="mr-2 h-4 w-4" />
            Statistics
          </TabsTrigger>
          <TabsTrigger value="speakers">Speakers</TabsTrigger>
          <TabsTrigger value="chunks">Chunk Types</TabsTrigger>
        </TabsList>

        <TabsContent value="stats" className="space-y-4">
          <Card className="p-6">
            <h4 className="mb-4 text-lg font-semibold">
              Screenplay Statistics
            </h4>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-muted-foreground text-sm">Total Chunks</p>
                <p className="text-2xl font-bold">{analysis.total_chunks}</p>
              </div>
              <div>
                <p className="text-muted-foreground text-sm">Total Speakers</p>
                <p className="text-2xl font-bold">
                  {analysis.total_distinct_speakers}
                </p>
              </div>
            </div>
          </Card>
        </TabsContent>

        <TabsContent value="speakers" className="space-y-4">
          <Card className="p-6">
            <h4 className="mb-4 text-lg font-semibold">Speaker Line Counts</h4>
            <div className="space-y-2">
              {Object.entries(analysis.speaker_counts)
                .sort(([, a], [, b]) => (b as number) - (a as number))
                .map(([speaker, count]) => (
                  <div
                    key={speaker}
                    className="flex items-center justify-between border-b py-2 last:border-0"
                  >
                    <span className="font-medium">{speaker}</span>
                    <span className="text-muted-foreground text-sm">
                      {count as number} lines
                    </span>
                  </div>
                ))}
            </div>
          </Card>
        </TabsContent>

        <TabsContent value="chunks" className="space-y-4">
          <Card className="p-6">
            <h4 className="mb-4 text-lg font-semibold">
              Chunk Type Distribution
            </h4>
            <div className="space-y-2">
              {Object.entries(analysis.chunk_type_counts)
                .sort(([, a], [, b]) => (b as number) - (a as number))
                .map(([type, count]) => (
                  <div
                    key={type}
                    className="flex items-center justify-between border-b py-2 last:border-0"
                  >
                    <span className="font-medium capitalize">
                      {type.replace('_', ' ')}
                    </span>
                    <span className="text-muted-foreground text-sm">
                      {count as number}
                    </span>
                  </div>
                ))}
            </div>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
