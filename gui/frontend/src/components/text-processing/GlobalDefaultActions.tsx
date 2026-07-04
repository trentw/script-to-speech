import { ChevronDown, Download, RotateCcw, Save, Undo2 } from 'lucide-react';
import React, { useState } from 'react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

import {
  useDeleteTextProcessorGlobalDefault,
  useUpdateTextProcessorGlobalDefault,
} from '../../hooks/mutations/useTextProcessorGlobalDefaultMutations';
import { useTextProcessorGlobalDefault } from '../../hooks/queries/useTextProcessorGlobalDefault';
import type { EntryPayload } from '../../services/textProcessorApi';
import type {
  TextProcessorEntry,
  TextProcessorMetadata,
} from '../../types/text-processing';

interface GlobalDefaultActionsProps {
  /** Current buffer entries (what "Save as my default" persists) */
  getEntries: () => EntryPayload[];
  /** Metadata of the project config (for provenance hash carry-forward) */
  metadata: TextProcessorMetadata | null;
  /** Replace the buffer with other entries (Load my default) */
  onLoadEntries: (entries: TextProcessorEntry[]) => void;
  /** Re-seed this project's config from the shipped defaults */
  onResetProject: () => void;
  /** Whether the buffer has unsaved edits (guards destructive Load) */
  isDirty: boolean;
}

type ConfirmAction =
  | 'save-default'
  | 'reset-project'
  | 'clear-default'
  | 'load-default'
  | null;

const CONFIRM_COPY: Record<
  Exclude<ConfirmAction, null>,
  { title: string; description: string; confirmLabel: string }
> = {
  'save-default': {
    title: 'Save as my default configuration?',
    description:
      'This pipeline will seed the text processor config of screenplays you parse in the future. Screenplays that already have a config are not affected.',
    confirmLabel: 'Save default',
  },
  'reset-project': {
    title: 'Reset this project to the built-in defaults?',
    description:
      "This discards this project's text processor customizations and re-seeds the config from the built-in defaults.",
    confirmLabel: 'Reset config',
  },
  'clear-default': {
    title: 'Remove my default configuration?',
    description:
      'Future screenplays will seed from the built-in defaults again. Existing projects are not affected.',
    confirmLabel: 'Remove default',
  },
  'load-default': {
    title: 'Discard your unsaved changes?',
    description:
      'Loading your default configuration replaces the pipeline below, discarding the unsaved changes you have made in this project.',
    confirmLabel: 'Load default',
  },
};

/**
 * Header menu for global-default management: save the current pipeline as
 * the user's default for future screenplays, load that default into this
 * project, or reset either back to the shipped defaults.
 */
export const GlobalDefaultActions: React.FC<GlobalDefaultActionsProps> = ({
  getEntries,
  metadata,
  onLoadEntries,
  onResetProject,
  isDirty,
}) => {
  const [confirmAction, setConfirmAction] = useState<ConfirmAction>(null);

  const { data: globalDefault } = useTextProcessorGlobalDefault();
  const updateGlobalDefault = useUpdateTextProcessorGlobalDefault();
  const deleteGlobalDefault = useDeleteTextProcessorGlobalDefault();

  const hasGlobalDefault = globalDefault?.exists ?? false;

  const loadDefault = () => {
    const entries = globalDefault?.entries;
    if (entries) {
      onLoadEntries(entries);
      toast.info(
        'Loaded your default configuration — review and save to apply'
      );
    }
  };

  const runConfirmed = async () => {
    const action = confirmAction;
    setConfirmAction(null);
    try {
      if (action === 'save-default') {
        await updateGlobalDefault.mutateAsync({
          entries: getEntries(),
          basedOnDefaultSha256: metadata?.default_config_sha256,
          baseFileHash: globalDefault?.file_hash,
        });
        toast.success('Saved as your default text processing configuration');
      } else if (action === 'clear-default') {
        await deleteGlobalDefault.mutateAsync(globalDefault?.file_hash);
        toast.success('Removed your default configuration');
      } else if (action === 'reset-project') {
        onResetProject();
      } else if (action === 'load-default') {
        loadDefault();
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Operation failed');
    }
  };

  const copy = confirmAction ? CONFIRM_COPY[confirmAction] : null;

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" size="sm">
            Defaults
            <ChevronDown className="ml-1 h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-72">
          <DropdownMenuItem onClick={() => setConfirmAction('save-default')}>
            <Save className="mr-2 h-4 w-4" />
            <div>
              <div>Save as my default</div>
              <div className="text-muted-foreground text-xs">
                Use this pipeline for future screenplays
              </div>
            </div>
          </DropdownMenuItem>
          <DropdownMenuItem
            disabled={!hasGlobalDefault}
            onClick={() => {
              if (isDirty) {
                setConfirmAction('load-default');
              } else {
                loadDefault();
              }
            }}
          >
            <Download className="mr-2 h-4 w-4" />
            <div>
              <div>Load my default into this project</div>
              <div className="text-muted-foreground text-xs">
                {hasGlobalDefault
                  ? 'Replaces the pipeline below (until saved)'
                  : 'No saved default yet'}
              </div>
            </div>
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => setConfirmAction('reset-project')}>
            <RotateCcw className="mr-2 h-4 w-4" />
            Reset this project to built-in defaults
          </DropdownMenuItem>
          <DropdownMenuItem
            disabled={!hasGlobalDefault}
            onClick={() => setConfirmAction('clear-default')}
          >
            <Undo2 className="mr-2 h-4 w-4" />
            Remove my default configuration
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <Dialog
        open={confirmAction !== null}
        onOpenChange={(open) => !open && setConfirmAction(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{copy?.title}</DialogTitle>
            <DialogDescription>{copy?.description}</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setConfirmAction(null)}>
              Cancel
            </Button>
            <Button onClick={runConfirmed}>{copy?.confirmLabel}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
};
