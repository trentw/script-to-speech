import React from 'react';

import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

import type { RegistryProcessor } from '../../types/text-processing';

interface AddProcessorDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  registryItems: RegistryProcessor[];
  existingNames: string[];
  onAdd: (name: string) => void;
}

/**
 * Registry-driven picker for adding a processor to the pipeline.
 * Override-mode processors (single instance) are disabled when already present.
 */
export const AddProcessorDialog: React.FC<AddProcessorDialogProps> = ({
  open,
  onOpenChange,
  registryItems,
  existingNames,
  onAdd,
}) => {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Add processing step</DialogTitle>
          <DialogDescription>
            Steps run in order; the output of one is the input to the next.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-2">
          {registryItems.map((item) => {
            const blocked =
              item.multi_config_mode === 'override' &&
              existingNames.includes(item.name);
            return (
              <button
                key={item.name}
                type="button"
                disabled={blocked}
                className="hover:bg-accent w-full rounded-md border p-3 text-left transition-colors disabled:cursor-not-allowed disabled:opacity-50"
                onClick={() => onAdd(item.name)}
              >
                <div className="flex items-center gap-2">
                  <span className="font-medium">{item.label}</span>
                  <Badge variant="outline" className="font-mono text-[10px]">
                    {item.name}
                  </Badge>
                </div>
                <p className="text-muted-foreground mt-1 text-xs">
                  {item.description}
                </p>
                {blocked && (
                  <p className="text-muted-foreground mt-1 text-xs italic">
                    Already in the pipeline — this step only supports a single
                    instance.
                  </p>
                )}
              </button>
            );
          })}
        </div>
      </DialogContent>
    </Dialog>
  );
};
