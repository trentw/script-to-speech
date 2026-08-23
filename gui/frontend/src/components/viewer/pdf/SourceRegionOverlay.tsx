import { PenLine, RotateCcw } from 'lucide-react';
import { memo, useMemo } from 'react';

import { cn } from '@/lib/utils';
import type { ChunkInventoryEntry } from '@/types/chunks';

import {
  type PageRegion,
  scaleRect,
  statusOverlayClasses,
  summarizeRegion,
} from './pdfOverlayLogic';

interface SourceRegionOverlayProps {
  region: PageRegion;
  entries: ChunkInventoryEntry[];
  /** renderedWidth / pageWidth */
  scale: number;
  activePosition: number | null;
  selectedPosition: number | null;
  onSelect: (position: number, regionPositions: number[]) => void;
}

/**
 * One interactive PDF source region. Most regions represent one audio chunk;
 * preprocessor splits share this same target and are resolved in the persistent
 * detail panel instead of competing as overlapping PDF controls.
 */
export const SourceRegionOverlay = memo(function SourceRegionOverlay({
  region,
  entries,
  scale,
  activePosition,
  selectedPosition,
  onSelect,
}: SourceRegionOverlayProps) {
  const bounds = useMemo(() => {
    const xs0 = region.rects.map((rect) => rect.x0);
    const tops = region.rects.map((rect) => rect.top);
    const xs1 = region.rects.map((rect) => rect.x1);
    const bottoms = region.rects.map((rect) => rect.bottom);
    return {
      x0: Math.min(...xs0),
      top: Math.min(...tops),
      x1: Math.max(...xs1),
      bottom: Math.max(...bottoms),
    };
  }, [region.rects]);

  const positions = region.members.map((member) => member.position);
  const regionEntries = positions
    .map((position) => entries[position])
    .filter((entry): entry is ChunkInventoryEntry => entry !== undefined);
  const summary = summarizeRegion(regionEntries);
  const isActive =
    activePosition !== null && positions.includes(activePosition);
  const isSelected =
    selectedPosition !== null && positions.includes(selectedPosition);
  const preferredPosition = isSelected
    ? selectedPosition
    : isActive
      ? activePosition
      : positions[0];
  const boxClasses = statusOverlayClasses(summary.status, {
    isActive,
    isSelected,
  });

  if (preferredPosition === null || preferredPosition === undefined)
    return null;

  const chunkIds = region.members.map((member) => member.idx);
  const firstEntry = regionEntries[0];
  const sourceDescription =
    region.members.length === 1
      ? `Source region for chunk ${chunkIds[0]}: ${firstEntry?.chunkType ?? 'unknown'}`
      : `Source region with ${region.members.length} audio chunks: ${chunkIds
          .map((idx) => `#${idx}`)
          .join(', ')}`;
  const statusDescription = summary.status.replace('_', ' ');
  const provenanceDescription = summary.modifiedKinds
    .map((kind) => (kind === 'edit' ? 'edited text' : 'custom take'))
    .join(', ');
  const ariaLabel = `${sourceDescription}; ${statusDescription}${
    provenanceDescription ? `; ${provenanceDescription}` : ''
  }`;

  return (
    <button
      type="button"
      aria-label={ariaLabel}
      className="group/source focus-visible:outline-primary absolute cursor-pointer rounded-sm focus-visible:outline-2 focus-visible:outline-offset-2"
      style={{
        left: bounds.x0 * scale,
        top: bounds.top * scale,
        width: (bounds.x1 - bounds.x0) * scale,
        height: (bounds.bottom - bounds.top) * scale,
      }}
      onClick={() => onSelect(preferredPosition, positions)}
    >
      {region.rects.map((rect, index) => {
        const scaled = scaleRect(rect, scale);
        return (
          <span
            key={`${rect.top}-${rect.x0}-${index}`}
            aria-hidden="true"
            className={cn('pointer-events-none absolute', boxClasses)}
            style={{
              left: scaled.left - bounds.x0 * scale,
              top: scaled.top - bounds.top * scale,
              width: scaled.width,
              height: scaled.height,
            }}
          />
        );
      })}

      <span className="absolute -top-2 -right-2 flex items-center gap-0.5 font-sans">
        {region.members.length > 1 && (
          <span className="bg-foreground text-background flex h-4 min-w-4 items-center justify-center rounded-full px-1 text-[9px] font-semibold shadow-sm">
            {region.members.length}
          </span>
        )}
        {summary.modifiedKinds.includes('edit') && (
          <span
            className="flex h-4 w-4 items-center justify-center rounded-full bg-amber-500 text-white shadow-sm"
            title="Contains audio generated from edited text"
          >
            <PenLine className="h-2.5 w-2.5" />
          </span>
        )}
        {summary.modifiedKinds.includes('retake') && (
          <span
            className="flex h-4 w-4 items-center justify-center rounded-full bg-violet-500 text-white shadow-sm"
            title="Contains a custom take"
          >
            <RotateCcw className="h-2.5 w-2.5" />
          </span>
        )}
      </span>
    </button>
  );
});
