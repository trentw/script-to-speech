import { diffWords } from 'diff';
import React from 'react';

import type { Chunk } from '../../types/text-processing';

interface ChunkDiffProps {
  before: Chunk;
  after: Chunk;
}

const DIFFABLE_FIELDS = ['text', 'speaker', 'type'] as const;

/**
 * Word-level inline diff of a chunk's fields. The text field gets full
 * word-diff highlighting; other changed fields render as before → after.
 */
export const ChunkDiff: React.FC<ChunkDiffProps> = ({ before, after }) => {
  const textBefore = String(before.text ?? '');
  const textAfter = String(after.text ?? '');
  const textChanged = textBefore !== textAfter;

  const otherChanges = DIFFABLE_FIELDS.filter(
    (field) =>
      field !== 'text' &&
      String(before[field] ?? '') !== String(after[field] ?? '')
  );

  return (
    <div className="space-y-1 text-sm">
      {textChanged && (
        <p className="leading-relaxed">
          {diffWords(textBefore, textAfter).map((part, index) => (
            <span
              key={index}
              className={
                part.added
                  ? 'rounded bg-green-500/20 px-0.5 text-green-700 dark:text-green-400'
                  : part.removed
                    ? 'rounded bg-red-500/20 px-0.5 text-red-700 line-through dark:text-red-400'
                    : undefined
              }
            >
              {part.value}
            </span>
          ))}
        </p>
      )}
      {otherChanges.map((field) => (
        <p key={field} className="text-muted-foreground text-xs">
          <span className="font-medium">{field}:</span>{' '}
          <span className="rounded bg-red-500/20 px-0.5 line-through">
            {String(before[field] ?? '(empty)')}
          </span>{' '}
          →{' '}
          <span className="rounded bg-green-500/20 px-0.5">
            {String(after[field] ?? '(empty)')}
          </span>
        </p>
      ))}
      {!textChanged && otherChanges.length === 0 && (
        <p className="text-muted-foreground text-xs italic">
          Changes in other fields (e.g. raw_text)
        </p>
      )}
    </div>
  );
};
