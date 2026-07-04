import React from 'react';

import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';

import type {
  FieldSpec,
  TextProcessorPreviewDiff,
} from '../../../types/text-processing';
import type { ListFieldDiff } from '../editorState';
import { ObjectListField } from './ObjectListField';
import { SpeakerMapField } from './SpeakerMapField';
import { StringListField } from './StringListField';

export interface SuggestionSources {
  chunk_types: string[];
  chunk_fields: string[];
}

interface FieldInputProps {
  field: FieldSpec;
  value: unknown;
  onChange: (value: unknown) => void;
  suggestions: SuggestionSources;
  /** Per-row dirty statuses when this is a list-of-object field */
  fieldDiff?: ListFieldDiff | undefined;
  /** Per-row test/save wiring, scoped to this field by the parent form */
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

/**
 * Schema-driven input dispatcher: renders the right composable field
 * component for a FieldSpec (the FieldRenderer pattern, extended with the
 * text processor primitives).
 */
export const FieldInput: React.FC<FieldInputProps> = ({
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
  canCommitRows,
  onDismissTest,
}) => {
  const suggestionsFor = (ref?: string): string[] | undefined =>
    ref === 'chunk_types'
      ? suggestions.chunk_types
      : ref === 'chunk_fields'
        ? suggestions.chunk_fields
        : undefined;

  switch (field.type) {
    case 'string': {
      // Fields referencing a known finite set (chunk types/fields) are
      // pick-only: free text could never match anything at runtime
      const options = suggestionsFor(field.suggestions_ref);
      if (options && options.length > 0) {
        const current = (value as string) ?? '';
        // A hand-edited config may hold a value outside the known set; keep
        // it selectable so the Select doesn't render empty
        const items =
          current !== '' && !options.includes(current)
            ? [current, ...options]
            : options;
        return (
          <Select value={current} onValueChange={(next) => onChange(next)}>
            <SelectTrigger className="h-8 w-56 text-sm">
              <SelectValue placeholder="Select…" />
            </SelectTrigger>
            <SelectContent>
              {items.map((option) => (
                <SelectItem key={option} value={option}>
                  {option}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        );
      }
      return (
        <Input
          value={(value as string) ?? ''}
          placeholder={field.format === 'regex' ? 'Regular expression' : ''}
          className={`h-8 text-sm ${field.format === 'regex' ? 'font-mono' : ''}`}
          onChange={(e) =>
            onChange(
              e.target.value === '' && !field.required
                ? undefined
                : e.target.value
            )
          }
        />
      );
    }

    case 'integer':
      return (
        <Input
          type="number"
          value={value === undefined || value === null ? '' : String(value)}
          min={field.min}
          className="h-8 w-32 text-sm"
          onChange={(e) => {
            const raw = e.target.value;
            onChange(raw === '' ? undefined : Number(raw));
          }}
        />
      );

    case 'boolean':
      return (
        <Switch
          checked={Boolean(value)}
          onCheckedChange={(checked) => onChange(checked)}
        />
      );

    case 'enum':
      return (
        <Select
          value={(value as string) ?? ''}
          onValueChange={(next) => onChange(next)}
        >
          <SelectTrigger className="h-8 w-48 text-sm">
            <SelectValue placeholder="Select…" />
          </SelectTrigger>
          <SelectContent>
            {(field.enum || []).map((option) => (
              <SelectItem key={option} value={option}>
                {option.replace(/_/g, ' ')}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      );

    case 'list':
      if (field.item_schema?.type === 'object') {
        return (
          <ObjectListField
            field={field}
            value={(value as Record<string, unknown>[]) ?? []}
            onChange={(next) => onChange(next)}
            suggestions={suggestions}
            fieldDiff={fieldDiff}
            onTestRow={onTestRow}
            rowTestResultFor={rowTestResultFor}
            onCommitRow={onCommitRow}
            onRevertRow={onRevertRow}
            onRestoreRemovedRow={onRestoreRemovedRow}
            isTesting={isTesting}
            isCommitting={isCommitting}
            canCommitRows={canCommitRows}
            onDismissTest={onDismissTest}
          />
        );
      }
      return (
        <StringListField
          value={(value as string[]) ?? []}
          onChange={(next) =>
            onChange(next.length === 0 && !field.required ? undefined : next)
          }
          suggestions={suggestionsFor(field.item_schema?.suggestions_ref)}
        />
      );

    case 'dict_of_string_lists':
      return (
        <SpeakerMapField
          value={(value as Record<string, string[]>) ?? {}}
          onChange={(next) => onChange(next)}
        />
      );

    default:
      return (
        <p className="text-muted-foreground text-xs">
          Unsupported field type: {field.type}
        </p>
      );
  }
};
