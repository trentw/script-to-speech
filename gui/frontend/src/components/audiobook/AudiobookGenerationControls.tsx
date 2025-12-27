import { Loader2, Play, Settings } from 'lucide-react';
import { useState } from 'react';

import { appButtonVariants } from '@/components/ui/button-variants';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import type {
  AudiobookGenerationMode,
  AudiobookGenerationRequest,
} from '@/types';
import { MODE_DESCRIPTIONS } from '@/types';

interface AudiobookGenerationControlsProps {
  projectName: string;
  inputJsonPath: string;
  voiceConfigPath: string;
  onGenerate: (request: AudiobookGenerationRequest) => void;
  isGenerating: boolean;
  disabled?: boolean;
}

export function AudiobookGenerationControls({
  projectName,
  inputJsonPath,
  voiceConfigPath,
  onGenerate,
  isGenerating,
  disabled = false,
}: AudiobookGenerationControlsProps) {
  const [mode, setMode] = useState<AudiobookGenerationMode>('full');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [silenceCheck, setSilenceCheck] = useState(true);
  const [silenceThreshold, setSilenceThreshold] = useState(-40);
  const [gapMs, setGapMs] = useState(500);
  const [maxWorkers, setMaxWorkers] = useState(12);

  const handleGenerate = () => {
    const request: AudiobookGenerationRequest = {
      projectName,
      inputJsonPath,
      voiceConfigPath,
      mode,
      silenceThreshold: silenceCheck ? silenceThreshold : null,
      gapMs,
      maxWorkers,
    };
    onGenerate(request);
  };

  return (
    <Card className="p-6">
      <div className="space-y-6">
        {/* Mode Selection */}
        <div className="space-y-2">
          <Label htmlFor="generation-mode">Generation Mode</Label>
          <Select
            value={mode}
            onValueChange={(value) => setMode(value as AudiobookGenerationMode)}
            disabled={isGenerating || disabled}
          >
            <SelectTrigger id="generation-mode">
              <SelectValue placeholder="Select mode" />
            </SelectTrigger>
            <SelectContent className="bg-white">
              <SelectItem value="full">Full Generation</SelectItem>
              <SelectItem value="populate-cache">
                Populate Cache Only
              </SelectItem>
              <SelectItem value="dry-run">Dry Run (Plan Only)</SelectItem>
            </SelectContent>
          </Select>
          <p className="text-muted-foreground text-sm">
            {MODE_DESCRIPTIONS[mode]}
          </p>
        </div>

        {/* Advanced Settings Toggle */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Settings className="h-4 w-4" />
            <span className="text-sm font-medium">Advanced Settings</span>
          </div>
          <Switch
            checked={showAdvanced}
            onCheckedChange={setShowAdvanced}
            disabled={isGenerating || disabled}
          />
        </div>

        {/* Advanced Settings Panel */}
        {showAdvanced && (
          <div className="bg-muted/50 space-y-4 rounded-lg p-4">
            {/* Silence Check */}
            <div className="flex items-center justify-between">
              <div>
                <Label htmlFor="silence-check">Check for Silent Clips</Label>
                <p className="text-muted-foreground text-xs">
                  Detect and report clips that are silent
                </p>
              </div>
              <Switch
                id="silence-check"
                checked={silenceCheck}
                onCheckedChange={setSilenceCheck}
                disabled={isGenerating || disabled}
              />
            </div>

            {/* Silence Threshold */}
            {silenceCheck && (
              <div className="space-y-2">
                <Label htmlFor="silence-threshold">
                  Silence Threshold (dBFS)
                </Label>
                <Input
                  id="silence-threshold"
                  type="number"
                  value={silenceThreshold}
                  onChange={(e) => setSilenceThreshold(Number(e.target.value))}
                  min={-60}
                  max={0}
                  disabled={isGenerating || disabled}
                />
                <p className="text-muted-foreground text-xs">
                  Audio below this level is considered silent (default: -40
                  dBFS)
                </p>
              </div>
            )}

            {/* Gap Duration */}
            <div className="space-y-2">
              <Label htmlFor="gap-ms">Gap Between Clips (ms)</Label>
              <Input
                id="gap-ms"
                type="number"
                value={gapMs}
                onChange={(e) => setGapMs(Number(e.target.value))}
                min={0}
                max={5000}
                step={100}
                disabled={isGenerating || disabled}
              />
              <p className="text-muted-foreground text-xs">
                Silence duration between dialogue clips
              </p>
            </div>

            {/* Max Workers */}
            <div className="space-y-2">
              <Label htmlFor="max-workers">Concurrent Workers</Label>
              <Input
                id="max-workers"
                type="number"
                value={maxWorkers}
                onChange={(e) => setMaxWorkers(Number(e.target.value))}
                min={1}
                max={50}
                disabled={isGenerating || disabled}
              />
              <p className="text-muted-foreground text-xs">
                Number of parallel audio generation threads
              </p>
            </div>
          </div>
        )}

        {/* Generate Button */}
        <div className="flex justify-center">
          <button
            onClick={handleGenerate}
            disabled={isGenerating || disabled}
            className={appButtonVariants({
              variant: 'primary',
              size: 'lg',
            })}
          >
            {isGenerating ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Play className="mr-2 h-4 w-4" />
                Generate Audiobook
              </>
            )}
          </button>
        </div>

        {/* Info about what will be generated */}
        <div className="text-muted-foreground text-center text-xs">
          <p>Project: {projectName}</p>
        </div>
      </div>
    </Card>
  );
}
