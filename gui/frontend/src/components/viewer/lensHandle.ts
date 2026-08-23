/**
 * Imperative contract shared by both viewer lenses (list and PDF). The shell
 * holds one ref of this type against whichever lens is mounted.
 */
export interface ViewerLensHandle {
  /** Scroll a chunk (by list position) into view, centered. */
  scrollToPosition: (position: number) => void;
  /** Force-refresh lens-specific derived data, when the lens owns any. */
  refresh?: () => Promise<unknown>;
}
