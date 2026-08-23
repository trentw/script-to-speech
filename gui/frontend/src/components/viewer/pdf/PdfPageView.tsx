import { memo } from 'react';
import { Page } from 'react-pdf';

import type { ChunkInventoryEntry } from '@/types/chunks';

import type { PageRegion } from './pdfOverlayLogic';
import { SourceRegionOverlay } from './SourceRegionOverlay';

interface PdfPageViewProps {
  /** 0-indexed page number */
  pageNumber: number;
  /** Rendered page width in px (Page width prop); height derives from ratio */
  renderWidth: number;
  /** renderedWidth / pageWidth (PDF points -> px) */
  scale: number;
  pageRegions: PageRegion[];
  entries: ChunkInventoryEntry[];
  activePosition: number | null;
  selectedPosition: number | null;
  onSelect: (position: number, regionPositions: number[]) => void;
}

/**
 * A single rendered PDF page with its chunk overlays layered on top. The page
 * canvas is rendered by react-pdf (text/annotation layers disabled — the
 * overlays replace them); the overlay layer is absolutely positioned to match.
 */
export const PdfPageView = memo(function PdfPageView({
  pageNumber,
  renderWidth,
  scale,
  pageRegions,
  entries,
  activePosition,
  selectedPosition,
  onSelect,
}: PdfPageViewProps) {
  return (
    <div
      className="border-border bg-card relative mx-auto border shadow-sm"
      style={{ width: renderWidth }}
    >
      <Page
        pageNumber={pageNumber + 1}
        width={renderWidth}
        renderTextLayer={false}
        renderAnnotationLayer={false}
      />
      <div className="absolute inset-0">
        {pageRegions.map((region) => (
          <SourceRegionOverlay
            key={region.key}
            region={region}
            entries={entries}
            scale={scale}
            activePosition={activePosition}
            selectedPosition={selectedPosition}
            onSelect={onSelect}
          />
        ))}
      </div>
    </div>
  );
});
