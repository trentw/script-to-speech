import { useBlocker } from '@tanstack/react-router';
import { AlertTriangle, Loader2, Save } from 'lucide-react';
import React, { useEffect, useMemo, useReducer, useState } from 'react';
import { toast } from 'sonner';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { buttonUtils } from '@/components/ui/button-variants';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

import {
  useConvertTextProcessorConfig,
  usePreviewTextProcessorDiff,
  useResetTextProcessorConfig,
  useUpdateTextProcessorConfig,
  useValidateTextProcessorEntries,
} from '../../hooks/mutations/useTextProcessorConfigMutations';
import { useTextProcessorConfig } from '../../hooks/queries/useTextProcessorConfig';
import { useTextProcessorRegistry } from '../../hooks/queries/useTextProcessorRegistry';
import { useDebounce } from '../../hooks/useDebounce';
import { TextProcessorApiError } from '../../services/textProcessorApi';
import type {
  TextProcessorPreviewDiff,
  ValidationIssue,
} from '../../types/text-processing';
import { UnsavedChangesDialog } from '../voice-editor/UnsavedChangesDialog';
import {
  type AnyChangeRef,
  buildDefaultConfig,
  buildSingleChangePayload,
  buildSingleRowChangePayload,
  changeKey,
  changeKeyBelongsToEntry,
  computeDiff,
  type DirtyChangeRef,
  editorReducer,
  initialEditorState,
  type RowChangeRef,
  toEntryPayloads,
} from './editorState';
import { GlobalDefaultActions } from './GlobalDefaultActions';
import { PipelineSection } from './PipelineSection';
import { PreviewPanel } from './PreviewPanel';
import { StalenessBanner } from './StalenessBanner';

interface TextProcessorPipelineEditorProps {
  inputPath: string;
}

/**
 * The text processor configuration editor. The config file on disk is the
 * source of truth (shared with the CLI); this component maintains an edit
 * buffer initialized from the last server read and saves it back with
 * optimistic locking (file hash), surfacing conflicts instead of clobbering.
 */
export const TextProcessorPipelineEditor: React.FC<
  TextProcessorPipelineEditorProps
> = ({ inputPath }) => {
  const configQuery = useTextProcessorConfig(inputPath);
  const registryQuery = useTextProcessorRegistry();

  const updateConfig = useUpdateTextProcessorConfig();
  const convertConfig = useConvertTextProcessorConfig();
  const resetConfig = useResetTextProcessorConfig();
  const validateEntries = useValidateTextProcessorEntries();

  const [state, dispatch] = useReducer(editorReducer, initialEditorState);
  const [issues, setIssues] = useState<ValidationIssue[]>([]);

  const previewDiff = usePreviewTextProcessorDiff();
  const [testResult, setTestResult] = useState<{
    key: string;
    data: TextProcessorPreviewDiff;
  } | null>(null);

  const serverConfig = configQuery.data ?? null;

  const diff = useMemo(() => computeDiff(state), [state]);
  const baselineByUid = useMemo(
    () => new Map(state.baseline.map((b) => [b.uid, b])),
    [state.baseline]
  );

  // Adopt server reads: initial load always; out-of-band changes (CLI edits
  // picked up by focus refetch) only while the buffer is clean.
  useEffect(() => {
    if (!serverConfig) return;
    if (state.baseFileHash === null) {
      dispatch({ type: 'init', config: serverConfig });
    } else if (!diff.dirty && serverConfig.file_hash !== state.baseFileHash) {
      dispatch({ type: 'init', config: serverConfig });
    }
  }, [serverConfig, state.baseFileHash, diff.dirty]);

  // Debounced server-side validation of the buffer (authoritative — includes
  // Python regex compilation)
  const debouncedEntries = useDebounce(state.entries, 600);
  useEffect(() => {
    if (debouncedEntries.length === 0) {
      setIssues([]);
      return;
    }
    validateEntries
      .mutateAsync(toEntryPayloads(debouncedEntries))
      .then((result) => setIssues(result.errors))
      .catch(() => {
        // Validation service errors shouldn't block editing
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedEntries]);

  const issuesByUid = useMemo(() => {
    const map = new Map<string, ValidationIssue[]>();
    for (const issue of issues) {
      const entry = state.entries[issue.entry_index];
      if (!entry) continue;
      map.set(entry.uid, [...(map.get(entry.uid) ?? []), issue]);
    }
    return map;
  }, [issues, state.entries]);

  // Block route navigation (and window unload via beforeunload) while there
  // are unsaved changes. Note: Tauri's native window close can bypass
  // beforeunload; an onCloseRequested listener is out of scope for now.
  const blocker = useBlocker({
    shouldBlockFn: () => diff.dirty,
    disabled: !diff.dirty,
    enableBeforeUnload: () => diff.dirty,
    withResolver: true,
  });

  const fileChangedUnderneath =
    diff.dirty &&
    serverConfig !== null &&
    state.baseFileHash !== null &&
    serverConfig.file_hash !== state.baseFileHash;

  const handleSaveError = (error: unknown) => {
    if (error instanceof TextProcessorApiError && error.status === 409) {
      toast.error('The config file changed outside this editor', {
        description:
          'Reload to pick up the external changes, then re-apply your edits.',
      });
    } else if (
      error instanceof TextProcessorApiError &&
      error.details?.errors
    ) {
      setIssues(error.details.errors as ValidationIssue[]);
      toast.error('Fix the highlighted configuration errors and try again');
    } else {
      toast.error(error instanceof Error ? error.message : 'Save failed');
    }
  };

  const handleSave = async (): Promise<boolean> => {
    if (!state.baseFileHash) return false;
    try {
      const saved = await updateConfig.mutateAsync({
        inputPath,
        entries: toEntryPayloads(state.entries),
        baseFileHash: state.baseFileHash,
      });
      dispatch({ type: 'init', config: saved });
      setTestResult(null);
      toast.success('Text processing configuration saved');
      return true;
    } catch (error) {
      handleSaveError(error);
      return false;
    }
  };

  // Inline "save this change": write the file as it is on disk plus exactly
  // one dirty change (an entry, a removal, an order change, or a single
  // row), then re-baseline so the other pending edits stay put.
  const handleCommitChange = async (change: AnyChangeRef) => {
    if (!state.baseFileHash) return;
    const single =
      change.type === 'row' || change.type === 'rowRemoval'
        ? buildSingleRowChangePayload(state, change)
        : buildSingleChangePayload(state, change);
    if (!single) return;
    try {
      const saved = await updateConfig.mutateAsync({
        inputPath,
        entries: single.payload,
        baseFileHash: state.baseFileHash,
      });
      dispatch({
        type: 'rebaseline',
        config: saved,
        uidOrder: single.uidOrder,
      });
      setTestResult(null);
      toast.success('Change saved');
    } catch (error) {
      handleSaveError(error);
    }
  };

  // Inline "test this change": diff the on-disk baseline plus exactly one
  // dirty change (an entry, a removal, an order change, or a single row)
  // against the baseline itself — the change's added effect.
  const handleTestChange = async (change: AnyChangeRef) => {
    const single =
      change.type === 'row' || change.type === 'rowRemoval'
        ? buildSingleRowChangePayload(state, change)
        : buildSingleChangePayload(state, change);
    if (!single) return;
    try {
      const data = await previewDiff.mutateAsync({
        inputPath,
        draftEntries: single.payload,
        baselineEntries: toEntryPayloads(state.baseline),
        maxChangedChunks: 10,
      });
      setTestResult({ key: changeKey(change), data });
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Test failed');
    }
  };

  // A test result describes one change vs a specific disk baseline: drop it
  // when that change is edited or reverted, and drop all results when a
  // write (or reload) moves the baseline.
  const clearAllTests = () => setTestResult(null);
  const clearTestFor = (change: DirtyChangeRef) =>
    setTestResult((current) =>
      current && current.key === changeKey(change) ? null : current
    );
  // Any edit inside an entry stales that entry's result AND its row results
  const clearTestsForEntry = (uid: string) =>
    setTestResult((current) =>
      current && changeKeyBelongsToEntry(current.key, uid) ? null : current
    );

  const handleRevertRow = (change: RowChangeRef) => {
    clearTestsForEntry(change.entryUid);
    dispatch({
      type: 'revertRow',
      entryUid: change.entryUid,
      field: change.field,
      rowUid: change.rowUid,
    });
  };

  const handleRestoreRemovedRow = (change: RowChangeRef) => {
    clearTestsForEntry(change.entryUid);
    dispatch({
      type: 'restoreRemovedRow',
      entryUid: change.entryUid,
      field: change.field,
      rowUid: change.rowUid,
    });
  };

  const handleConvert = async () => {
    try {
      const converted = await convertConfig.mutateAsync(inputPath);
      dispatch({ type: 'init', config: converted });
      toast.success('Converted to an editable standalone config');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Conversion failed');
    }
  };

  const handleReset = async () => {
    try {
      const fresh = await resetConfig.mutateAsync({
        inputPath,
        source: 'shipped_default',
      });
      dispatch({ type: 'init', config: fresh });
      toast.success('Config re-seeded from the built-in defaults');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Reset failed');
    }
  };

  if (configQuery.isLoading || registryQuery.isLoading) {
    return (
      <div className="text-muted-foreground flex items-center gap-2 py-12">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading configuration…
      </div>
    );
  }

  if (configQuery.error || !serverConfig) {
    return (
      <Alert variant="destructive">
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription>
          {configQuery.error instanceof Error
            ? configQuery.error.message
            : 'Failed to load the text processor configuration.'}
        </AlertDescription>
      </Alert>
    );
  }

  if (registryQuery.error || !registryQuery.data) {
    return (
      <Alert variant="destructive">
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription>
          Failed to load the text processor registry.
        </AlertDescription>
      </Alert>
    );
  }

  const registry = registryQuery.data;
  const suggestions = {
    chunk_types: registry.chunk_types,
    chunk_fields: registry.chunk_fields,
  };

  const changeDetails =
    diff.details.length > 0 ? (
      <div className="space-y-0.5">
        {diff.details.map((detail, i) => (
          <p key={i}>{detail}</p>
        ))}
      </div>
    ) : (
      <p>No unsaved changes</p>
    );

  return (
    <div className="space-y-4">
      <UnsavedChangesDialog
        open={blocker.status === 'blocked'}
        description="You have unsaved text processing changes. What would you like to do?"
        onCancel={() => blocker.reset?.()}
        onDiscard={() => {
          clearAllTests();
          dispatch({ type: 'init', config: serverConfig });
          blocker.proceed?.();
        }}
        onSaveAndContinue={() => {
          void handleSave().then((saved) => {
            if (saved) {
              blocker.proceed?.();
            } else {
              blocker.reset?.();
            }
          });
        }}
      />

      <StalenessBanner
        config={serverConfig}
        onConvert={handleConvert}
        onReseed={handleReset}
        isConverting={convertConfig.isPending}
      />

      {fileChangedUnderneath && (
        <Alert variant="warning">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription className="flex items-center justify-between gap-2">
            <span>
              The config file changed on disk while you were editing (e.g. via
              the CLI). Saving now would fail — reload to pick up the changes.
            </span>
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                clearAllTests();
                dispatch({ type: 'init', config: serverConfig });
              }}
            >
              Reload (discard my edits)
            </Button>
          </AlertDescription>
        </Alert>
      )}

      <Tabs defaultValue="configure">
        <div className="flex items-center justify-between gap-2">
          <TabsList>
            <TabsTrigger value="configure">Configure</TabsTrigger>
            <TabsTrigger value="preview">Preview</TabsTrigger>
          </TabsList>

          <div className="flex items-center gap-2">
            <GlobalDefaultActions
              getEntries={() => toEntryPayloads(state.entries)}
              metadata={serverConfig.metadata}
              onLoadEntries={(entries) =>
                dispatch({ type: 'replaceEntries', entries })
              }
              onResetProject={handleReset}
              isDirty={diff.dirty}
            />
            {diff.dirty && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      clearAllTests();
                      dispatch({ type: 'init', config: serverConfig });
                    }}
                  >
                    Discard all
                    <Badge variant="secondary" className="ml-1">
                      {diff.total}
                    </Badge>
                  </Button>
                </TooltipTrigger>
                <TooltipContent>{changeDetails}</TooltipContent>
              </Tooltip>
            )}
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  size="sm"
                  aria-disabled={!diff.dirty || updateConfig.isPending}
                  className={cn(
                    (!diff.dirty || updateConfig.isPending) &&
                      buttonUtils.ariaDisabled
                  )}
                  onClick={() => {
                    if (diff.dirty && !updateConfig.isPending) {
                      void handleSave();
                    }
                  }}
                >
                  <Save className="mr-1 h-4 w-4" />
                  {updateConfig.isPending ? 'Saving…' : 'Save all'}
                  {diff.total > 0 && (
                    <Badge variant="secondary" className="ml-1">
                      {diff.total}
                    </Badge>
                  )}
                </Button>
              </TooltipTrigger>
              <TooltipContent>{changeDetails}</TooltipContent>
            </Tooltip>
          </div>
        </div>

        <TabsContent value="configure" className="mt-4 space-y-6">
          <PipelineSection
            kind="preprocessor"
            title="Structure"
            description="Reshape the screenplay's chunks before line-by-line processing (merge, split, remove)."
            entries={state.entries}
            registryItems={registry.preprocessors}
            issuesByUid={issuesByUid}
            statusByUid={diff.statusByUid}
            baselineByUid={baselineByUid}
            removed={diff.removed}
            orderChanged={diff.orderChanged.preprocessor}
            isCommitting={updateConfig.isPending}
            suggestions={suggestions}
            defaultCollapsed
            onMove={(uid, direction) =>
              dispatch({ type: 'move', uid, direction })
            }
            onRemove={(uid) => dispatch({ type: 'remove', uid })}
            onConfigChange={(uid, config) => {
              clearTestsForEntry(uid);
              dispatch({ type: 'updateConfig', uid, config });
            }}
            onYamlChange={(uid, configYaml) => {
              clearTestsForEntry(uid);
              dispatch({ type: 'updateYaml', uid, configYaml });
            }}
            onToggleRawMode={(uid, rawMode) =>
              dispatch({ type: 'setRawMode', uid, rawMode })
            }
            onAdd={(name) => {
              const item = registry.preprocessors.find((p) => p.name === name);
              dispatch({
                type: 'add',
                kind: 'preprocessor',
                name,
                config: buildDefaultConfig(item?.schema ?? null),
              });
            }}
            onCommitChange={(change) => void handleCommitChange(change)}
            onRevertEntry={(uid) => {
              clearTestsForEntry(uid);
              dispatch({ type: 'revertEntry', uid });
            }}
            onRestoreRemoved={(uid) => {
              clearTestFor({ type: 'removal', uid });
              dispatch({ type: 'restoreRemoved', uid });
            }}
            onRevertOrder={() => {
              clearTestFor({ type: 'order', kind: 'preprocessor' });
              dispatch({ type: 'revertOrder', kind: 'preprocessor' });
            }}
            onRevertRow={handleRevertRow}
            onRestoreRemovedRow={handleRestoreRemovedRow}
            onTestChange={(change) => void handleTestChange(change)}
            isTesting={previewDiff.isPending}
            testResult={testResult}
            onDismissTest={() => setTestResult(null)}
          />

          <Separator />

          <PipelineSection
            kind="processor"
            title="Text"
            description="Transform the spoken text of each line (substitutions, casing, pattern replacements)."
            entries={state.entries}
            registryItems={registry.processors}
            issuesByUid={issuesByUid}
            statusByUid={diff.statusByUid}
            baselineByUid={baselineByUid}
            removed={diff.removed}
            orderChanged={diff.orderChanged.processor}
            isCommitting={updateConfig.isPending}
            suggestions={suggestions}
            onMove={(uid, direction) =>
              dispatch({ type: 'move', uid, direction })
            }
            onRemove={(uid) => dispatch({ type: 'remove', uid })}
            onConfigChange={(uid, config) => {
              clearTestsForEntry(uid);
              dispatch({ type: 'updateConfig', uid, config });
            }}
            onYamlChange={(uid, configYaml) => {
              clearTestsForEntry(uid);
              dispatch({ type: 'updateYaml', uid, configYaml });
            }}
            onToggleRawMode={(uid, rawMode) =>
              dispatch({ type: 'setRawMode', uid, rawMode })
            }
            onAdd={(name) => {
              const item = registry.processors.find((p) => p.name === name);
              dispatch({
                type: 'add',
                kind: 'processor',
                name,
                config: buildDefaultConfig(item?.schema ?? null),
              });
            }}
            onCommitChange={(change) => void handleCommitChange(change)}
            onRevertEntry={(uid) => {
              clearTestsForEntry(uid);
              dispatch({ type: 'revertEntry', uid });
            }}
            onRestoreRemoved={(uid) => {
              clearTestFor({ type: 'removal', uid });
              dispatch({ type: 'restoreRemoved', uid });
            }}
            onRevertOrder={() => {
              clearTestFor({ type: 'order', kind: 'processor' });
              dispatch({ type: 'revertOrder', kind: 'processor' });
            }}
            onRevertRow={handleRevertRow}
            onRestoreRemovedRow={handleRestoreRemovedRow}
            onTestChange={(change) => void handleTestChange(change)}
            isTesting={previewDiff.isPending}
            testResult={testResult}
            onDismissTest={() => setTestResult(null)}
          />
        </TabsContent>

        <TabsContent value="preview" className="mt-4">
          <PreviewPanel
            inputPath={inputPath}
            getEntries={() => toEntryPayloads(state.entries)}
            getBaselineEntries={() => toEntryPayloads(state.baseline)}
            dirty={diff.dirty}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
};
