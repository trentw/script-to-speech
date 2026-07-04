import React from 'react';

import {
  appButtonVariants,
  buttonUtils,
} from '@/components/ui/button-variants';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

interface InlineIconButtonProps {
  /** Tooltip text; doubles as the accessible label */
  label: string;
  onClick: () => void;
  disabled?: boolean;
  className?: string;
  children: React.ReactNode;
}

/**
 * The review-audio inline action idiom: a tooltip-wrapped list-action icon
 * button. Disabled state uses aria-disabled (not the native attribute) so the
 * tooltip still explains the button when it can't be clicked.
 */
export const InlineIconButton: React.FC<InlineIconButtonProps> = ({
  label,
  onClick,
  disabled = false,
  className,
  children,
}) => (
  <Tooltip>
    <TooltipTrigger asChild>
      <button
        type="button"
        aria-label={label}
        aria-disabled={disabled || undefined}
        className={cn(
          appButtonVariants({ variant: 'list-action', size: 'icon-sm' }),
          disabled && buttonUtils.ariaDisabled,
          className
        )}
        onClick={() => {
          if (!disabled) onClick();
        }}
      >
        {children}
      </button>
    </TooltipTrigger>
    <TooltipContent>
      <p>{label}</p>
    </TooltipContent>
  </Tooltip>
);
