/**
 * Review-flow generation kind helpers. The kinds themselves are defined once
 * in types/chunks.ts (GENERATION_KINDS / GenerationKind) and validated by the
 * backend: "retake" when regenerating the chunk's exact processed text,
 * "edit" when the text was modified.
 */

import type { GenerationKind } from '@/types/chunks';

/**
 * UI labels for each generation kind. The badge wording is intentionally
 * different from the wire value ("retake" renders as "custom take").
 * Adding a new kind to GENERATION_KINDS requires adding its labels here.
 */
export const GENERATION_KIND_BADGES: Record<
  GenerationKind,
  { label: string; description: string }
> = {
  retake: {
    label: 'custom take',
    description: 'Cached audio was committed from a regenerated take',
  },
  edit: {
    label: 'edited text',
    description: 'Cached audio was committed from modified text',
  },
};

/**
 * Decide the generation kind for a review-flow generation.
 *
 * Must be evaluated at the moment Generate is clicked, by STRICT string
 * equality against the chunk's processed text - never by which UI component
 * is open (a user who opens the edit box but leaves the text unchanged
 * generates a "retake").
 *
 * @param textToGenerate - The text about to be sent for generation
 * @param clipText - The chunk's processed text (clip.text)
 */
export function getGenerationKind(
  textToGenerate: string,
  clipText: string
): GenerationKind {
  return textToGenerate === clipText ? 'retake' : 'edit';
}
