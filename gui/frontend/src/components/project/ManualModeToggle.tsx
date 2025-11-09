import { useNavigate, useRouter } from '@tanstack/react-router';
import React from 'react';

import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { useProject } from '@/stores/appStore';

interface ManualModeToggleProps {
  className?: string;
}

export function ManualModeToggle({ className }: ManualModeToggleProps) {
  const navigate = useNavigate();
  const router = useRouter();
  const projectState = useProject();
  const isManualMode = projectState.mode === 'manual';

  const handleToggle = (checked: boolean) => {
    if (checked) {
      // Switching to manual mode - update state and trigger guard re-evaluation
      projectState.setMode('manual');
      router.invalidate(); // Guard will redirect to /tts
    } else {
      // Switching to project mode - update state and navigate to welcome screen
      projectState.setMode('project');
      navigate({ to: '/project/welcome', replace: true });
    }
  };

  return (
    <div className={cn('manual-mode-toggle space-y-2', className)}>
      {/* Toggle with Label - shadcn pattern */}
      <Tooltip>
        <TooltipTrigger asChild>
          <div className="flex items-center space-x-2">
            <Switch
              id="manual-mode-switch"
              checked={isManualMode}
              onCheckedChange={handleToggle}
            />
            <Label
              htmlFor="manual-mode-switch"
              className="text-sm leading-none font-medium peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
            >
              Manual Mode
            </Label>
          </div>
        </TooltipTrigger>
        <TooltipContent side="right" sideOffset={8}>
          <p className="max-w-xs">
            Use screenplay tools in a one-off fashion, separate from a
            screenplay project
          </p>
        </TooltipContent>
      </Tooltip>

      {/* Status Text */}
      <div className="text-muted-foreground text-xs">
        {isManualMode ? 'Enabled' : 'Disabled'}
      </div>
    </div>
  );
}
