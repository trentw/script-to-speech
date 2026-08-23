/**
 * Types for the PDF overlay view (M3).
 *
 * Correspond to the backend models in gui_backend/models.py (AnchorRect,
 * ChunkAnchor, PdfPageInfo, ChunkAnchorsResponse). Anchors map each
 * post-preprocessed chunk (by idx, shared with ChunkInventoryEntry) onto the
 * rendered PDF. Coordinates are in PDF points with a top-left origin, so the
 * frontend scales them by renderedWidth / pageWidth.
 */

/** One line's bounding box for a chunk on a given page. */
export interface AnchorRect {
  /** 0-indexed page number */
  page: number;
  x0: number;
  top: number;
  x1: number;
  bottom: number;
}

/** Where a single chunk sits on the rendered PDF. */
export interface ChunkAnchor {
  /** Matches ChunkInventoryEntry.idx (post-preprocessed position) */
  idx: number;
  /** One rect per rendered line; may span pages */
  rects: AnchorRect[];
  /** Fraction of the chunk's tokens matched on the page (0..1) */
  matchRatio: number;
}

/** Dimensions of one PDF page, for laying out before render. */
export interface PdfPageInfo {
  /** 0-indexed page number */
  page: number;
  width: number;
  height: number;
}

/** Full chunk-to-PDF anchoring for a project's overlay view. */
export interface ChunkAnchorsResponse {
  projectName: string;
  pages: PdfPageInfo[];
  /** Anchored chunks only; unanchored ones appear in unanchoredIdxs */
  anchors: ChunkAnchor[];
  unanchoredIdxs: number[];
  totalChunks: number;
  anchoredCount: number;
  /** Must match the current inventory before anchor idxs are used. */
  chunkLayoutRevision: string;
  /**
   * Pages whose visible box is cropped or origin-shifted. Their word geometry
   * is intentionally not overlaid until that coordinate transform is validated.
   */
  unsupportedGeometryPages: number[];
  /** ISO timestamp of when these anchors were computed */
  generatedAt: string;
}
