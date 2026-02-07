import { Check, Edit2, X } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';

import { appButtonVariants } from '@/components/ui/button-variants';
import { Input } from '@/components/ui/input';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { useUpdateId3TagConfig } from '@/hooks/mutations/useUpdateId3TagConfig';
import { useId3TagConfig } from '@/hooks/queries/useId3TagConfig';

/**
 * Validate that a year string is exactly 4 digits (e.g. "2025").
 * Returns an error message or null if valid. Empty string is valid (field is optional).
 */
export function validateYear(value: string): string | null {
  if (value === '') return null;
  if (!/^\d{4}$/.test(value)) return 'Year must be 4 digits';
  return null;
}

// ─── Per-field inline editor ────────────────────────────────────────────────

interface InlineFieldProps {
  label: string;
  value: string;
  placeholder: string;
  /** Use font-medium for the display value (e.g. title field) */
  bold?: boolean;
  validate?: (v: string) => string | null;
  onSave: (value: string) => void;
  id?: string;
  compact?: boolean;
}

function InlineField({
  label,
  value,
  placeholder,
  bold,
  validate,
  onSave,
  id,
  compact,
}: InlineFieldProps) {
  const [editing, setEditing] = useState(false);
  const [localValue, setLocalValue] = useState(value);
  const [error, setError] = useState<string | null>(null);

  // Sync display value from server when not editing
  useEffect(() => {
    if (!editing) setLocalValue(value);
  }, [value, editing]);

  const handleEdit = () => {
    setLocalValue(value);
    setError(null);
    setEditing(true);
  };

  const handleCancel = () => {
    setLocalValue(value);
    setError(null);
    setEditing(false);
  };

  const handleSave = () => {
    if (validate) {
      const err = validate(localValue);
      if (err) {
        setError(err);
        return;
      }
    }
    if (localValue !== value) {
      onSave(localValue);
    }
    setError(null);
    setEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSave();
    if (e.key === 'Escape') handleCancel();
  };

  const labelClass = compact
    ? 'text-muted-foreground text-xs font-medium'
    : 'text-muted-foreground text-sm font-medium';

  // The pencil button is w-7 (1.75rem) + gap-1.5 (0.375rem) = 2.125rem.
  // We offset the label and editing row by this amount so they align with the
  // value text rather than with the pencil icon.
  const inlineOffset = 'pl-[2.125rem]';

  // Overflow detection for tooltip (hooks must be above the early return)
  const hasValue = value !== '';
  const textRef = useRef<HTMLParagraphElement>(null);
  const [isOverflowing, setIsOverflowing] = useState(false);

  const checkOverflow = useCallback(() => {
    const el = textRef.current;
    if (el) {
      setIsOverflowing(el.scrollWidth > el.clientWidth);
    }
  }, []);

  useEffect(() => {
    checkOverflow();
    window.addEventListener('resize', checkOverflow);
    return () => window.removeEventListener('resize', checkOverflow);
  }, [checkOverflow, value]);

  if (editing) {
    return (
      <div className="space-y-1">
        <div className={`${labelClass} ${inlineOffset}`}>{label}</div>
        <div className={`flex items-center gap-1 ${inlineOffset}`}>
          <Input
            id={id}
            value={localValue}
            onChange={(e) => {
              setLocalValue(e.target.value);
              if (error) setError(null);
            }}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            className={`${compact ? 'h-8 text-sm' : ''} ${error ? 'border-red-400' : ''}`}
            autoFocus
          />
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                className={`${appButtonVariants({
                  variant: 'list-action',
                  size: 'icon-sm',
                })} shrink-0 text-green-600 hover:text-green-700`}
                onClick={handleSave}
              >
                <Check className="h-3.5 w-3.5" />
              </button>
            </TooltipTrigger>
            <TooltipContent>Save</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                className={`${appButtonVariants({
                  variant: 'list-action',
                  size: 'icon-sm',
                })} shrink-0`}
                onClick={handleCancel}
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </TooltipTrigger>
            <TooltipContent>Cancel</TooltipContent>
          </Tooltip>
        </div>
        {error && (
          <p className={`text-xs text-red-500 ${inlineOffset}`}>{error}</p>
        )}
      </div>
    );
  }

  const displayText = hasValue ? (
    <p
      ref={textRef}
      className={`min-w-0 truncate ${compact ? 'text-sm' : ''} ${bold ? 'font-medium' : ''}`}
    >
      {value}
    </p>
  ) : (
    <p
      ref={textRef}
      className={`text-muted-foreground min-w-0 truncate italic ${compact ? 'text-sm' : ''}`}
    >
      {placeholder}
    </p>
  );

  return (
    <div className="space-y-1">
      <div className={`${labelClass} ${inlineOffset}`}>{label}</div>
      <div className="flex items-center gap-1.5">
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              className={`${appButtonVariants({
                variant: 'list-action',
                size: 'icon-sm',
              })} shrink-0`}
              onClick={handleEdit}
            >
              <Edit2 className="h-3 w-3" />
            </button>
          </TooltipTrigger>
          <TooltipContent>Edit {label.toLowerCase()}</TooltipContent>
        </Tooltip>
        {isOverflowing && hasValue ? (
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="min-w-0">{displayText}</div>
            </TooltipTrigger>
            <TooltipContent side="bottom" className="max-w-xs">
              {value}
            </TooltipContent>
          </Tooltip>
        ) : (
          displayText
        )}
      </div>
    </div>
  );
}

// ─── Main editor component ──────────────────────────────────────────────────

interface Id3TagEditorProps {
  inputPath: string;
  screenplayName: string;
  /** Compact layout: single row with smaller labels (for generate page) */
  compact?: boolean;
  /** ID prefix for input elements to avoid id collisions */
  idPrefix?: string;
}

export function Id3TagEditor({
  inputPath,
  screenplayName,
  compact = false,
  idPrefix = 'id3',
}: Id3TagEditorProps) {
  const { config: id3Config } = useId3TagConfig(inputPath);
  const updateId3 = useUpdateId3TagConfig();

  const saveField = (field: string, value: string) => {
    updateId3.mutate({ inputPath, update: { [field]: value } });
  };

  const gridClass = compact
    ? 'grid grid-cols-1 gap-3 md:grid-cols-3'
    : 'grid grid-cols-1 gap-4 md:grid-cols-3';

  return (
    <div className={gridClass}>
      <InlineField
        label={compact ? 'Title' : 'Screenplay Title'}
        value={id3Config?.title ?? ''}
        placeholder={screenplayName}
        bold
        onSave={(v) => saveField('title', v)}
        id={`${idPrefix}-title`}
        compact={compact}
      />
      <InlineField
        label="Author"
        value={id3Config?.screenplayAuthor ?? ''}
        placeholder="Not set"
        onSave={(v) => saveField('screenplayAuthor', v)}
        id={`${idPrefix}-author`}
        compact={compact}
      />
      <InlineField
        label="Year"
        value={id3Config?.date ?? ''}
        placeholder="Not set"
        validate={validateYear}
        onSave={(v) => saveField('date', v)}
        id={`${idPrefix}-year`}
        compact={compact}
      />
    </div>
  );
}
