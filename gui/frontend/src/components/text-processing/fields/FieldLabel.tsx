import { HelpCircle } from 'lucide-react';
import React from 'react';

import { Label } from '@/components/ui/label';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';

interface FieldLabelProps {
  label: string;
  /** Field help text, shown behind a "?" tooltip when present */
  description?: string | undefined;
  /** Marks the field's value as differing from what's saved on disk */
  changed?: boolean | undefined;
  className?: string;
}

/**
 * A form field label with an optional "?" help tooltip fed by the field's
 * schema description (so e.g. "Replace pattern" can explain itself), and an
 * amber dot when the field's value has unsaved changes.
 */
export const FieldLabel: React.FC<FieldLabelProps> = ({
  label,
  description,
  changed = false,
  className = 'text-xs',
}) => (
  <div className="flex items-center gap-1">
    <Label className={className}>{label}</Label>
    {changed && (
      <span
        className="size-1.5 shrink-0 rounded-full bg-amber-500"
        aria-label="Unsaved change"
      />
    )}
    {description && (
      <Tooltip>
        <TooltipTrigger asChild>
          <span className="cursor-help" aria-label={`About ${label}`}>
            <HelpCircle className="text-muted-foreground h-3 w-3" />
          </span>
        </TooltipTrigger>
        <TooltipContent className="max-w-xs">
          <p className="font-normal whitespace-pre-wrap">{description}</p>
        </TooltipContent>
      </Tooltip>
    )}
  </div>
);
