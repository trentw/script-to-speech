import { FolderOpen, Loader2 } from 'lucide-react';
import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

import { useImportLLMRun } from '../../hooks/mutations/useVoiceEditorMutations';
import { useVoiceEditorStore } from '../../stores/voiceEditorStore';

export function LLMRunImport() {
  const [runDir, setRunDir] = useState('');
  const importMutation = useImportLLMRun();
  const { llmRunData, setLLMRunData, clearLLMRun } = useVoiceEditorStore();

  const handleImport = () => {
    if (!runDir.trim()) return;
    importMutation.mutate(runDir.trim(), {
      onSuccess: (data) => {
        setLLMRunData(data, runDir.trim());
      },
    });
  };

  return (
    <div className="space-y-2 rounded-md border p-3">
      <Label className="text-xs font-medium">LLM Run Import</Label>
      <div className="flex gap-2">
        <Input
          value={runDir}
          onChange={(e) => setRunDir(e.target.value)}
          placeholder="output/llm_labeler_minimax_20260309_..."
          className="h-8 flex-1 text-xs"
        />
        <Button
          size="sm"
          variant="outline"
          onClick={handleImport}
          disabled={!runDir.trim() || importMutation.isPending}
          className="h-8 text-xs"
        >
          {importMutation.isPending ? (
            <Loader2 className="size-3 animate-spin" />
          ) : (
            <FolderOpen className="size-3" />
          )}
          Import
        </Button>
      </div>
      {importMutation.isError && (
        <p className="text-destructive text-xs">
          {importMutation.error.message}
        </p>
      )}
      {llmRunData && (
        <div className="flex items-center justify-between">
          <p className="text-muted-foreground text-xs">
            LLM data loaded: {Object.keys(llmRunData.voices).length} voices (
            {llmRunData.provider})
          </p>
          <Button
            size="sm"
            variant="ghost"
            onClick={clearLLMRun}
            className="h-6 px-2 text-xs"
          >
            Clear
          </Button>
        </div>
      )}
    </div>
  );
}
