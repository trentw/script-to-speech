import {
  ArrowDown,
  Check,
  ChevronDown,
  ChevronRight,
  FlaskConical,
  Plus,
  RotateCcw,
  Undo2,
} from 'lucide-react';
import React, { useEffect, useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';

import type {
  ProcessorKind,
  RegistryProcessor,
  TextProcessorPreviewDiff,
  ValidationIssue,
} from '../../types/text-processing';
import { AddProcessorDialog } from './AddProcessorDialog';
import { DirtyDiffResults } from './DirtyDiffResults';
import {
  type AnyChangeRef,
  type BaselineEntry,
  changeKey,
  type DirtyChangeRef,
  type EditorEntry,
  type EntryStatus,
  type RemovedEntry,
  type RowChangeRef,
} from './editorState';
import { type SuggestionSources } from './fields/FieldInput';
import { InlineIconButton } from './InlineIconButton';
import { ProcessorCard } from './ProcessorCard';

interface PipelineSectionProps {
  kind: ProcessorKind;
  title: string;
  description: string;
  entries: EditorEntry[];
  registryItems: RegistryProcessor[];
  issuesByUid: Map<string, ValidationIssue[]>;
  statusByUid: Map<string, EntryStatus>;
  baselineByUid: Map<string, BaselineEntry>;
  removed: RemovedEntry[];
  orderChanged: boolean;
  isCommitting: boolean;
  suggestions: SuggestionSources;
  /** Collapsed by default behind a twirl-down (used for Structure) */
  defaultCollapsed?: boolean;
  onMove: (uid: string, direction: 'up' | 'down') => void;
  onRemove: (uid: string) => void;
  onConfigChange: (uid: string, config: Record<string, unknown>) => void;
  onYamlChange: (uid: string, configYaml: string) => void;
  onToggleRawMode: (uid: string, rawMode: boolean) => void;
  onAdd: (name: string) => void;
  onCommitChange: (change: AnyChangeRef) => void;
  onRevertEntry: (uid: string) => void;
  onRestoreRemoved: (uid: string) => void;
  onRevertOrder: () => void;
  onRevertRow: (change: RowChangeRef) => void;
  onRestoreRemovedRow: (change: RowChangeRef) => void;
  onTestChange: (change: AnyChangeRef) => void;
  isTesting: boolean;
  /** The single most recent test result, keyed by changeKey */
  testResult: { key: string; data: TextProcessorPreviewDiff } | null;
  onDismissTest: () => void;
}

type Row =
  | { type: 'entry'; entry: EditorEntry }
  | { type: 'tombstone'; removed: RemovedEntry };

/**
 * One ordered section of the pipeline (Structure = preprocessors,
 * Text = processors). Entries run top to bottom; each entry's output feeds
 * the next (the arrows between cards). Uncommitted removals stay visible as
 * tombstone rows; a reorder surfaces as a section-level "order changed" chip
 * with its own save/revert.
 */
export const PipelineSection: React.FC<PipelineSectionProps> = ({
  kind,
  title,
  description,
  entries,
  registryItems,
  issuesByUid,
  statusByUid,
  baselineByUid,
  removed,
  orderChanged,
  isCommitting,
  suggestions,
  defaultCollapsed = false,
  onMove,
  onRemove,
  onConfigChange,
  onYamlChange,
  onToggleRawMode,
  onAdd,
  onCommitChange,
  onRevertEntry,
  onRestoreRemoved,
  onRevertOrder,
  onRevertRow,
  onRestoreRemovedRow,
  onTestChange,
  isTesting,
  testResult,
  onDismissTest,
}) => {
  const [addOpen, setAddOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(defaultCollapsed);

  const registryByName = new Map(
    registryItems.map((item) => [item.name, item])
  );
  const sectionEntries = entries.filter((entry) => entry.kind === kind);
  const sectionRemoved = removed.filter((r) => r.entry.kind === kind);

  const dirtyEntryCount = sectionEntries.filter(
    (entry) => (statusByUid.get(entry.uid) ?? 'clean') !== 'clean'
  ).length;
  const pendingCount =
    dirtyEntryCount + sectionRemoved.length + (orderChanged ? 1 : 0);
  const hasIssues = sectionEntries.some(
    (entry) => (issuesByUid.get(entry.uid) ?? []).length > 0
  );

  // Never hide pending state or problems behind the twirl-down
  const mustExpand = pendingCount > 0 || hasIssues;
  useEffect(() => {
    if (mustExpand) setCollapsed(false);
  }, [mustExpand]);

  const resultFor = (
    change: DirtyChangeRef
  ): TextProcessorPreviewDiff | null =>
    testResult && testResult.key === changeKey(change) ? testResult.data : null;

  const orderTestResult = resultFor({ type: 'order', kind });

  // Interleave tombstones after the surviving entry they used to follow
  const rows: Row[] = [];
  for (const r of sectionRemoved.filter((r) => r.afterUid === null)) {
    rows.push({ type: 'tombstone', removed: r });
  }
  for (const entry of sectionEntries) {
    rows.push({ type: 'entry', entry });
    for (const r of sectionRemoved.filter((r) => r.afterUid === entry.uid)) {
      rows.push({ type: 'tombstone', removed: r });
    }
  }

  return (
    <section>
      <div className="mb-3 flex items-start justify-between gap-2">
        <div className="flex min-w-0 items-start gap-1">
          <InlineIconButton
            label={collapsed ? `Expand ${title}` : `Collapse ${title}`}
            onClick={() => setCollapsed(!collapsed)}
          >
            {collapsed ? (
              <ChevronRight className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
          </InlineIconButton>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-semibold">{title}</h2>
              {collapsed && (
                <Badge variant="secondary" className="text-[10px]">
                  {sectionEntries.length} step
                  {sectionEntries.length === 1 ? '' : 's'}
                </Badge>
              )}
              {orderChanged && (
                <span className="flex items-center gap-1">
                  <Badge
                    variant="outline"
                    className="border-amber-500/50 bg-amber-500/10 text-[10px] text-amber-600"
                  >
                    order changed
                  </Badge>
                  <InlineIconButton
                    label="Test order change"
                    onClick={() => onTestChange({ type: 'order', kind })}
                    disabled={isTesting}
                  >
                    <FlaskConical className="h-3.5 w-3.5" />
                  </InlineIconButton>
                  <InlineIconButton
                    label="Save new order"
                    onClick={() => onCommitChange({ type: 'order', kind })}
                    disabled={isCommitting}
                    className="text-green-600 hover:text-green-700"
                  >
                    <Check className="h-3.5 w-3.5" />
                  </InlineIconButton>
                  <InlineIconButton
                    label="Revert order"
                    onClick={onRevertOrder}
                    disabled={isCommitting}
                  >
                    <Undo2 className="h-3.5 w-3.5" />
                  </InlineIconButton>
                </span>
              )}
            </div>
            <p className="text-muted-foreground text-sm">{description}</p>
          </div>
        </div>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setAddOpen(true)}
            >
              <Plus className="mr-1 h-4 w-4" />
              Add
            </Button>
          </TooltipTrigger>
          <TooltipContent>
            <p>Add a step to the {title.toLowerCase()} section</p>
          </TooltipContent>
        </Tooltip>
      </div>

      {orderChanged && orderTestResult && (
        <div className="mb-3">
          <DirtyDiffResults
            result={orderTestResult}
            subject="the order change"
            onDismiss={onDismissTest}
          />
        </div>
      )}

      {!collapsed &&
        (rows.length === 0 ? (
          <p className="text-muted-foreground rounded-md border border-dashed p-4 text-center text-sm">
            No {title.toLowerCase()} configured.
          </p>
        ) : (
          <div>
            {rows.map((row, index) => {
              const key =
                row.type === 'entry' ? row.entry.uid : row.removed.entry.uid;
              return (
                <React.Fragment key={key}>
                  {index > 0 && (
                    <div
                      aria-hidden="true"
                      className="flex justify-center py-0.5"
                    >
                      <ArrowDown className="text-muted-foreground/50 h-4 w-4" />
                    </div>
                  )}
                  {row.type === 'entry' ? (
                    <ProcessorCard
                      entry={row.entry}
                      registryItem={registryByName.get(row.entry.name)}
                      issues={issuesByUid.get(row.entry.uid) ?? []}
                      status={statusByUid.get(row.entry.uid) ?? 'clean'}
                      baselineEntry={baselineByUid.get(row.entry.uid) ?? null}
                      canMoveUp={sectionEntries.indexOf(row.entry) > 0}
                      canMoveDown={
                        sectionEntries.indexOf(row.entry) <
                        sectionEntries.length - 1
                      }
                      isCommitting={isCommitting}
                      suggestions={suggestions}
                      onMove={(direction) => onMove(row.entry.uid, direction)}
                      onRemove={() => onRemove(row.entry.uid)}
                      onConfigChange={(config) =>
                        onConfigChange(row.entry.uid, config)
                      }
                      onYamlChange={(yaml) => onYamlChange(row.entry.uid, yaml)}
                      onToggleRawMode={(rawMode) =>
                        onToggleRawMode(row.entry.uid, rawMode)
                      }
                      onCommit={() =>
                        onCommitChange({ type: 'entry', uid: row.entry.uid })
                      }
                      onRevert={() => onRevertEntry(row.entry.uid)}
                      onTest={() =>
                        onTestChange({ type: 'entry', uid: row.entry.uid })
                      }
                      onTestRow={onTestChange}
                      onCommitRow={onCommitChange}
                      onRevertRow={onRevertRow}
                      onRestoreRemovedRow={onRestoreRemovedRow}
                      isTesting={isTesting}
                      testResult={testResult}
                      onDismissTest={onDismissTest}
                    />
                  ) : (
                    <TombstoneRow
                      removed={row.removed}
                      label={
                        registryByName.get(row.removed.entry.name)?.label ??
                        row.removed.entry.name
                      }
                      isCommitting={isCommitting}
                      isTesting={isTesting}
                      testResult={resultFor({
                        type: 'removal',
                        uid: row.removed.entry.uid,
                      })}
                      onDismissTest={onDismissTest}
                      onCommit={() =>
                        onCommitChange({
                          type: 'removal',
                          uid: row.removed.entry.uid,
                        })
                      }
                      onRestore={() => onRestoreRemoved(row.removed.entry.uid)}
                      onTest={() =>
                        onTestChange({
                          type: 'removal',
                          uid: row.removed.entry.uid,
                        })
                      }
                    />
                  )}
                </React.Fragment>
              );
            })}
          </div>
        ))}

      <AddProcessorDialog
        open={addOpen}
        onOpenChange={setAddOpen}
        registryItems={registryItems}
        existingNames={sectionEntries.map((entry) => entry.name)}
        onAdd={(name) => {
          onAdd(name);
          setAddOpen(false);
          setCollapsed(false);
        }}
      />
    </section>
  );
};

interface TombstoneRowProps {
  removed: RemovedEntry;
  label: string;
  isCommitting: boolean;
  isTesting: boolean;
  testResult: TextProcessorPreviewDiff | null;
  onDismissTest: () => void;
  onCommit: () => void;
  onRestore: () => void;
  onTest: () => void;
}

/** A pending (uncommitted) removal, kept visible where the entry used to be */
const TombstoneRow: React.FC<TombstoneRowProps> = ({
  removed,
  label,
  isCommitting,
  isTesting,
  testResult,
  onDismissTest,
  onCommit,
  onRestore,
  onTest,
}) => (
  <div className="space-y-2">
    <div className="border-muted-foreground/40 bg-muted/30 flex items-center justify-between gap-2 rounded-md border border-dashed px-4 py-2 opacity-80">
      <div className="flex min-w-0 items-center gap-2">
        <span className="truncate font-medium line-through">{label}</span>
        <Badge variant="outline" className="font-mono text-[10px]">
          {removed.entry.name}
        </Badge>
        <Badge
          variant="outline"
          className="border-destructive/50 text-destructive text-[10px]"
        >
          removed
        </Badge>
      </div>
      <div className="flex shrink-0 items-center gap-1">
        <InlineIconButton
          label="Test removal"
          onClick={onTest}
          disabled={isTesting}
        >
          <FlaskConical className="h-3.5 w-3.5" />
        </InlineIconButton>
        <InlineIconButton
          label="Save removal"
          onClick={onCommit}
          disabled={isCommitting}
          className="text-green-600 hover:text-green-700"
        >
          <Check className="h-3.5 w-3.5" />
        </InlineIconButton>
        <InlineIconButton
          label="Restore"
          onClick={onRestore}
          disabled={isCommitting}
        >
          <RotateCcw className="h-3.5 w-3.5" />
        </InlineIconButton>
      </div>
    </div>
    {testResult && (
      <DirtyDiffResults
        result={testResult}
        subject="this removal"
        onDismiss={onDismissTest}
      />
    )}
  </div>
);
