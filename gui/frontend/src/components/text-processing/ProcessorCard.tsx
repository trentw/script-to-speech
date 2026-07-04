import { dump } from 'js-yaml';
import {
  AlertCircle,
  ArrowDown,
  ArrowUp,
  Check,
  FlaskConical,
  HelpCircle,
  Trash2,
  Undo2,
} from 'lucide-react';
import React, { useMemo, useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from '@/components/ui/dialog';
import { cn } from '@/lib/utils';

import type {
  RegistryProcessor,
  TextProcessorPreviewDiff,
  ValidationIssue,
} from '../../types/text-processing';
import { DirtyDiffResults } from './DirtyDiffResults';
import {
  type BaselineEntry,
  changedScalarFields,
  changeKey,
  computeRowDiff,
  type EditorEntry,
  type EntryStatus,
  type RowChangeRef,
  stripRowUids,
} from './editorState';
import { type SuggestionSources } from './fields/FieldInput';
import { InlineIconButton } from './InlineIconButton';
import { ProcessorConfigForm } from './ProcessorConfigForm';
import { RawConfigEditor } from './RawConfigEditor';

interface ProcessorCardProps {
  entry: EditorEntry;
  registryItem?: RegistryProcessor | undefined;
  issues: ValidationIssue[];
  status: EntryStatus;
  /** The entry as it is on disk; null for added entries */
  baselineEntry: BaselineEntry | null;
  canMoveUp: boolean;
  canMoveDown: boolean;
  isCommitting: boolean;
  suggestions: SuggestionSources;
  onMove: (direction: 'up' | 'down') => void;
  onRemove: () => void;
  onConfigChange: (config: Record<string, unknown>) => void;
  onYamlChange: (configYaml: string) => void;
  /**
   * Kept for a future "edit as YAML" affordance; the toggle button was
   * removed from the UI (raw editing stays available for unknown processors)
   */
  onToggleRawMode: (rawMode: boolean) => void;
  onCommit: () => void;
  onRevert: () => void;
  onTest: () => void;
  onTestRow: (change: RowChangeRef) => void;
  onCommitRow: (change: RowChangeRef) => void;
  onRevertRow: (change: RowChangeRef) => void;
  onRestoreRemovedRow: (change: RowChangeRef) => void;
  isTesting: boolean;
  /** The most recent test result, keyed by changeKey (any change, any card) */
  testResult: { key: string; data: TextProcessorPreviewDiff } | null;
  onDismissTest: () => void;
}

/**
 * One pipeline entry: schema-driven form for known processors, raw YAML
 * fallback for unknown ones (or when toggled via "Edit as YAML"). When the
 * entry diverges from what's on disk it shows a status chip plus inline
 * save/discard actions for just this change (review-audio style).
 */
export const ProcessorCard: React.FC<ProcessorCardProps> = ({
  entry,
  registryItem,
  issues,
  status,
  baselineEntry,
  canMoveUp,
  canMoveDown,
  isCommitting,
  suggestions,
  onMove,
  onRemove,
  onConfigChange,
  onYamlChange,
  onToggleRawMode: _onToggleRawMode,
  onCommit,
  onRevert,
  onTest,
  onTestRow,
  onCommitRow,
  onRevertRow,
  onRestoreRemovedRow,
  isTesting,
  testResult,
  onDismissTest,
}) => {
  const schema = registryItem?.schema ?? null;
  const useForm = entry.known && schema && !entry.rawMode;
  const [helpOpen, setHelpOpen] = useState(false);

  // Seed the raw editor display from the structured config when there's no
  // YAML text (form edits clear it). Derived, not dispatched: merely toggling
  // the view must not register as an edit against the baseline. js-yaml is
  // display-only serialization — the backend still parses whatever is saved.
  const rawText =
    entry.config_yaml ?? dump(stripRowUids(entry.config ?? {}) ?? {});

  const dirty = status !== 'clean';

  // Localize what changed inside a modified card: per-row statuses for list
  // fields and dots for changed scalar fields. Added entries skip this (the
  // whole card is new; painting every row amber would be noise).
  const rowDiff = useMemo(
    () =>
      status === 'modified' && !entry.rawMode
        ? computeRowDiff(entry, baselineEntry)
        : undefined,
    [status, entry, baselineEntry]
  );
  const changedFields = useMemo(
    () =>
      status === 'modified' && !entry.rawMode
        ? changedScalarFields(entry, baselineEntry)
        : undefined,
    [status, entry, baselineEntry]
  );

  const entryTestResult =
    testResult &&
    testResult.key === changeKey({ type: 'entry', uid: entry.uid })
      ? testResult.data
      : null;
  const rowChangeRef = (
    field: string,
    rowUid: string,
    removal: boolean
  ): RowChangeRef => ({
    type: removal ? 'rowRemoval' : 'row',
    entryUid: entry.uid,
    field,
    rowUid,
  });
  const rowTestResultFor = (
    field: string,
    rowUid: string,
    removal: boolean
  ): TextProcessorPreviewDiff | null =>
    testResult &&
    testResult.key === changeKey(rowChangeRef(field, rowUid, removal))
      ? testResult.data
      : null;

  return (
    <Card
      className={cn('py-4', dirty && 'border-amber-500/40 bg-amber-500/[0.03]')}
    >
      <CardHeader className="px-4">
        <div className="flex items-center justify-between gap-2">
          {/* Left: identity, then state + its actions (chip next to the
              buttons that act on that state) */}
          <div className="flex min-w-0 items-center gap-2">
            <span className="truncate font-semibold">
              {registryItem?.label || entry.name}
            </span>
            {schema?.help && (
              <InlineIconButton
                label="About this processor"
                onClick={() => setHelpOpen(true)}
              >
                <HelpCircle className="h-3.5 w-3.5" />
              </InlineIconButton>
            )}
            <Badge variant="outline" className="font-mono text-[10px]">
              {entry.name}
            </Badge>
            {!entry.known && (
              <Badge variant="secondary" className="text-[10px]">
                unknown
              </Badge>
            )}
            {registryItem?.multi_config_mode === 'override' && (
              <Badge variant="secondary" className="text-[10px]">
                single instance
              </Badge>
            )}
            {issues.length > 0 && (
              <Badge variant="destructive" className="gap-1 text-[10px]">
                <AlertCircle className="h-3 w-3" />
                invalid
              </Badge>
            )}
            {dirty && (
              <>
                <Badge
                  variant="outline"
                  className="border-amber-500/50 bg-amber-500/10 text-[10px] text-amber-600"
                >
                  {status}
                </Badge>
                <InlineIconButton
                  label="Test this change"
                  onClick={onTest}
                  disabled={isTesting || issues.length > 0}
                >
                  <FlaskConical className="h-3.5 w-3.5" />
                </InlineIconButton>
                <InlineIconButton
                  label="Save this change"
                  onClick={onCommit}
                  disabled={isCommitting || issues.length > 0}
                  className="text-green-600 hover:text-green-700"
                >
                  <Check className="h-3.5 w-3.5" />
                </InlineIconButton>
                <InlineIconButton
                  label="Discard this change"
                  onClick={onRevert}
                  disabled={isCommitting}
                  className="text-destructive hover:text-destructive"
                >
                  <Undo2 className="h-3.5 w-3.5" />
                </InlineIconButton>
              </>
            )}
          </div>

          {/* Right: structural actions only */}
          <div className="flex shrink-0 items-center gap-1">
            <InlineIconButton
              label="Move up"
              onClick={() => onMove('up')}
              disabled={!canMoveUp}
            >
              <ArrowUp className="h-3.5 w-3.5" />
            </InlineIconButton>
            <InlineIconButton
              label="Move down"
              onClick={() => onMove('down')}
              disabled={!canMoveDown}
            >
              <ArrowDown className="h-3.5 w-3.5" />
            </InlineIconButton>
            <InlineIconButton
              label="Remove"
              onClick={onRemove}
              className="text-destructive hover:text-destructive"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </InlineIconButton>
          </div>
        </div>
        {registryItem?.description && (
          <p className="text-muted-foreground text-xs">
            {registryItem.description}
          </p>
        )}
      </CardHeader>

      <CardContent className="px-4">
        {issues.length > 0 && (
          <div className="border-destructive/50 bg-destructive/10 mb-3 rounded-md border p-2">
            {issues.map((issue, i) => (
              <p key={i} className="text-destructive text-xs">
                {issue.message}
              </p>
            ))}
          </div>
        )}

        {useForm ? (
          <ProcessorConfigForm
            schema={schema}
            config={entry.config ?? {}}
            onChange={onConfigChange}
            suggestions={suggestions}
            rowDiff={rowDiff}
            changedFields={changedFields}
            onTestRow={(field, rowUid, removal) =>
              onTestRow(rowChangeRef(field, rowUid, removal))
            }
            rowTestResultFor={rowTestResultFor}
            onCommitRow={(field, rowUid, removal) =>
              onCommitRow(rowChangeRef(field, rowUid, removal))
            }
            onRevertRow={(field, rowUid) =>
              onRevertRow(rowChangeRef(field, rowUid, false))
            }
            onRestoreRemovedRow={(field, rowUid) =>
              onRestoreRemovedRow(rowChangeRef(field, rowUid, true))
            }
            isTesting={isTesting}
            isCommitting={isCommitting}
            canCommitRows={issues.length === 0}
            onDismissTest={onDismissTest}
          />
        ) : (
          <RawConfigEditor configYaml={rawText} onChange={onYamlChange} />
        )}

        {dirty && entryTestResult && (
          <div className="mt-3">
            <DirtyDiffResults
              result={entryTestResult}
              subject="this change"
              onDismiss={onDismissTest}
            />
          </div>
        )}
      </CardContent>

      {schema?.help && (
        <Dialog open={helpOpen} onOpenChange={setHelpOpen}>
          <DialogContent>
            <DialogTitle>{schema.label}</DialogTitle>
            <DialogDescription>{schema.description}</DialogDescription>
            <div className="text-sm whitespace-pre-line">{schema.help}</div>
          </DialogContent>
        </Dialog>
      )}
    </Card>
  );
};
