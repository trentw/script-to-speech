import { X } from 'lucide-react';
import React, { useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';

interface StringListFieldProps {
  value: string[];
  onChange: (value: string[]) => void;
  suggestions?: string[] | undefined;
  placeholder?: string | undefined;
}

/**
 * Chip-style editor for a list of strings. With suggestions (a known finite
 * set like chunk types) items are pick-only: selecting from the dropdown adds
 * immediately, and used-up options disappear from it. Without suggestions
 * (free-form patterns) it stays a text input.
 */
export const StringListField: React.FC<StringListFieldProps> = ({
  value,
  onChange,
  suggestions,
  placeholder,
}) => {
  const [draft, setDraft] = useState('');

  const addDraft = () => {
    const trimmed = draft.trim();
    if (!trimmed || value.includes(trimmed)) {
      setDraft('');
      return;
    }
    onChange([...value, trimmed]);
    setDraft('');
  };

  const available = (suggestions ?? []).filter(
    (option) => !value.includes(option)
  );

  return (
    <div className="space-y-2">
      {value.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {value.map((item) => (
            <Badge key={item} variant="secondary" className="gap-1 font-mono">
              {item}
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    type="button"
                    aria-label={`Remove ${item}`}
                    className="hover:text-destructive"
                    onClick={() => onChange(value.filter((v) => v !== item))}
                  >
                    <X className="h-3 w-3" />
                  </button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Remove {item}</p>
                </TooltipContent>
              </Tooltip>
            </Badge>
          ))}
        </div>
      )}

      {suggestions ? (
        available.length > 0 && (
          <Select
            value=""
            onValueChange={(option) => onChange([...value, option])}
          >
            <SelectTrigger className="h-8 w-56 text-sm">
              <SelectValue placeholder={placeholder || 'Add item…'} />
            </SelectTrigger>
            <SelectContent>
              {available.map((option) => (
                <SelectItem key={option} value={option}>
                  {option}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )
      ) : (
        <div className="flex gap-2">
          <Input
            value={draft}
            placeholder={placeholder || 'Add item…'}
            className="h-8 text-sm"
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault();
                addDraft();
              }
            }}
          />
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={addDraft}
            disabled={!draft.trim()}
          >
            Add
          </Button>
        </div>
      )}
    </div>
  );
};
