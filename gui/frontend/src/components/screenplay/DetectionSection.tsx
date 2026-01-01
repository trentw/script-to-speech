import { Loader2, Search, Settings } from 'lucide-react';
import { useState } from 'react';

import { appButtonVariants } from '@/components/ui/button-variants';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import type { DetectHeadersParams, DetectionResult } from '@/types';

interface DetectionSectionProps {
  pdfPath: string;
  onDetectionComplete: (result: DetectionResult) => void;
  onDetect: (params: DetectHeadersParams) => Promise<DetectionResult>;
  isDetecting: boolean;
}

/**
 * Section for running header/footer detection on a PDF.
 * Includes advanced settings for customizing detection parameters.
 */
export function DetectionSection({
  pdfPath,
  onDetectionComplete,
  onDetect,
  isDetecting,
}: DetectionSectionProps) {
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [linesToScan, setLinesToScan] = useState(2);
  const [threshold, setThreshold] = useState(20);

  const handleDetect = async () => {
    try {
      const result = await onDetect({
        pdfPath,
        linesToScan,
        minOccurrences: undefined, // Let backend auto-calculate
        threshold,
      });
      onDetectionComplete(result);
    } catch (error) {
      console.error('Detection failed:', error);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <Search className="h-5 w-5" />
          Detect Headers/Footers
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-muted-foreground text-sm">
          Scan the PDF for repeating text patterns that appear at the top or
          bottom of pages. These are often page numbers, draft info, or title
          headers that should be removed.
        </p>

        {/* Advanced Settings Toggle */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Settings className="h-4 w-4" />
            <span className="text-sm font-medium">Advanced Settings</span>
          </div>
          <Switch
            checked={showAdvanced}
            onCheckedChange={setShowAdvanced}
            disabled={isDetecting}
          />
        </div>

        {/* Advanced Settings Panel */}
        {showAdvanced && (
          <div className="bg-muted/50 space-y-4 rounded-lg p-4">
            {/* Lines to Scan */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label htmlFor="lines-to-scan">Lines to Check</Label>
                <span className="text-muted-foreground text-sm">
                  {linesToScan}
                </span>
              </div>
              <Slider
                id="lines-to-scan"
                value={[linesToScan]}
                onValueChange={([value]) => setLinesToScan(value)}
                min={1}
                max={10}
                step={1}
                disabled={isDetecting}
              />
              <p className="text-muted-foreground text-xs">
                Number of lines from top/bottom of each page to scan for
                patterns
              </p>
            </div>

            {/* Detection Threshold */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label htmlFor="threshold">Detection Threshold</Label>
                <span className="text-muted-foreground text-sm">
                  {threshold}%
                </span>
              </div>
              <Slider
                id="threshold"
                value={[threshold]}
                onValueChange={([value]) => setThreshold(value)}
                min={10}
                max={100}
                step={5}
                disabled={isDetecting}
              />
              <p className="text-muted-foreground text-xs">
                Minimum percentage of pages a pattern must appear on
              </p>
            </div>
          </div>
        )}

        {/* Detect Button */}
        <button
          onClick={handleDetect}
          disabled={isDetecting}
          className={appButtonVariants({
            variant: 'secondary',
            size: 'default',
          })}
        >
          {isDetecting ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Detecting...
            </>
          ) : (
            <>
              <Search className="mr-2 h-4 w-4" />
              Detect Headers/Footers
            </>
          )}
        </button>
      </CardContent>
    </Card>
  );
}
