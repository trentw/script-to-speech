import { Check, Play, Trash2 } from 'lucide-react';
import { useCallback } from 'react';

import { appButtonVariants } from '@/components/ui/button-variants';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { useCommitVariant } from '@/hooks/mutations/useCommitVariant';
import { useDeleteVariant } from '@/hooks/mutations/useDeleteVariant';
import type { VariantInfo } from '@/types/review';

interface VariantListProps {
  variants: VariantInfo[];
  projectName: string;
  targetCacheFilename: string;
  onRemove: (variantId: string) => void;
  onCommit: (variantId: string) => void;
}

/**
 * Displays a list of generated variants with playback, commit, and remove controls.
 */
export function VariantList({
  variants,
  projectName,
  targetCacheFilename,
  onRemove,
  onCommit,
}: VariantListProps) {
  const commitVariant = useCommitVariant();
  const deleteVariant = useDeleteVariant();

  const handlePlay = useCallback((audioUrl: string) => {
    const audio = new Audio(audioUrl);
    audio.play().catch(console.error);
  }, []);

  const handleCommit = useCallback(
    async (variant: VariantInfo) => {
      try {
        await commitVariant.mutateAsync({
          sourcePath: variant.filePath,
          targetCacheFilename,
          projectName,
        });
        onCommit(variant.id);
      } catch (error) {
        console.error('Failed to commit variant:', error);
      }
    },
    [commitVariant, projectName, targetCacheFilename, onCommit]
  );

  const handleRemove = useCallback(
    async (variant: VariantInfo) => {
      try {
        await deleteVariant.mutateAsync(variant.filePath);
        onRemove(variant.id);
      } catch (error) {
        console.error('Failed to delete variant:', error);
      }
    },
    [deleteVariant, onRemove]
  );

  if (variants.length === 0) {
    return null;
  }

  return (
    <div className="border-border rounded border p-2">
      <div className="text-muted-foreground mb-2 text-xs font-medium">
        Variants ({variants.length})
      </div>
      <div className="space-y-1">
        {variants.map((variant, index) => (
          <div
            key={variant.id}
            className="bg-background/50 flex items-center justify-between gap-2 rounded px-2 py-1"
          >
            <span className="text-sm">
              Variant {index + 1}
              {variant.committed && (
                <span className="ml-2 text-xs text-green-600">(committed)</span>
              )}
            </span>
            <div className="flex items-center gap-1">
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    className={appButtonVariants({
                      variant: 'list-action',
                      size: 'icon-sm',
                    })}
                    onClick={() => handlePlay(variant.audioUrl)}
                  >
                    <Play className="h-3 w-3" />
                  </button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Play variant</p>
                </TooltipContent>
              </Tooltip>
              {!variant.committed && (
                <>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button
                        className={`${appButtonVariants({
                          variant: 'list-action',
                          size: 'icon-sm',
                        })} text-green-600 hover:text-green-700`}
                        onClick={() => handleCommit(variant)}
                        disabled={commitVariant.isPending}
                      >
                        <Check className="h-3 w-3" />
                      </button>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>Commit to cache</p>
                    </TooltipContent>
                  </Tooltip>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button
                        className={`${appButtonVariants({
                          variant: 'list-action',
                          size: 'icon-sm',
                        })} text-destructive hover:text-destructive`}
                        onClick={() => handleRemove(variant)}
                        disabled={deleteVariant.isPending}
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>Remove variant</p>
                    </TooltipContent>
                  </Tooltip>
                </>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
