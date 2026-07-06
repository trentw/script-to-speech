import { describe, expect, it } from 'vitest';

import { GENERATION_KINDS } from '@/types/chunks';

import { GENERATION_KIND_BADGES, getGenerationKind } from '../generationKind';

describe('getGenerationKind', () => {
  it('returns "retake" when the generated text exactly matches the clip text', () => {
    expect(getGenerationKind('HELLO WORLD.', 'HELLO WORLD.')).toBe('retake');
  });

  it('returns "edit" when the generated text differs from the clip text', () => {
    expect(getGenerationKind('HELLO, WORLD.', 'HELLO WORLD.')).toBe('edit');
  });

  it('uses strict string equality - whitespace differences are edits', () => {
    expect(getGenerationKind('HELLO WORLD. ', 'HELLO WORLD.')).toBe('edit');
  });

  it('uses strict string equality - case differences are edits', () => {
    expect(getGenerationKind('hello world.', 'HELLO WORLD.')).toBe('edit');
  });

  it('returns "retake" for unchanged text even if it came from an edit input', () => {
    // The decision is by text comparison, never by which UI component is open
    const clipText = 'sighs';
    const editBoxText = clipText; // user opened the edit box but changed nothing
    expect(getGenerationKind(editBoxText, clipText)).toBe('retake');
  });
});

describe('GENERATION_KIND_BADGES', () => {
  it('has badge labels for every generation kind', () => {
    for (const kind of GENERATION_KINDS) {
      expect(GENERATION_KIND_BADGES[kind].label).toBeTruthy();
      expect(GENERATION_KIND_BADGES[kind].description).toBeTruthy();
    }
  });

  it('keeps the user-facing labels stable across the wire-value rename', () => {
    expect(GENERATION_KIND_BADGES.retake.label).toBe('custom take');
    expect(GENERATION_KIND_BADGES.edit.label).toBe('edited text');
  });
});
