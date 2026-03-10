import { AlertTriangle, FolderOpen, Loader2, Play, Search } from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectSeparator,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { apiService } from '@/services/api';
import { useAudioCommands } from '@/services/AudioService';

import { useImportLLMRun } from '../../hooks/mutations/useVoiceEditorMutations';
import {
  useLLMRuns,
  useVoiceLibrary,
  useVoiceLibraryProviders,
} from '../../hooks/queries/useVoiceLibrary';
import { useVoiceEditorStore } from '../../stores/voiceEditorStore';
import { PlayPreviewButton } from '../PlayPreviewButton';
import { UnsavedChangesDialog } from './UnsavedChangesDialog';

const LOAD_RUN_VALUE = '__load_run__';

function parseFlaggedDimensions(flags: string[]): string[] {
  const dims = new Set<string>();
  for (const flag of flags) {
    const match = flag.match(/\w+:(\w+)/);
    if (match) dims.add(match[1]);
  }
  return Array.from(dims);
}

export function VoiceEditorPanel() {
  const { data: providers } = useVoiceLibraryProviders();
  const {
    selectedProvider,
    selectedStsId,
    isDirty,
    llmRunData,
    llmRunDir,
    showLoadRunDialog,
    setSelectedProvider,
    setSelectedStsId,
    setLLMRunData,
    setShowLoadRunDialog,
  } = useVoiceEditorStore();
  const { data: voices } = useVoiceLibrary(selectedProvider ?? '');
  const { data: availableRuns } = useLLMRuns();
  const [searchQuery, setSearchQuery] = useState('');
  const { loadAndPlay } = useAudioCommands();
  const importMutation = useImportLLMRun();

  // Unsaved changes dialog state
  const [pendingStsId, setPendingStsId] = useState<string | null>(null);

  // Load Run dialog state
  const [loadRunDir, setLoadRunDir] = useState('');
  const loadRunInputRef = useRef<HTMLInputElement>(null);
  const [isTauriEnv, setIsTauriEnv] = useState(false);
  useEffect(() => {
    setIsTauriEnv('__TAURI_INTERNALS__' in window);
  }, []);

  // Set of sts_ids that have LLM run data
  const llmVoiceIds = useMemo(() => {
    if (!llmRunData) return new Set<string>();
    return new Set(Object.keys(llmRunData.voices));
  }, [llmRunData]);

  const filteredVoices = useMemo(() => {
    if (!voices) return [];
    if (!searchQuery.trim()) return voices;
    const q = searchQuery.toLowerCase();
    return voices.filter(
      (v) =>
        v.sts_id.toLowerCase().includes(q) ||
        v.description?.provider_name?.toLowerCase().includes(q)
    );
  }, [voices, searchQuery]);

  const handleVoiceClick = useCallback(
    (stsId: string) => {
      if (stsId === selectedStsId) return;
      if (isDirty) {
        setPendingStsId(stsId);
      } else {
        setSelectedStsId(stsId);
      }
    },
    [isDirty, selectedStsId, setSelectedStsId]
  );

  const handleDialogDiscard = useCallback(() => {
    if (pendingStsId) {
      setSelectedStsId(pendingStsId);
      setPendingStsId(null);
    }
  }, [pendingStsId, setSelectedStsId]);

  const handleDialogCancel = useCallback(() => {
    setPendingStsId(null);
  }, []);

  // Play LLM audio sample for a voice
  const handlePlayLLMAudio = useCallback(
    (stsId: string, type: 'neutral' | 'expressive') => {
      if (!llmRunDir || !selectedProvider) return;
      const runId = llmRunDir.split('/').pop() ?? '';
      const suffix = type === 'neutral' ? '_neutral' : '_expressive';
      const filename = `${selectedProvider}_${stsId}${suffix}.mp3`;
      const url = apiService.getLLMRunAudioUrl(runId, filename);
      loadAndPlay(url, {
        primaryText: `${stsId} (${type})`,
        secondaryText: `${selectedProvider} · LLM sample`,
      });
    },
    [llmRunDir, selectedProvider, loadAndPlay]
  );

  // Handle provider select, including the "Load LLM Run Data" action
  const handleProviderChange = useCallback(
    (value: string) => {
      if (value === LOAD_RUN_VALUE) {
        setShowLoadRunDialog(true);
        return;
      }
      setSelectedProvider(value || null);
      setSearchQuery('');
    },
    [setSelectedProvider, setShowLoadRunDialog]
  );

  // Handle import from dialog
  const handleImportRun = useCallback(
    (pathOverride?: string | unknown) => {
      const dir = (
        typeof pathOverride === 'string' ? pathOverride : loadRunDir
      ).trim();
      if (!dir) return;
      importMutation.mutate(dir, {
        onSuccess: (data) => {
          setLLMRunData(data, dir);
          // Auto-select the provider from the loaded run
          if (data.provider && providers?.includes(data.provider)) {
            setSelectedProvider(data.provider);
          }
          setShowLoadRunDialog(false);
          setLoadRunDir('');
        },
      });
    },
    [
      loadRunDir,
      importMutation,
      setLLMRunData,
      setSelectedProvider,
      setShowLoadRunDialog,
      providers,
    ]
  );

  // Open directory picker (Tauri) or fall back to text input
  const handleBrowseDirectory = useCallback(async () => {
    try {
      const { isTauri } = await import('@tauri-apps/api/core');
      if (isTauri()) {
        const { open } = await import('@tauri-apps/plugin-dialog');
        const selected = await open({
          directory: true,
          multiple: false,
          title: 'Select LLM Run Output Directory',
        });
        if (selected && typeof selected === 'string') {
          setLoadRunDir(selected);
        }
        return;
      }
    } catch {
      // Not in Tauri, fall through to focus input
    }
    loadRunInputRef.current?.focus();
  }, []);

  return (
    <div className="flex h-full flex-col">
      {/* Provider selector */}
      <div className="space-y-2 border-b p-3">
        <Select
          value={selectedProvider ?? ''}
          onValueChange={handleProviderChange}
        >
          <SelectTrigger className="h-8 w-full text-xs">
            <SelectValue placeholder="Select provider..." />
          </SelectTrigger>
          <SelectContent>
            {providers?.map((p) => (
              <SelectItem key={p} value={p} className="text-xs">
                {p}
                {llmRunData?.provider === p && (
                  <span className="ml-1.5 text-[10px] text-blue-600">
                    (LLM data)
                  </span>
                )}
              </SelectItem>
            ))}
            <SelectSeparator />
            <SelectItem
              value={LOAD_RUN_VALUE}
              className="text-muted-foreground text-xs"
            >
              <span className="flex items-center gap-1.5">
                <FolderOpen className="size-3" />
                Load LLM Run Data
              </span>
            </SelectItem>
          </SelectContent>
        </Select>

        {/* LLM run indicator */}
        {llmRunData && selectedProvider === llmRunData.provider && (
          <div className="flex items-center gap-1.5 px-1">
            <Badge
              variant="outline"
              className="border-blue-200 px-1.5 py-0 text-[10px] text-blue-600"
            >
              LLM: {Object.keys(llmRunData.voices).length} voices
            </Badge>
          </div>
        )}

        {/* Search */}
        <div className="relative">
          <Search className="text-muted-foreground absolute top-1/2 left-2 size-3 -translate-y-1/2" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Filter voices..."
            className="h-7 pl-7 text-xs"
          />
        </div>
      </div>

      {/* Voice list */}
      <ScrollArea className="flex-1">
        <div className="p-1">
          {!selectedProvider ? (
            <p className="text-muted-foreground p-3 text-center text-xs">
              Select a provider to browse voices
            </p>
          ) : filteredVoices.length === 0 ? (
            <p className="text-muted-foreground p-3 text-center text-xs">
              No voices found
            </p>
          ) : (
            filteredVoices.map((voice) => {
              const hasLLMData = llmVoiceIds.has(voice.sts_id);
              const isSelected = voice.sts_id === selectedStsId;
              const llmVoice = hasLLMData
                ? llmRunData?.voices[voice.sts_id]
                : null;
              const hasFlags =
                llmVoice && llmVoice.flags && llmVoice.flags.length > 0;

              return (
                <button
                  type="button"
                  key={voice.sts_id}
                  className={`group flex w-full cursor-pointer items-center gap-1 rounded-sm px-2 py-1 text-left transition-colors select-none ${
                    isSelected
                      ? 'bg-primary/15 font-medium'
                      : 'hover:bg-accent/50'
                  } ${hasLLMData ? 'border-l-2 border-blue-400' : ''}`}
                  onClick={() => handleVoiceClick(voice.sts_id)}
                >
                  {/* Dirty indicator */}
                  {isDirty && isSelected && (
                    <span className="size-1.5 shrink-0 rounded-full bg-amber-500" />
                  )}

                  {/* Voice name */}
                  <span className="flex-1 truncate text-xs">
                    {voice.sts_id}
                  </span>

                  {/* LLM flag indicator */}
                  {hasFlags && (
                    <TooltipProvider delayDuration={200}>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <AlertTriangle className="size-3 shrink-0 cursor-help text-amber-500" />
                        </TooltipTrigger>
                        <TooltipContent side="top">
                          <p className="text-xs font-medium">LLM Flags</p>
                          <p className="text-muted-foreground text-xs">
                            {parseFlaggedDimensions(llmVoice!.flags).join(', ')}
                          </p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  )}

                  {/* Gender badge */}
                  {voice.voice_properties?.gender && (
                    <TooltipProvider delayDuration={200}>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Badge
                            variant="outline"
                            className="shrink-0 cursor-help px-1 py-0 text-[10px]"
                          >
                            {voice.voice_properties.gender === 'masculine'
                              ? 'M'
                              : voice.voice_properties.gender === 'feminine'
                                ? 'F'
                                : voice.voice_properties.gender ===
                                    'androgynous'
                                  ? 'A'
                                  : '?'}
                          </Badge>
                        </TooltipTrigger>
                        <TooltipContent side="top">
                          <p className="text-xs capitalize">
                            {voice.voice_properties.gender}
                          </p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  )}

                  {/* Play preview button */}
                  {voice.preview_url && (
                    <div className="shrink-0 opacity-0 transition-opacity group-hover:opacity-100">
                      <PlayPreviewButton
                        voice={voice}
                        providerName={selectedProvider}
                        size="icon-sm"
                        variant="list-action"
                      />
                    </div>
                  )}

                  {/* LLM audio play buttons */}
                  {hasLLMData && !voice.preview_url && (
                    <button
                      type="button"
                      className="hover:bg-accent shrink-0 cursor-pointer rounded p-0.5 opacity-0 transition-opacity group-hover:opacity-100"
                      onClick={(e) => {
                        e.stopPropagation();
                        handlePlayLLMAudio(voice.sts_id, 'neutral');
                      }}
                      title="Play LLM neutral sample"
                    >
                      <Play className="size-3" />
                    </button>
                  )}
                </button>
              );
            })
          )}
        </div>
      </ScrollArea>

      {/* Voice count */}
      {selectedProvider && voices && (
        <div className="border-t px-3 py-1.5">
          <p className="text-muted-foreground text-[10px]">
            {filteredVoices.length}
            {searchQuery.trim() ? ` / ${voices.length}` : ''} voices
          </p>
        </div>
      )}

      {/* Unsaved changes dialog */}
      <UnsavedChangesDialog
        open={!!pendingStsId}
        onSaveAndContinue={handleDialogDiscard}
        onDiscard={handleDialogDiscard}
        onCancel={handleDialogCancel}
      />

      {/* Load LLM Run Data dialog */}
      <Dialog
        open={showLoadRunDialog}
        onOpenChange={(open) => setShowLoadRunDialog(open)}
      >
        <DialogContent className="max-w-lg">
          <DialogTitle>Load LLM Run Data</DialogTitle>
          <DialogDescription>
            Select an LLM voice labeler run to load consensus data and audio
            samples.
          </DialogDescription>

          {/* Available runs */}
          {availableRuns && availableRuns.length > 0 && (
            <div className="space-y-1.5">
              <p className="text-muted-foreground text-xs font-medium">
                Available runs
              </p>
              <ScrollArea className="max-h-48">
                <div className="space-y-1">
                  {availableRuns.map((run) => (
                    <button
                      key={run.name}
                      type="button"
                      className={`w-full cursor-pointer rounded-md px-3 py-2 text-left text-xs transition-colors ${
                        loadRunDir === run.path
                          ? 'bg-primary/15 font-medium'
                          : 'hover:bg-accent/50'
                      }`}
                      onClick={() => setLoadRunDir(run.path)}
                      onDoubleClick={() => {
                        handleImportRun(run.path);
                      }}
                    >
                      <span className="font-medium">{run.provider}</span>
                      <span className="text-muted-foreground ml-1.5">
                        {run.timestamp.replace('_', ' ')}
                      </span>
                      <span className="text-muted-foreground ml-1.5">
                        ({run.voice_count} voices)
                      </span>
                    </button>
                  ))}
                </div>
              </ScrollArea>
            </div>
          )}

          {/* Manual path entry */}
          <div className="space-y-1.5">
            {availableRuns && availableRuns.length > 0 && (
              <p className="text-muted-foreground text-xs font-medium">
                Or enter path manually
              </p>
            )}
            <div className="flex gap-2">
              <Input
                ref={loadRunInputRef}
                value={loadRunDir}
                onChange={(e) => setLoadRunDir(e.target.value)}
                placeholder="output/llm_labeler_minimax_20260309_..."
                className="flex-1 text-xs"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleImportRun();
                }}
              />
              {isTauriEnv && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleBrowseDirectory}
                  className="shrink-0 cursor-pointer"
                >
                  <FolderOpen className="size-4" />
                </Button>
              )}
            </div>
          </div>

          {importMutation.isError && (
            <p className="text-destructive text-xs">
              {importMutation.error.message}
            </p>
          )}
          <DialogFooter>
            <Button
              variant="ghost"
              onClick={() => setShowLoadRunDialog(false)}
              className="cursor-pointer"
            >
              Cancel
            </Button>
            <Button
              onClick={handleImportRun}
              disabled={!loadRunDir.trim() || importMutation.isPending}
              className="cursor-pointer"
            >
              {importMutation.isPending && (
                <Loader2 className="mr-1 size-4 animate-spin" />
              )}
              Import
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
