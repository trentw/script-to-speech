import { X } from 'lucide-react';
import React from 'react';

import { appButtonVariants } from '@/components/ui/button-variants';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';

import { ProviderAvatar } from './ProviderAvatar';

interface VoiceCardHeaderProps {
  provider: string;
  title: string;
  subtitle?: string;
  icon?: React.ReactNode;
  onRemove?: () => void;
  showRemoveButton?: boolean;
  actions?: React.ReactNode;
}

export function VoiceCardHeader({
  provider,
  title,
  subtitle,
  icon,
  onRemove,
  showRemoveButton,
  actions,
}: VoiceCardHeaderProps) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex min-w-0 flex-1 items-center gap-3">
        {showRemoveButton && onRemove && (
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                className={appButtonVariants({
                  variant: 'list-action',
                  size: 'icon-sm',
                })}
                onClick={(e) => {
                  e.stopPropagation();
                  onRemove();
                }}
              >
                <X className="h-3 w-3" />
              </button>
            </TooltipTrigger>
            <TooltipContent>
              <p>Remove voice assignment</p>
            </TooltipContent>
          </Tooltip>
        )}
        <ProviderAvatar provider={provider} size="sm" />
        <div className="min-w-0 flex-1 space-y-1">
          <div className="flex items-center gap-2">
            <p className="text-sm font-medium">{title}</p>
            {icon}
          </div>
          {subtitle && (
            <p className="text-muted-foreground text-xs">{subtitle}</p>
          )}
        </div>
      </div>
      {actions && <div className="flex items-center gap-1">{actions}</div>}
    </div>
  );
}
