import { AlertTriangle, CircleHelp, Info } from 'lucide-react';
import { useCallback } from 'react';

import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

import type { SchemaPropertyDefinition } from '../../types/voice-editor';

interface VoicePropertySliderProps {
  name: string;
  schema: SchemaPropertyDefinition;
  value: number | undefined;
  onChange: (value: number) => void;
  reasoning?: string;
  warningFlags?: string[];
}

export function VoicePropertySlider({
  name,
  schema,
  value,
  onChange,
  reasoning,
  warningFlags,
}: VoicePropertySliderProps) {
  const displayValue = value ?? 0.5;

  const handleSliderChange = useCallback(
    (values: number[]) => {
      onChange(Math.round(values[0] * 20) / 20); // Round to nearest 0.05
    },
    [onChange]
  );

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const num = parseFloat(e.target.value);
      if (!isNaN(num) && num >= 0 && num <= 1) {
        onChange(Math.round(num * 20) / 20);
      }
    },
    [onChange]
  );

  // Build scale points tooltip
  const scalePointsText = schema.scalePoints
    ? Object.entries(schema.scalePoints)
        .sort(([a], [b]) => parseFloat(a) - parseFloat(b))
        .map(([val, label]) => `${val}: ${label}`)
        .join('\n')
    : null;

  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-1.5">
        <Label className="text-xs font-medium capitalize">{name}</Label>
        {scalePointsText && (
          <TooltipProvider delayDuration={200}>
            <Tooltip>
              <TooltipTrigger asChild>
                <CircleHelp className="text-muted-foreground size-3 cursor-help" />
              </TooltipTrigger>
              <TooltipContent side="right" className="max-w-xs">
                <p className="mb-1 text-xs font-medium">{schema.description}</p>
                <pre className="text-xs whitespace-pre-wrap opacity-80">
                  {scalePointsText}
                </pre>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        )}
        {reasoning && (
          <TooltipProvider delayDuration={200}>
            <Tooltip>
              <TooltipTrigger asChild>
                <Info className="size-3 cursor-help text-blue-500" />
              </TooltipTrigger>
              <TooltipContent side="right" className="max-w-sm">
                <p className="mb-1 text-xs font-medium">LLM Reasoning</p>
                <p className="text-xs opacity-80">{reasoning}</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        )}
        {warningFlags && warningFlags.length > 0 && (
          <TooltipProvider delayDuration={200}>
            <Tooltip>
              <TooltipTrigger asChild>
                <AlertTriangle className="size-3 cursor-help text-amber-500" />
              </TooltipTrigger>
              <TooltipContent side="right" className="max-w-sm">
                <p className="mb-1 text-xs font-medium">LLM Warning</p>
                {warningFlags.map((flag, i) => (
                  <p key={i} className="text-xs opacity-80">
                    {flag}
                  </p>
                ))}
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        )}
      </div>
      <div className="flex items-center gap-3">
        <Slider
          value={[displayValue]}
          min={0}
          max={1}
          step={0.05}
          onValueChange={handleSliderChange}
          className="flex-1"
        />
        <Input
          type="number"
          value={displayValue}
          onChange={handleInputChange}
          min={0}
          max={1}
          step={0.05}
          className="h-7 w-[4.5rem] text-center text-xs tabular-nums"
        />
      </div>
    </div>
  );
}
