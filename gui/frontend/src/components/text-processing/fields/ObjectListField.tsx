import {
  Check,
  ChevronDown,
  FlaskConical,
  Plus,
  RotateCcw,
  Trash2,
  Undo2,
} from 'lucide-react';
import React, { useState } from 'react';

import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

import type {
  FieldSpec,
  TextProcessorPreviewDiff,
} from '../../../types/text-processing';
import { DirtyDiffResults } from '../DirtyDiffResults';
import {
  type ListFieldDiff,
  type RemovedRow,
  ROW_UID_KEY,
  type RowStatus,
} from '../editorState';
import { InlineIconButton } from '../InlineIconButton';
import { FieldInput, type SuggestionSources } from './FieldInput';
import { FieldLabel } from './FieldLabel';

interface ObjectListFieldProps {
  field: FieldSpec;
  value: Record<string, unknown>[];
  onChange: (value: Record<string, unknown>[]) => void;
  suggestions: SuggestionSources;
  /** Per-row dirty statuses vs the on-disk baseline, when available */
  fieldDiff?: ListFieldDiff | undefined;
  /** Per-row test/save wiring, scoped to this field (removal=true for ghosts) */
  onTestRow?: ((rowUid: string, removal: boolean) => void) | undefined;
  rowTestResultFor?:
    | ((rowUid: string, removal: boolean) => TextProcessorPreviewDiff | null)
    | undefined;
  onCommitRow?: ((rowUid: string, removal: boolean) => void) | undefined;
  onRevertRow?: ((rowUid: string) => void) | undefined;
  onRestoreRemovedRow?: ((rowUid: string) => void) | undefined;
  isTesting?: boolean | undefined;
  isCommitting?: boolean | undefined;
  canCommitRows?: boolean | undefined;
  onDismissTest?: (() => void) | undefined;
}

type RenderRow =
  | { type: 'row'; row: Record<string, unknown>; index: number }
  | { type: 'ghost'; removed: RemovedRow };

const rowKey = (row: Record<string, unknown>, index: number): string =>
  typeof row[ROW_UID_KEY] === 'string'
    ? (row[ROW_UID_KEY] as string)
    : `index-${index}`;

/** Compact one-line description of a row, for removed-row ghosts */
const summarizeRow = (row: Record<string, unknown>): string =>
  Object.entries(row)
    .filter(
      ([key, v]) =>
        key !== ROW_UID_KEY &&
        key !== 'notes' &&
        (typeof v === 'string' || typeof v === 'number') &&
        String(v) !== ''
    )
    .map(([key, v]) => `${key}: ${JSON.stringify(v)}`)
    .join('  ·  ');

/**
 * Row-based editor for lists of objects (substitutions, replacements,
 * transformations). Each row renders its nested fields from the item schema;
 * nested fields marked advanced sit behind a per-row collapse. A row's
 * optional `notes` value is surfaced as a caption even while Advanced is
 * collapsed. Rows that differ from the saved config get an amber edge, and
 * rows deleted since the last save stay visible as ghost rows.
 */
export const ObjectListField: React.FC<ObjectListFieldProps> = ({
  field,
  value,
  onChange,
  suggestions,
  fieldDiff,
  onTestRow,
  rowTestResultFor,
  onCommitRow,
  onRevertRow,
  onRestoreRemovedRow,
  isTesting,
  isCommitting,
  canCommitRows = true,
  onDismissTest,
}) => {
  const [expandedAdvanced, setExpandedAdvanced] = useState<Set<string>>(
    new Set()
  );

  const itemFields = field.item_schema?.fields || [];
  const basicFields = itemFields.filter((f) => !f.advanced);
  const advancedFields = itemFields.filter((f) => f.advanced);

  const updateRow = (index: number, name: string, fieldValue: unknown) => {
    const next = value.map((row, i) => {
      if (i !== index) return row;
      const updated = { ...row };
      if (fieldValue === undefined) {
        delete updated[name];
      } else {
        updated[name] = fieldValue;
      }
      return updated;
    });
    onChange(next);
  };

  const addRow = () => {
    const row: Record<string, unknown> = {};
    for (const itemField of itemFields) {
      if (itemField.default !== undefined) {
        row[itemField.name] = itemField.default;
      } else if (itemField.required) {
        row[itemField.name] = itemField.type === 'list' ? [] : '';
      }
    }
    onChange([...value, row]);
  };

  const toggleAdvanced = (key: string) => {
    setExpandedAdvanced((current) => {
      const next = new Set(current);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  // Interleave removed-row ghosts after the surviving row they used to follow
  const removedRows = fieldDiff?.removedRows ?? [];
  const renderRows: RenderRow[] = [];
  for (const removed of removedRows.filter((r) => r.afterRowUid === null)) {
    renderRows.push({ type: 'ghost', removed });
  }
  value.forEach((row, index) => {
    renderRows.push({ type: 'row', row, index });
    const uid = row[ROW_UID_KEY];
    if (typeof uid === 'string') {
      for (const removed of removedRows.filter((r) => r.afterRowUid === uid)) {
        renderRows.push({ type: 'ghost', removed });
      }
    }
  });

  return (
    <div className="space-y-2">
      {renderRows.map((item) => {
        if (item.type === 'ghost') {
          const ghostResult = rowTestResultFor?.(item.removed.uid, true);
          return (
            <div key={`ghost-${item.removed.uid}`} className="space-y-2">
              <div className="border-muted-foreground/40 bg-muted/30 flex items-center justify-between gap-2 rounded-md border border-dashed px-3 py-1.5 opacity-80">
                <span className="text-muted-foreground truncate font-mono text-xs line-through">
                  {summarizeRow(item.removed.row) || '(empty row)'}
                </span>
                <span className="flex shrink-0 items-center gap-1">
                  <span className="text-destructive text-[10px] font-medium">
                    removed
                  </span>
                  {onTestRow && (
                    <InlineIconButton
                      label="Test removing this item"
                      onClick={() => onTestRow(item.removed.uid, true)}
                      disabled={isTesting ?? false}
                    >
                      <FlaskConical className="h-3.5 w-3.5" />
                    </InlineIconButton>
                  )}
                  {onCommitRow && (
                    <InlineIconButton
                      label="Save this removal"
                      onClick={() => onCommitRow(item.removed.uid, true)}
                      disabled={(isCommitting ?? false) || !canCommitRows}
                      className="text-green-600 hover:text-green-700"
                    >
                      <Check className="h-3.5 w-3.5" />
                    </InlineIconButton>
                  )}
                  {onRestoreRemovedRow && (
                    <InlineIconButton
                      label="Restore this item"
                      onClick={() => onRestoreRemovedRow(item.removed.uid)}
                      disabled={isCommitting ?? false}
                    >
                      <RotateCcw className="h-3.5 w-3.5" />
                    </InlineIconButton>
                  )}
                </span>
              </div>
              {ghostResult && (
                <DirtyDiffResults
                  result={ghostResult}
                  subject="removing this item"
                  onDismiss={onDismissTest ?? (() => undefined)}
                />
              )}
            </div>
          );
        }

        const { row, index } = item;
        const key = rowKey(row, index);
        const rowUid =
          typeof row[ROW_UID_KEY] === 'string'
            ? (row[ROW_UID_KEY] as string)
            : null;
        const status: RowStatus = rowUid
          ? (fieldDiff?.statusByRowUid.get(rowUid) ?? 'clean')
          : 'clean';
        const rowResult =
          rowUid && status !== 'clean'
            ? rowTestResultFor?.(rowUid, false)
            : null;

        return (
          <div
            key={key}
            className={cn(
              'bg-muted/30 rounded-md border p-3',
              status !== 'clean' && 'border-l-2 border-l-amber-500'
            )}
          >
            {typeof row.notes === 'string' && row.notes.trim() !== '' && (
              <p className="text-muted-foreground mb-2 text-xs italic">
                {row.notes}
              </p>
            )}

            <div className="grid gap-3 sm:grid-cols-2">
              {basicFields.map((itemField) => (
                <div key={itemField.name} className="space-y-1">
                  <FieldLabel
                    label={itemField.label || itemField.name}
                    description={itemField.description}
                  />
                  <FieldInput
                    field={itemField}
                    value={row[itemField.name]}
                    onChange={(next) => updateRow(index, itemField.name, next)}
                    suggestions={suggestions}
                  />
                </div>
              ))}
            </div>

            <div className="mt-2 flex items-center justify-between">
              {advancedFields.length > 0 ? (
                <button
                  type="button"
                  className="text-muted-foreground hover:text-foreground flex items-center gap-1 text-xs"
                  onClick={() => toggleAdvanced(key)}
                >
                  <ChevronDown
                    className={`h-3 w-3 transition-transform ${
                      expandedAdvanced.has(key) ? 'rotate-180' : ''
                    }`}
                  />
                  Advanced
                </button>
              ) : (
                <span />
              )}
              <span className="flex items-center gap-1">
                {status !== 'clean' && rowUid && (
                  <>
                    {onTestRow && (
                      <InlineIconButton
                        label="Test this item's change"
                        onClick={() => onTestRow(rowUid, false)}
                        disabled={isTesting ?? false}
                      >
                        <FlaskConical className="h-3.5 w-3.5" />
                      </InlineIconButton>
                    )}
                    {onCommitRow && (
                      <InlineIconButton
                        label="Save this item's change"
                        onClick={() => onCommitRow(rowUid, false)}
                        disabled={(isCommitting ?? false) || !canCommitRows}
                        className="text-green-600 hover:text-green-700"
                      >
                        <Check className="h-3.5 w-3.5" />
                      </InlineIconButton>
                    )}
                    {onRevertRow && (
                      <InlineIconButton
                        label="Discard this item's change"
                        onClick={() => onRevertRow(rowUid)}
                        disabled={isCommitting ?? false}
                        className="text-destructive hover:text-destructive"
                      >
                        <Undo2 className="h-3.5 w-3.5" />
                      </InlineIconButton>
                    )}
                  </>
                )}
                <InlineIconButton
                  label="Remove row"
                  onClick={() => onChange(value.filter((_, i) => i !== index))}
                  className="text-destructive hover:text-destructive"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </InlineIconButton>
              </span>
            </div>

            {expandedAdvanced.has(key) && advancedFields.length > 0 && (
              <div className="mt-2 grid gap-3 border-t pt-3 sm:grid-cols-2">
                {advancedFields.map((itemField) => (
                  <div key={itemField.name} className="space-y-1">
                    <FieldLabel
                      label={itemField.label || itemField.name}
                      description={itemField.description}
                    />
                    <FieldInput
                      field={itemField}
                      value={row[itemField.name]}
                      onChange={(next) =>
                        updateRow(index, itemField.name, next)
                      }
                      suggestions={suggestions}
                    />
                  </div>
                ))}
              </div>
            )}

            {rowResult && (
              <div className="mt-2">
                <DirtyDiffResults
                  result={rowResult}
                  subject="this item's change"
                  onDismiss={onDismissTest ?? (() => undefined)}
                />
              </div>
            )}
          </div>
        );
      })}

      <Button type="button" variant="outline" size="sm" onClick={addRow}>
        <Plus className="mr-1 h-4 w-4" />
        Add {field.label ? field.label.replace(/s$/, '').toLowerCase() : 'row'}
      </Button>
    </div>
  );
};
