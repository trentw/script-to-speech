import { AlertTriangle } from 'lucide-react';

import { Badge } from '@/components/ui/badge';

import type { LLMRunVoiceData } from '../../types/voice-editor';

interface LLMPropertyReasoningProps {
  voiceData: LLMRunVoiceData;
}

export function LLMPropertyReasoning({ voiceData }: LLMPropertyReasoningProps) {
  const { flags } = voiceData;

  if (flags.length === 0) return null;

  return (
    <div className="space-y-1.5 rounded-md border border-amber-200 bg-amber-50 p-2">
      <div className="flex items-center gap-1.5">
        <AlertTriangle className="size-3 text-amber-600" />
        <span className="text-xs font-medium text-amber-700">LLM Flags</span>
      </div>
      <div className="flex flex-wrap gap-1">
        {flags.map((flag, i) => (
          <Badge key={i} variant="outline" className="px-1.5 py-0 text-[10px]">
            {flag}
          </Badge>
        ))}
      </div>
    </div>
  );
}
