import React from 'react';

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';

import type {
  FieldSpec,
  ProcessorSchema,
  TextProcessorPreviewDiff,
} from '../../types/text-processing';
import type { ListFieldDiff } from './editorState';
import { FieldInput, type SuggestionSources } from './fields/FieldInput';
import { FieldLabel } from './fields/FieldLabel';

interface ProcessorConfigFormProps {
  schema: ProcessorSchema;
  config: Record<string, unknown>;
  onChange: (config: Record<string, unknown>) => void;
  suggestions: SuggestionSources;
  /** Per-row dirty statuses by list field name (entries with edits only) */
  rowDiff?: Map<string, ListFieldDiff> | undefined;
  /** Non-list fields whose value differs from the saved config */
  changedFields?: Set<string> | undefined;
  /** Per-row test/save wiring (removal=true for deleted-row ghosts) */
  onTestRow?:
    | ((field: string, rowUid: string, removal: boolean) => void)
    | undefined;
  rowTestResultFor?:
    | ((
        field: string,
        rowUid: string,
        removal: boolean
      ) => TextProcessorPreviewDiff | null)
    | undefined;
  onCommitRow?:
    | ((field: string, rowUid: string, removal: boolean) => void)
    | undefined;
  onRevertRow?: ((field: string, rowUid: string) => void) | undefined;
  onRestoreRemovedRow?: ((field: string, rowUid: string) => void) | undefined;
  isTesting?: boolean | undefined;
  isCommitting?: boolean | undefined;
  /** False while the entry has validation issues (blocks row saves) */
  canCommitRows?: boolean | undefined;
  onDismissTest?: (() => void) | undefined;
}

/**
 * Schema-driven form for a processor's config. Top-level fields marked
 * advanced collapse into an Advanced section; fields sharing an xor_group
 * (e.g. extract_only / extract_all_except) clear each other when set.
 */
export const ProcessorConfigForm: React.FC<ProcessorConfigFormProps> = ({
  schema,
  config,
  onChange,
  suggestions,
  rowDiff,
  changedFields,
  onTestRow,
  rowTestResultFor,
  onCommitRow,
  onRevertRow,
  onRestoreRemovedRow,
  isTesting,
  isCommitting,
  canCommitRows,
  onDismissTest,
}) => {
  const basicFields = schema.fields.filter((field) => !field.advanced);
  const advancedFields = schema.fields.filter((field) => field.advanced);

  const updateField = (field: FieldSpec, value: unknown) => {
    const next = { ...config };
    if (value === undefined) {
      delete next[field.name];
    } else {
      next[field.name] = value;
      // Fields in the same xor group are mutually exclusive
      if (field.xor_group) {
        for (const other of schema.fields) {
          if (
            other.xor_group === field.xor_group &&
            other.name !== field.name
          ) {
            delete next[other.name];
          }
        }
      }
    }
    onChange(next);
  };

  const renderField = (field: FieldSpec) => (
    <div key={field.name} className="space-y-1">
      <FieldLabel
        label={field.label || field.name}
        description={field.description}
        changed={changedFields?.has(field.name)}
        className="text-sm"
      />
      <FieldInput
        field={field}
        value={config[field.name]}
        onChange={(value) => updateField(field, value)}
        suggestions={suggestions}
        fieldDiff={rowDiff?.get(field.name)}
        onTestRow={
          onTestRow
            ? (rowUid, removal) => onTestRow(field.name, rowUid, removal)
            : undefined
        }
        rowTestResultFor={
          rowTestResultFor
            ? (rowUid, removal) => rowTestResultFor(field.name, rowUid, removal)
            : undefined
        }
        onCommitRow={
          onCommitRow
            ? (rowUid, removal) => onCommitRow(field.name, rowUid, removal)
            : undefined
        }
        onRevertRow={
          onRevertRow ? (rowUid) => onRevertRow(field.name, rowUid) : undefined
        }
        onRestoreRemovedRow={
          onRestoreRemovedRow
            ? (rowUid) => onRestoreRemovedRow(field.name, rowUid)
            : undefined
        }
        isTesting={isTesting}
        isCommitting={isCommitting}
        canCommitRows={canCommitRows}
        onDismissTest={onDismissTest}
      />
    </div>
  );

  return (
    <div className="space-y-4">
      {basicFields.map(renderField)}

      {advancedFields.length > 0 && (
        <Accordion type="single" collapsible>
          <AccordionItem value="advanced" className="border-none">
            <AccordionTrigger className="text-muted-foreground py-1 text-xs">
              Advanced options
            </AccordionTrigger>
            <AccordionContent className="space-y-4 pt-2">
              {advancedFields.map(renderField)}
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      )}
    </div>
  );
};
