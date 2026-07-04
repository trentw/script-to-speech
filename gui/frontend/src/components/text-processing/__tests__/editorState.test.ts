import { describe, expect, it } from 'vitest';

import type {
  TextProcessorConfig,
  TextProcessorEntry,
} from '@/types/text-processing';

import {
  buildSingleChangePayload,
  buildSingleRowChangePayload,
  changedScalarFields,
  computeDiff,
  computeRowDiff,
  editorReducer,
  type EditorState,
  initialEditorState,
  ROW_UID_KEY,
  toEntryPayloads,
} from '../editorState';

const ENTRIES: TextProcessorEntry[] = [
  {
    kind: 'preprocessor',
    name: 'skip_and_merge',
    known: true,
    config: { skip_types: ['page_number'] },
    config_yaml: 'skip_types:\n  - page_number\n',
  },
  {
    kind: 'preprocessor',
    name: 'speaker_merge',
    known: true,
    config: { speakers_to_merge: {} },
    config_yaml: 'speakers_to_merge: {}\n',
  },
  {
    kind: 'processor',
    name: 'text_substitution',
    known: true,
    config: { substitutions: [{ from: 'INT.', to: 'INTERIOR' }] },
    config_yaml: 'substitutions:\n  - from: INT.\n    to: INTERIOR\n',
  },
  {
    kind: 'processor',
    name: 'skip_empty',
    known: true,
    config: null,
    config_yaml: '{}\n',
  },
];

const makeConfig = (
  entries: TextProcessorEntry[] = ENTRIES,
  fileHash = 'hash-1'
): TextProcessorConfig => ({
  path: '/workspace/input/demo/demo_text_processor_config.yaml',
  yaml_text: 'irrelevant',
  file_hash: fileHash,
  entries,
  metadata: null,
  stale: false,
  is_legacy_additive: false,
  current_default_hash: 'default-hash',
});

const initState = (): EditorState =>
  editorReducer(initialEditorState, { type: 'init', config: makeConfig() });

const uidOf = (state: EditorState, name: string): string => {
  const entry = state.entries.find((e) => e.name === name);
  if (!entry) throw new Error(`no entry named ${name}`);
  return entry.uid;
};

describe('computeDiff', () => {
  it('reports a freshly initialized buffer as clean', () => {
    const state = initState();
    const diff = computeDiff(state);

    expect(diff.dirty).toBe(false);
    expect(diff.total).toBe(0);
    expect([...diff.statusByUid.values()]).toEqual([
      'clean',
      'clean',
      'clean',
      'clean',
    ]);
  });

  it('marks a form-edited entry modified, and clean again when edited back', () => {
    let state = initState();
    const uid = uidOf(state, 'text_substitution');

    state = editorReducer(state, {
      type: 'updateConfig',
      uid,
      config: { substitutions: [{ from: 'EXT.', to: 'EXTERIOR' }] },
    });
    expect(computeDiff(state).statusByUid.get(uid)).toBe('modified');
    expect(computeDiff(state).details).toContain('Modified: text_substitution');

    state = editorReducer(state, {
      type: 'updateConfig',
      uid,
      config: { substitutions: [{ from: 'INT.', to: 'INTERIOR' }] },
    });
    const diff = computeDiff(state);
    expect(diff.statusByUid.get(uid)).toBe('clean');
    expect(diff.dirty).toBe(false);
    // Snap-back restored the comment-bearing YAML from the baseline
    const entry = state.entries.find((e) => e.uid === uid);
    expect(entry?.config_yaml).toBe(
      'substitutions:\n  - from: INT.\n    to: INTERIOR\n'
    );
  });

  it('marks a YAML-edited entry modified, and clean when the text is restored', () => {
    let state = initState();
    const uid = uidOf(state, 'skip_and_merge');

    state = editorReducer(state, {
      type: 'updateYaml',
      uid,
      configYaml: 'skip_types:\n  - page_number\n  - title\n',
    });
    expect(computeDiff(state).statusByUid.get(uid)).toBe('modified');

    state = editorReducer(state, {
      type: 'updateYaml',
      uid,
      configYaml: 'skip_types:\n  - page_number\n',
    });
    const diff = computeDiff(state);
    expect(diff.statusByUid.get(uid)).toBe('clean');
    expect(diff.dirty).toBe(false);
  });

  it('treats a move as a section order change, not an entry modification', () => {
    let state = initState();
    const uid = uidOf(state, 'skip_and_merge');

    state = editorReducer(state, { type: 'move', uid, direction: 'down' });
    const diff = computeDiff(state);

    expect(diff.orderChanged.preprocessor).toBe(true);
    expect(diff.orderChanged.processor).toBe(false);
    expect(diff.statusByUid.get(uid)).toBe('clean');
    expect(diff.counts).toEqual({
      added: 0,
      modified: 0,
      removed: 0,
      orderChanges: 1,
    });
    expect(diff.details).toContain('Order changed: Structure');
  });

  it('surfaces a removed entry as a tombstone anchored to its predecessor', () => {
    let state = initState();
    const removedUid = uidOf(state, 'speaker_merge');
    const anchorUid = uidOf(state, 'skip_and_merge');

    state = editorReducer(state, { type: 'remove', uid: removedUid });
    const diff = computeDiff(state);

    expect(diff.counts.removed).toBe(1);
    expect(diff.removed[0]?.entry.name).toBe('speaker_merge');
    expect(diff.removed[0]?.afterUid).toBe(anchorUid);
    // Removing an entry is not an order change for the survivors
    expect(diff.orderChanged.preprocessor).toBe(false);
  });

  it('marks an added entry and counts it in the total', () => {
    let state = initState();
    state = editorReducer(state, {
      type: 'add',
      kind: 'processor',
      name: 'pattern_replace',
      config: { replacements: [] },
    });
    const uid = uidOf(state, 'pattern_replace');
    const diff = computeDiff(state);

    expect(diff.statusByUid.get(uid)).toBe('added');
    expect(diff.total).toBe(1);
    expect(diff.details).toContain('Added: pattern_replace');
  });
});

describe('revert actions', () => {
  it('revertEntry restores a modified entry to its baseline', () => {
    let state = initState();
    const uid = uidOf(state, 'text_substitution');
    state = editorReducer(state, {
      type: 'updateConfig',
      uid,
      config: { substitutions: [] },
    });

    state = editorReducer(state, { type: 'revertEntry', uid });

    expect(computeDiff(state).dirty).toBe(false);
    const entry = state.entries.find((e) => e.uid === uid);
    // Content restored (config also carries a client-only row uid)
    expect(entry?.config).toMatchObject({
      substitutions: [{ from: 'INT.', to: 'INTERIOR' }],
    });
  });

  it('revertEntry drops an added entry', () => {
    let state = initState();
    state = editorReducer(state, {
      type: 'add',
      kind: 'processor',
      name: 'pattern_replace',
      config: {},
    });
    const uid = uidOf(state, 'pattern_replace');

    state = editorReducer(state, { type: 'revertEntry', uid });

    expect(state.entries.some((e) => e.name === 'pattern_replace')).toBe(false);
    expect(computeDiff(state).dirty).toBe(false);
  });

  it('restoreRemoved reinserts a tombstoned entry at its original position', () => {
    let state = initState();
    const uid = uidOf(state, 'speaker_merge');
    state = editorReducer(state, { type: 'remove', uid });

    state = editorReducer(state, { type: 'restoreRemoved', uid });

    expect(state.entries.map((e) => e.name)).toEqual([
      'skip_and_merge',
      'speaker_merge',
      'text_substitution',
      'skip_empty',
    ]);
    expect(computeDiff(state).dirty).toBe(false);
  });

  it('revertOrder restores baseline order and keeps added entries at the end', () => {
    let state = initState();
    state = editorReducer(state, {
      type: 'add',
      kind: 'processor',
      name: 'pattern_replace',
      config: {},
    });
    state = editorReducer(state, {
      type: 'move',
      uid: uidOf(state, 'text_substitution'),
      direction: 'down',
    });
    expect(computeDiff(state).orderChanged.processor).toBe(true);

    state = editorReducer(state, { type: 'revertOrder', kind: 'processor' });

    const processorNames = state.entries
      .filter((e) => e.kind === 'processor')
      .map((e) => e.name);
    expect(processorNames).toEqual([
      'text_substitution',
      'skip_empty',
      'pattern_replace',
    ]);
    expect(computeDiff(state).orderChanged.processor).toBe(false);
  });
});

describe('buildSingleChangePayload', () => {
  it('for a modified entry: baseline plus only that change, other edits excluded', () => {
    let state = initState();
    const modifiedUid = uidOf(state, 'text_substitution');
    const otherUid = uidOf(state, 'skip_and_merge');
    state = editorReducer(state, {
      type: 'updateConfig',
      uid: modifiedUid,
      config: { substitutions: [{ from: 'EXT.', to: 'EXTERIOR' }] },
    });
    state = editorReducer(state, {
      type: 'updateConfig',
      uid: otherUid,
      config: { skip_types: ['title'] },
    });

    const result = buildSingleChangePayload(state, {
      type: 'entry',
      uid: modifiedUid,
    });

    expect(result).not.toBeNull();
    expect(result!.payload.map((e) => e.name)).toEqual([
      'skip_and_merge',
      'speaker_merge',
      'text_substitution',
      'skip_empty',
    ]);
    const committed = result!.payload.find(
      (e) => e.name === 'text_substitution'
    );
    expect(committed?.config).toEqual({
      substitutions: [{ from: 'EXT.', to: 'EXTERIOR' }],
    });
    // The other pending edit stays out of this write
    const untouched = result!.payload.find((e) => e.name === 'skip_and_merge');
    expect(untouched?.config).toEqual({ skip_types: ['page_number'] });
    expect(result!.uidOrder).toHaveLength(4);
  });

  it('for an added entry: inserted after its nearest baseline sibling', () => {
    let state = initState();
    state = editorReducer(state, {
      type: 'add',
      kind: 'processor',
      name: 'pattern_replace',
      config: { replacements: [] },
    });
    const addedUid = uidOf(state, 'pattern_replace');
    // Move it up so it sits between the two baseline processors
    state = editorReducer(state, {
      type: 'move',
      uid: addedUid,
      direction: 'up',
    });

    const result = buildSingleChangePayload(state, {
      type: 'entry',
      uid: addedUid,
    });

    expect(result!.payload.map((e) => e.name)).toEqual([
      'skip_and_merge',
      'speaker_merge',
      'text_substitution',
      'pattern_replace',
      'skip_empty',
    ]);
    expect(result!.uidOrder[3]).toBe(addedUid);
  });

  it('for a removal: baseline minus the entry', () => {
    let state = initState();
    const uid = uidOf(state, 'speaker_merge');
    state = editorReducer(state, { type: 'remove', uid });

    const result = buildSingleChangePayload(state, { type: 'removal', uid });

    expect(result!.payload.map((e) => e.name)).toEqual([
      'skip_and_merge',
      'text_substitution',
      'skip_empty',
    ]);
  });

  it('for an order change: buffer order with baseline entry data', () => {
    let state = initState();
    const uid = uidOf(state, 'text_substitution');
    // Content edit that must NOT leak into the order commit
    state = editorReducer(state, {
      type: 'updateConfig',
      uid,
      config: { substitutions: [{ from: 'EXT.', to: 'EXTERIOR' }] },
    });
    state = editorReducer(state, { type: 'move', uid, direction: 'down' });

    const result = buildSingleChangePayload(state, {
      type: 'order',
      kind: 'processor',
    });

    expect(result!.payload.map((e) => e.name)).toEqual([
      'skip_and_merge',
      'speaker_merge',
      'skip_empty',
      'text_substitution',
    ]);
    const moved = result!.payload.find((e) => e.name === 'text_substitution');
    expect(moved?.config).toEqual({
      substitutions: [{ from: 'INT.', to: 'INTERIOR' }],
    });
  });
});

describe('row uids and row-level diffing', () => {
  const rowsOf = (state: EditorState, name: string, field: string) => {
    const entry = state.entries.find((e) => e.name === name);
    return (entry?.config?.[field] ?? []) as Record<string, unknown>[];
  };

  it('assigns row uids on init and strips them from payloads', () => {
    const state = initState();

    const rows = rowsOf(state, 'text_substitution', 'substitutions');
    expect(rows).toHaveLength(1);
    expect(typeof rows[0]?.[ROW_UID_KEY]).toBe('string');
    // Baseline shares the same uids (same adoption walk)
    const baseRows = (state.baseline.find((b) => b.name === 'text_substitution')
      ?.config?.['substitutions'] ?? []) as Record<string, unknown>[];
    expect(baseRows[0]?.[ROW_UID_KEY]).toBe(rows[0]?.[ROW_UID_KEY]);

    const payloads = toEntryPayloads(state.entries);
    const payloadRows = (payloads.find((p) => p.name === 'text_substitution')
      ?.config?.['substitutions'] ?? []) as Record<string, unknown>[];
    expect(payloadRows[0]).not.toHaveProperty(ROW_UID_KEY);
  });

  it('flags only the edited row as modified', () => {
    let state = initState();
    const uid = uidOf(state, 'text_substitution');
    const rows = rowsOf(state, 'text_substitution', 'substitutions');
    const edited = [
      { ...rows[0], to: 'INSIDE' },
      { from: 'EXT.', to: 'EXTERIOR' },
    ];
    state = editorReducer(state, {
      type: 'updateConfig',
      uid,
      config: { substitutions: edited },
    });

    const entry = state.entries.find((e) => e.uid === uid);
    const base = state.baseline.find((b) => b.uid === uid);
    const nextRows = rowsOf(state, 'text_substitution', 'substitutions');
    // The new row got a uid assigned during the update
    expect(typeof nextRows[1]?.[ROW_UID_KEY]).toBe('string');

    const rowDiff = computeRowDiff(entry!, base).get('substitutions');
    expect(
      rowDiff?.statusByRowUid.get(nextRows[0]?.[ROW_UID_KEY] as string)
    ).toBe('modified');
    expect(
      rowDiff?.statusByRowUid.get(nextRows[1]?.[ROW_UID_KEY] as string)
    ).toBe('added');
    expect(rowDiff?.removedRows).toHaveLength(0);
  });

  it('surfaces a deleted row as a removed ghost with its anchor', () => {
    let state = initState();
    const uid = uidOf(state, 'text_substitution');
    state = editorReducer(state, {
      type: 'updateConfig',
      uid,
      config: { substitutions: [] },
    });

    const entry = state.entries.find((e) => e.uid === uid);
    const base = state.baseline.find((b) => b.uid === uid);
    const rowDiff = computeRowDiff(entry!, base).get('substitutions');
    expect(rowDiff?.removedRows).toHaveLength(1);
    expect(rowDiff?.removedRows[0]?.row.from).toBe('INT.');
    expect(rowDiff?.removedRows[0]?.afterRowUid).toBeNull();
  });

  it('reports changed scalar fields separately from row lists', () => {
    let state = initState();
    const uid = uidOf(state, 'skip_and_merge');
    state = editorReducer(state, {
      type: 'updateConfig',
      uid,
      config: { skip_types: ['page_number', 'title'] },
    });

    const entry = state.entries.find((e) => e.uid === uid);
    const base = state.baseline.find((b) => b.uid === uid);
    expect(changedScalarFields(entry!, base)).toEqual(new Set(['skip_types']));
  });

  it('row identity survives a single-change commit (rebaseline)', () => {
    let state = initState();
    const uid = uidOf(state, 'text_substitution');
    const originalRowUid = rowsOf(
      state,
      'text_substitution',
      'substitutions'
    )[0]?.[ROW_UID_KEY];
    // Edit the row, then commit the entry and rebaseline from the response
    state = editorReducer(state, {
      type: 'updateConfig',
      uid,
      config: {
        substitutions: [
          {
            [ROW_UID_KEY]: originalRowUid,
            from: 'INT.',
            to: 'INSIDE',
          },
        ],
      },
    });
    const single = buildSingleChangePayload(state, { type: 'entry', uid })!;
    state = editorReducer(state, {
      type: 'rebaseline',
      config: makeConfig(
        single.payload.map((e) => ({ ...e })),
        'hash-2'
      ),
      uidOrder: single.uidOrder,
    });

    // Payload rows are stripped; the rebaselined rows re-adopt the same uid
    const payloadRow = (single.payload.find(
      (p) => p.name === 'text_substitution'
    )?.config?.['substitutions'] ?? [])[0] as Record<string, unknown>;
    expect(payloadRow).not.toHaveProperty(ROW_UID_KEY);
    const newBaseRow = (state.baseline.find((b) => b.uid === uid)?.config?.[
      'substitutions'
    ] ?? [])[0] as Record<string, unknown>;
    expect(newBaseRow[ROW_UID_KEY]).toBe(originalRowUid);
    expect(computeDiff(state).dirty).toBe(false);
  });
});

describe('buildSingleRowChangePayload', () => {
  const setupTwoRowEdits = () => {
    // Start from a two-row baseline so single-row deltas are observable
    const entries = ENTRIES.map((entry) =>
      entry.name === 'text_substitution'
        ? {
            ...entry,
            config: {
              substitutions: [
                { from: 'INT.', to: 'INTERIOR' },
                { from: 'EXT.', to: 'EXTERIOR' },
              ],
            },
            config_yaml: null,
          }
        : entry
    );
    let state = editorReducer(initialEditorState, {
      type: 'init',
      config: makeConfig(entries),
    });
    const uid = uidOf(state, 'text_substitution');
    const rows = (state.entries.find((e) => e.uid === uid)?.config?.[
      'substitutions'
    ] ?? []) as Record<string, unknown>[];
    const [rowA, rowB] = rows as [
      Record<string, unknown>,
      Record<string, unknown>,
    ];
    // Edit BOTH rows in the buffer
    state = editorReducer(state, {
      type: 'updateConfig',
      uid,
      config: {
        substitutions: [
          { ...rowA, to: 'INSIDE' },
          { ...rowB, to: 'OUTSIDE' },
        ],
      },
    });
    return { state, uid, rowA, rowB };
  };

  it('for a modified row: baseline plus only that row change', () => {
    const { state, uid, rowA } = setupTwoRowEdits();

    const result = buildSingleRowChangePayload(state, {
      type: 'row',
      entryUid: uid,
      field: 'substitutions',
      rowUid: rowA[ROW_UID_KEY] as string,
    });

    const subs = (result!.payload.find((p) => p.name === 'text_substitution')
      ?.config?.['substitutions'] ?? []) as Record<string, unknown>[];
    // Row A carries its edit; row B stays as it is on disk
    expect(subs).toEqual([
      { from: 'INT.', to: 'INSIDE' },
      { from: 'EXT.', to: 'EXTERIOR' },
    ]);
  });

  it('for an added row: inserted after its buffer predecessor', () => {
    const setup = setupTwoRowEdits();
    const { uid } = setup;
    let { state } = setup;
    const currentRows = (state.entries.find((e) => e.uid === uid)?.config?.[
      'substitutions'
    ] ?? []) as Record<string, unknown>[];
    // Insert a brand-new row between A and B
    state = editorReducer(state, {
      type: 'updateConfig',
      uid,
      config: {
        substitutions: [
          currentRows[0]!,
          { from: 'O.S.', to: 'OFF SCREEN' },
          currentRows[1]!,
        ],
      },
    });
    const newRowUid = (
      (state.entries.find((e) => e.uid === uid)?.config?.['substitutions'] ??
        []) as Record<string, unknown>[]
    )[1]?.[ROW_UID_KEY] as string;

    const result = buildSingleRowChangePayload(state, {
      type: 'row',
      entryUid: uid,
      field: 'substitutions',
      rowUid: newRowUid,
    });

    const subs = (result!.payload.find((p) => p.name === 'text_substitution')
      ?.config?.['substitutions'] ?? []) as Record<string, unknown>[];
    // The new row lands after row A; the uncommitted edits to A/B stay out
    expect(subs).toEqual([
      { from: 'INT.', to: 'INTERIOR' },
      { from: 'O.S.', to: 'OFF SCREEN' },
      { from: 'EXT.', to: 'EXTERIOR' },
    ]);
  });

  it('for a row removal: baseline minus that row', () => {
    const { state, uid, rowB } = setupTwoRowEdits();

    const result = buildSingleRowChangePayload(state, {
      type: 'rowRemoval',
      entryUid: uid,
      field: 'substitutions',
      rowUid: rowB[ROW_UID_KEY] as string,
    });

    const subs = (result!.payload.find((p) => p.name === 'text_substitution')
      ?.config?.['substitutions'] ?? []) as Record<string, unknown>[];
    expect(subs).toEqual([{ from: 'INT.', to: 'INTERIOR' }]);
  });
});

describe('row-level revert, restore, and partial commit', () => {
  const setupTwoRowEdits = () => {
    const entries = ENTRIES.map((entry) =>
      entry.name === 'text_substitution'
        ? {
            ...entry,
            config: {
              substitutions: [
                { from: 'INT.', to: 'INTERIOR' },
                { from: 'EXT.', to: 'EXTERIOR' },
              ],
            },
            config_yaml: null,
          }
        : entry
    );
    let state = editorReducer(initialEditorState, {
      type: 'init',
      config: makeConfig(entries),
    });
    const uid = uidOf(state, 'text_substitution');
    const rows = (state.entries.find((e) => e.uid === uid)?.config?.[
      'substitutions'
    ] ?? []) as Record<string, unknown>[];
    const [rowA, rowB] = rows as [
      Record<string, unknown>,
      Record<string, unknown>,
    ];
    state = editorReducer(state, {
      type: 'updateConfig',
      uid,
      config: {
        substitutions: [
          { ...rowA, to: 'INSIDE' },
          { ...rowB, to: 'OUTSIDE' },
        ],
      },
    });
    return { state, uid, rowA, rowB };
  };

  it('revertRow restores one row and snaps the entry clean when it was the only edit', () => {
    const { state: base, uid, rowA, rowB } = setupTwoRowEdits();

    let state = editorReducer(base, {
      type: 'revertRow',
      entryUid: uid,
      field: 'substitutions',
      rowUid: rowA[ROW_UID_KEY] as string,
    });
    // Row A back to disk content; row B still dirty
    const entry = state.entries.find((e) => e.uid === uid);
    expect(entry?.config).toMatchObject({
      substitutions: [
        { from: 'INT.', to: 'INTERIOR' },
        { from: 'EXT.', to: 'OUTSIDE' },
      ],
    });
    expect(computeDiff(state).statusByUid.get(uid)).toBe('modified');

    state = editorReducer(state, {
      type: 'revertRow',
      entryUid: uid,
      field: 'substitutions',
      rowUid: rowB[ROW_UID_KEY] as string,
    });
    expect(computeDiff(state).dirty).toBe(false);
  });

  it('revertRow drops an added row', () => {
    const setup = setupTwoRowEdits();
    const { uid } = setup;
    let { state } = setup;
    const currentRows = (state.entries.find((e) => e.uid === uid)?.config?.[
      'substitutions'
    ] ?? []) as Record<string, unknown>[];
    state = editorReducer(state, {
      type: 'updateConfig',
      uid,
      config: {
        substitutions: [...currentRows, { from: 'O.S.', to: 'OFF SCREEN' }],
      },
    });
    const addedUid = (
      (state.entries.find((e) => e.uid === uid)?.config?.['substitutions'] ??
        []) as Record<string, unknown>[]
    )[2]?.[ROW_UID_KEY] as string;

    state = editorReducer(state, {
      type: 'revertRow',
      entryUid: uid,
      field: 'substitutions',
      rowUid: addedUid,
    });

    const rows = (state.entries.find((e) => e.uid === uid)?.config?.[
      'substitutions'
    ] ?? []) as Record<string, unknown>[];
    expect(rows).toHaveLength(2);
  });

  it('restoreRemovedRow reinserts a deleted row at its original position', () => {
    let state = initState();
    const uid = uidOf(state, 'text_substitution');
    const originalRow = (
      (state.entries.find((e) => e.uid === uid)?.config?.['substitutions'] ??
        []) as Record<string, unknown>[]
    )[0] as Record<string, unknown>;
    state = editorReducer(state, {
      type: 'updateConfig',
      uid,
      config: { substitutions: [] },
    });

    state = editorReducer(state, {
      type: 'restoreRemovedRow',
      entryUid: uid,
      field: 'substitutions',
      rowUid: originalRow[ROW_UID_KEY] as string,
    });

    expect(computeDiff(state).dirty).toBe(false);
    const entry = state.entries.find((e) => e.uid === uid);
    // Snap-back adopted the baseline copy, comments and all
    expect(entry?.config_yaml).toBe(
      'substitutions:\n  - from: INT.\n    to: INTERIOR\n'
    );
  });

  it('committing one row keeps the other row edit pending across rebaseline', () => {
    const { state: edited, uid, rowA, rowB } = setupTwoRowEdits();

    const single = buildSingleRowChangePayload(edited, {
      type: 'row',
      entryUid: uid,
      field: 'substitutions',
      rowUid: rowA[ROW_UID_KEY] as string,
    })!;
    const state = editorReducer(edited, {
      type: 'rebaseline',
      config: makeConfig(
        single.payload.map((e) => ({ ...e })),
        'hash-2'
      ),
      uidOrder: single.uidOrder,
    });

    // Entry still modified: row B's edit remains vs the new baseline
    const diff = computeDiff(state);
    expect(diff.statusByUid.get(uid)).toBe('modified');
    const entry = state.entries.find((e) => e.uid === uid)!;
    const baseEntry = state.baseline.find((b) => b.uid === uid);
    const rowDiff = computeRowDiff(entry, baseEntry).get('substitutions')!;
    expect(rowDiff.statusByRowUid.get(rowA[ROW_UID_KEY] as string)).toBe(
      'clean'
    );
    expect(rowDiff.statusByRowUid.get(rowB[ROW_UID_KEY] as string)).toBe(
      'modified'
    );
  });
});

describe('rebaseline', () => {
  it('adopts a single-change save while preserving other pending edits', () => {
    let state = initState();
    const committedUid = uidOf(state, 'text_substitution');
    const pendingUid = uidOf(state, 'skip_and_merge');
    state = editorReducer(state, {
      type: 'updateConfig',
      uid: committedUid,
      config: { substitutions: [{ from: 'EXT.', to: 'EXTERIOR' }] },
    });
    state = editorReducer(state, {
      type: 'updateConfig',
      uid: pendingUid,
      config: { skip_types: ['title'] },
    });

    const single = buildSingleChangePayload(state, {
      type: 'entry',
      uid: committedUid,
    })!;
    // Simulate the server response to the single-change PUT
    const savedEntries: TextProcessorEntry[] = single.payload.map((e) => ({
      ...e,
      config_yaml:
        e.name === 'text_substitution'
          ? 'substitutions:\n  - from: EXT.\n    to: EXTERIOR\n'
          : e.config_yaml,
    }));
    state = editorReducer(state, {
      type: 'rebaseline',
      config: makeConfig(savedEntries, 'hash-2'),
      uidOrder: single.uidOrder,
    });

    const diff = computeDiff(state);
    expect(state.baseFileHash).toBe('hash-2');
    // Committed entry is clean and adopted the server's YAML round-trip
    expect(diff.statusByUid.get(committedUid)).toBe('clean');
    const committed = state.entries.find((e) => e.uid === committedUid);
    expect(committed?.config_yaml).toBe(
      'substitutions:\n  - from: EXT.\n    to: EXTERIOR\n'
    );
    // The other pending edit survived and still diffs against the new baseline
    expect(diff.statusByUid.get(pendingUid)).toBe('modified');
    expect(diff.total).toBe(1);
  });

  it('falls back to a full adopt when the response cannot be mapped to uids', () => {
    let state = initState();
    const uid = uidOf(state, 'skip_and_merge');
    state = editorReducer(state, {
      type: 'updateConfig',
      uid,
      config: { skip_types: ['title'] },
    });

    state = editorReducer(state, {
      type: 'rebaseline',
      config: makeConfig(ENTRIES, 'hash-3'),
      uidOrder: ['only-one-uid'],
    });

    expect(state.baseFileHash).toBe('hash-3');
    expect(computeDiff(state).dirty).toBe(false);
  });
});
