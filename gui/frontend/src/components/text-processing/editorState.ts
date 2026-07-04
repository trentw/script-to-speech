/**
 * Edit-buffer state for the text processor pipeline editor.
 *
 * The buffer mirrors the entries of the config file on disk (the source of
 * truth). It is initialized from a server read (keyed by file_hash) and
 * flushed back with a PUT carrying that hash for optimistic locking.
 *
 * A baseline snapshot of the last adopted server read makes dirtiness a
 * derived property (computeDiff) instead of a sticky flag: each entry is
 * clean/modified/added by comparison against its baseline twin (matched by
 * uid), deletions surface as tombstones, and reorders are a section-level
 * change. That is what enables inline per-change commit/discard
 * (buildSingleChangePayload) alongside "save all".
 */

import type { EntryPayload } from '../../services/textProcessorApi';
import type {
  ProcessorKind,
  ProcessorSchema,
  TextProcessorConfig,
  TextProcessorEntry,
} from '../../types/text-processing';

export interface EditorEntry extends TextProcessorEntry {
  /** Stable client-side key for list rendering and actions */
  uid: string;
  /** True when the user toggled this entry to raw YAML editing */
  rawMode: boolean;
}

/** A buffer entry as it looked in the last adopted server read */
export interface BaselineEntry extends TextProcessorEntry {
  /** Shared with the buffer entry it was adopted alongside */
  uid: string;
}

export interface EditorState {
  /** All entries in file order (preprocessors and processors interleaved by kind) */
  entries: EditorEntry[];
  /** Snapshot of the last adopted server read, in file order */
  baseline: BaselineEntry[];
  /** file_hash of the server read this buffer was initialized from */
  baseFileHash: string | null;
}

export type EditorAction =
  | { type: 'init'; config: TextProcessorConfig }
  | {
      /**
       * Adopt a server read produced by committing a single change while
       * keeping the other pending edits in the buffer. uidOrder maps the
       * returned entries back to buffer/baseline uids (see
       * buildSingleChangePayload).
       */
      type: 'rebaseline';
      config: TextProcessorConfig;
      uidOrder: string[];
    }
  | { type: 'replaceEntries'; entries: TextProcessorEntry[] }
  | { type: 'updateConfig'; uid: string; config: Record<string, unknown> }
  | { type: 'updateYaml'; uid: string; configYaml: string }
  | { type: 'rename'; uid: string; name: string; known: boolean }
  | { type: 'move'; uid: string; direction: 'up' | 'down' }
  | { type: 'remove'; uid: string }
  | {
      type: 'add';
      kind: ProcessorKind;
      name: string;
      config: Record<string, unknown> | null;
    }
  | { type: 'setRawMode'; uid: string; rawMode: boolean }
  | { type: 'revertEntry'; uid: string }
  | { type: 'restoreRemoved'; uid: string }
  | { type: 'revertOrder'; kind: ProcessorKind }
  | { type: 'revertRow'; entryUid: string; field: string; rowUid: string }
  | {
      type: 'restoreRemovedRow';
      entryUid: string;
      field: string;
      rowUid: string;
    };

let uidCounter = 0;
const nextUid = () => `entry-${++uidCounter}`;

/**
 * Rows inside list-of-object config fields (substitutions, replacements,
 * transformations) carry a client-only uid under this key — the row-level
 * analogue of the entry uid, enabling exact per-row dirty tracking and
 * per-row commit/test. Stripped from every payload (toEntryPayloads) and
 * from the raw-YAML editor seed.
 */
export const ROW_UID_KEY = '_uid';

let rowUidCounter = 0;
const nextRowUid = () => `row-${++rowUidCounter}`;

type ConfigObject = Record<string, unknown>;

const isRowObject = (value: unknown): value is ConfigObject =>
  value !== null && typeof value === 'object' && !Array.isArray(value);

/** A top-level config value that is a non-empty list of plain objects */
const isRowList = (value: unknown): value is ConfigObject[] =>
  Array.isArray(value) && value.length > 0 && value.every(isRowObject);

const rowUidOf = (row: ConfigObject): string | undefined =>
  typeof row[ROW_UID_KEY] === 'string'
    ? (row[ROW_UID_KEY] as string)
    : undefined;

const stripRow = (row: ConfigObject): ConfigObject => {
  if (!(ROW_UID_KEY in row)) return row;
  const { [ROW_UID_KEY]: _uid, ...rest } = row;
  return rest;
};

/** Assign row uids to any object rows that don't have one yet */
export function decorateRowUids(
  config: ConfigObject | null
): ConfigObject | null {
  if (!config) return config;
  let changed = false;
  const next: ConfigObject = { ...config };
  for (const [key, value] of Object.entries(config)) {
    if (!isRowList(value)) continue;
    if (value.every((row) => rowUidOf(row) !== undefined)) continue;
    next[key] = value.map((row) =>
      rowUidOf(row) !== undefined
        ? row
        : { ...row, [ROW_UID_KEY]: nextRowUid() }
    );
    changed = true;
  }
  return changed ? next : config;
}

/** Remove client-only row uids (the wire format never carries them) */
export function stripRowUids(config: ConfigObject | null): ConfigObject | null {
  if (!config) return config;
  let changed = false;
  const next: ConfigObject = { ...config };
  for (const [key, value] of Object.entries(config)) {
    if (!isRowList(value)) continue;
    if (value.every((row) => !(ROW_UID_KEY in row))) continue;
    next[key] = value.map(stripRow);
    changed = true;
  }
  return changed ? next : config;
}

/**
 * Re-decorate a server-returned config, re-adopting row uids from candidate
 * configs (buffer first, then the old baseline) by content match. Every row
 * the server echoes back was sent from one of the candidates, so matching
 * recovers identity; genuinely new content gets a fresh uid.
 */
function adoptRowUids(
  config: ConfigObject | null,
  candidates: Array<ConfigObject | null | undefined>
): ConfigObject | null {
  if (!config) return config;
  const next: ConfigObject = { ...config };
  for (const [key, value] of Object.entries(config)) {
    if (!isRowList(value)) continue;
    const pool: ConfigObject[] = [];
    for (const candidate of candidates) {
      const rows = candidate?.[key];
      if (Array.isArray(rows)) {
        pool.push(...rows.filter(isRowObject).filter((r) => rowUidOf(r)));
      }
    }
    const consumed = new Set<number>();
    const usedUids = new Set<string>();
    next[key] = value.map((row) => {
      const stripped = stripRow(row);
      for (let i = 0; i < pool.length; i++) {
        if (consumed.has(i)) continue;
        const candidateRow = pool[i] as ConfigObject;
        const candidateUid = rowUidOf(candidateRow) as string;
        if (usedUids.has(candidateUid)) continue;
        if (deepEqual(stripped, stripRow(candidateRow))) {
          consumed.add(i);
          usedUids.add(candidateUid);
          return { ...row, [ROW_UID_KEY]: candidateUid };
        }
      }
      return { ...row, [ROW_UID_KEY]: nextRowUid() };
    });
  }
  return next;
}

const toEditorEntry = (
  entry: TextProcessorEntry,
  rawMode = false
): EditorEntry => ({
  ...entry,
  config: decorateRowUids(entry.config),
  uid: nextUid(),
  rawMode,
});

export const initialEditorState: EditorState = {
  entries: [],
  baseline: [],
  baseFileHash: null,
};

function deepEqual(a: unknown, b: unknown): boolean {
  if (a === b) return true;
  if (typeof a !== typeof b) return false;
  if (Array.isArray(a) || Array.isArray(b)) {
    if (!Array.isArray(a) || !Array.isArray(b) || a.length !== b.length) {
      return false;
    }
    return a.every((value, i) => deepEqual(value, b[i]));
  }
  if (a !== null && b !== null && typeof a === 'object') {
    const aRecord = a as Record<string, unknown>;
    const bRecord = b as Record<string, unknown>;
    const aKeys = Object.keys(aRecord);
    if (aKeys.length !== Object.keys(bRecord).length) return false;
    return aKeys.every(
      (key) => key in bRecord && deepEqual(aRecord[key], bRecord[key])
    );
  }
  return false;
}

/**
 * Semantic equality between a buffer entry and its baseline twin. When the
 * buffer entry carries raw YAML text it is authoritative, so compare texts;
 * a form-edited entry cleared its config_yaml, so compare structured configs.
 */
export function entryEquals(
  buffer: TextProcessorEntry,
  base: TextProcessorEntry
): boolean {
  if (buffer.name !== base.name || buffer.kind !== base.kind) return false;
  const bufferYaml = buffer.config_yaml ?? '';
  if (bufferYaml.trim() !== '') {
    return bufferYaml === (base.config_yaml ?? '');
  }
  // Row uids are client bookkeeping, not content
  return deepEqual(
    stripRowUids(buffer.config ?? null),
    stripRowUids(base.config ?? null)
  );
}

const initFromConfig = (config: TextProcessorConfig): EditorState => {
  const entries = config.entries.map((entry) => toEditorEntry(entry));
  return {
    entries,
    baseline: entries.map(({ rawMode: _rawMode, ...wire }) => wire),
    baseFileHash: config.file_hash,
  };
};

/**
 * If an edited entry landed back on its baseline value, adopt the baseline
 * copy (restores the comment-bearing config_yaml so a later save doesn't
 * silently drop comments from an entry the user only touched transiently).
 */
const snapBack = (
  entries: EditorEntry[],
  baseline: BaselineEntry[],
  uid: string
): EditorEntry[] => {
  const base = baseline.find((b) => b.uid === uid);
  if (!base) return entries;
  return entries.map((entry) =>
    entry.uid === uid && entryEquals(entry, base)
      ? { ...base, rawMode: entry.rawMode }
      : entry
  );
};

export function editorReducer(
  state: EditorState,
  action: EditorAction
): EditorState {
  switch (action.type) {
    case 'init':
      return initFromConfig(action.config);

    case 'rebaseline': {
      // Guard against a server response that doesn't line up with the payload
      // we sent — fall back to a full adopt rather than mis-attributing uids.
      if (action.config.entries.length !== action.uidOrder.length) {
        return initFromConfig(action.config);
      }
      const oldBaseByUid = new Map(state.baseline.map((b) => [b.uid, b]));
      const bufferByUid = new Map(state.entries.map((e) => [e.uid, e]));
      const baseline: BaselineEntry[] = action.config.entries.map(
        (entry, index) => {
          const uid = action.uidOrder[index] as string;
          // Re-adopt row uids by content: every row the server echoed back
          // was sent from either the buffer or the old baseline
          const config = adoptRowUids(entry.config, [
            bufferByUid.get(uid)?.config,
            oldBaseByUid.get(uid)?.config,
          ]);
          return { ...entry, config, uid };
        }
      );
      const baseByUid = new Map(baseline.map((b) => [b.uid, b]));
      // Buffer entries now matching the new baseline adopt the server copy
      // (picks up the round-tripped config_yaml); pending edits stay put.
      const entries = state.entries.map((entry) => {
        const base = baseByUid.get(entry.uid);
        return base && entryEquals(entry, base)
          ? { ...base, rawMode: entry.rawMode }
          : entry;
      });
      return { entries, baseline, baseFileHash: action.config.file_hash };
    }

    case 'replaceEntries':
      // Load a different pipeline (e.g. the global default) into the buffer.
      // The baseline stays put: the diff then reports the load as
      // adds/removals against what's on disk, which is what it is.
      return {
        ...state,
        entries: action.entries.map((entry) => toEditorEntry(entry)),
      };

    case 'updateConfig':
      return {
        ...state,
        entries: snapBack(
          state.entries.map((entry) =>
            entry.uid === action.uid
              ? // Form edits clear config_yaml: the structured config becomes
                // authoritative for this entry (comments in it are dropped).
                // Newly added rows get their uid here.
                {
                  ...entry,
                  config: decorateRowUids(action.config),
                  config_yaml: null,
                }
              : entry
          ),
          state.baseline,
          action.uid
        ),
      };

    case 'updateYaml':
      return {
        ...state,
        entries: snapBack(
          state.entries.map((entry) =>
            entry.uid === action.uid
              ? { ...entry, config_yaml: action.configYaml, config: null }
              : entry
          ),
          state.baseline,
          action.uid
        ),
      };

    case 'rename':
      return {
        ...state,
        entries: snapBack(
          state.entries.map((entry) =>
            entry.uid === action.uid
              ? { ...entry, name: action.name, known: action.known }
              : entry
          ),
          state.baseline,
          action.uid
        ),
      };

    case 'move': {
      // Reorder within the entry's own kind; the file keeps sections separate
      const moving = state.entries.find((e) => e.uid === action.uid);
      if (!moving) return state;
      const sameKind = state.entries.filter((e) => e.kind === moving.kind);
      const position = sameKind.findIndex((e) => e.uid === action.uid);
      const target = action.direction === 'up' ? position - 1 : position + 1;
      if (target < 0 || target >= sameKind.length) {
        return state;
      }
      const reordered = [...sameKind];
      const swapped = reordered[target] as EditorEntry;
      reordered[target] = reordered[position] as EditorEntry;
      reordered[position] = swapped;
      let cursor = 0;
      return {
        ...state,
        entries: state.entries.map((entry) =>
          entry.kind === moving.kind
            ? (reordered[cursor++] as EditorEntry)
            : entry
        ),
      };
    }

    case 'remove':
      return {
        ...state,
        entries: state.entries.filter((entry) => entry.uid !== action.uid),
      };

    case 'add': {
      const added = toEditorEntry({
        kind: action.kind,
        name: action.name,
        known: true,
        config: action.config,
        config_yaml: null,
      });
      // Insert at the end of the entry's kind group
      const lastIndex = state.entries.reduce(
        (acc, entry, index) => (entry.kind === action.kind ? index : acc),
        -1
      );
      const entries = [...state.entries];
      entries.splice(lastIndex + 1, 0, added);
      return { ...state, entries };
    }

    case 'setRawMode':
      return {
        ...state,
        entries: state.entries.map((entry) =>
          entry.uid === action.uid
            ? { ...entry, rawMode: action.rawMode }
            : entry
        ),
      };

    case 'revertEntry': {
      const base = state.baseline.find((b) => b.uid === action.uid);
      if (!base) {
        // Added entry: reverting means dropping it
        return {
          ...state,
          entries: state.entries.filter((entry) => entry.uid !== action.uid),
        };
      }
      return {
        ...state,
        entries: state.entries.map((entry) =>
          entry.uid === action.uid ? { ...base, rawMode: entry.rawMode } : entry
        ),
      };
    }

    case 'restoreRemoved': {
      const baseIndex = state.baseline.findIndex((b) => b.uid === action.uid);
      if (
        baseIndex < 0 ||
        state.entries.some((entry) => entry.uid === action.uid)
      ) {
        return state;
      }
      const base = state.baseline[baseIndex] as BaselineEntry;
      // Reinsert after the nearest preceding same-kind baseline sibling that
      // is still in the buffer; with none, at the top of its kind group.
      let insertAt = -1;
      for (let j = baseIndex - 1; j >= 0 && insertAt < 0; j--) {
        const prev = state.baseline[j] as BaselineEntry;
        if (prev.kind !== base.kind) continue;
        const bufferIndex = state.entries.findIndex(
          (entry) => entry.uid === prev.uid
        );
        if (bufferIndex >= 0) insertAt = bufferIndex + 1;
      }
      if (insertAt < 0) {
        const firstSameKind = state.entries.findIndex(
          (entry) => entry.kind === base.kind
        );
        insertAt =
          firstSameKind >= 0
            ? firstSameKind
            : base.kind === 'preprocessor'
              ? 0
              : state.entries.length;
      }
      const entries = [...state.entries];
      entries.splice(insertAt, 0, { ...base, rawMode: false });
      return { ...state, entries };
    }

    case 'revertRow': {
      // Revert one row to its on-disk content (added rows are dropped)
      const base = state.baseline.find((b) => b.uid === action.entryUid);
      const baseValue = base?.config?.[action.field];
      const baseRows = isRowList(baseValue) ? baseValue : [];
      const baseRow = baseRows.find((r) => rowUidOf(r) === action.rowUid);
      const entries = state.entries.map((entry) => {
        if (entry.uid !== action.entryUid || !entry.config) return entry;
        const value = entry.config[action.field];
        if (!Array.isArray(value)) return entry;
        const rows = (value as ConfigObject[]).filter(isRowObject);
        const nextRows = baseRow
          ? rows.map((r) => (rowUidOf(r) === action.rowUid ? baseRow : r))
          : rows.filter((r) => rowUidOf(r) !== action.rowUid);
        return {
          ...entry,
          config: { ...entry.config, [action.field]: nextRows },
        };
      });
      return {
        ...state,
        entries: snapBack(entries, state.baseline, action.entryUid),
      };
    }

    case 'restoreRemovedRow': {
      // Reinsert a deleted row where it used to sit, from baseline content
      const base = state.baseline.find((b) => b.uid === action.entryUid);
      const baseValue = base?.config?.[action.field];
      const baseRows = isRowList(baseValue) ? baseValue : [];
      const baseIndex = baseRows.findIndex(
        (r) => rowUidOf(r) === action.rowUid
      );
      if (baseIndex < 0) return state;
      const baseRow = baseRows[baseIndex] as ConfigObject;
      const entries = state.entries.map((entry) => {
        if (entry.uid !== action.entryUid) return entry;
        const value = entry.config?.[action.field];
        const rows = Array.isArray(value) ? [...(value as ConfigObject[])] : [];
        if (rows.some((r) => isRowObject(r) && rowUidOf(r) === action.rowUid)) {
          return entry;
        }
        let insertAt = 0;
        for (let j = baseIndex - 1; j >= 0 && insertAt === 0; j--) {
          const prevUid = rowUidOf(baseRows[j] as ConfigObject);
          const bufferIndex = rows.findIndex(
            (r) => isRowObject(r) && rowUidOf(r) === prevUid
          );
          if (bufferIndex >= 0) insertAt = bufferIndex + 1;
        }
        rows.splice(insertAt, 0, baseRow);
        return {
          ...entry,
          config: { ...(entry.config ?? {}), [action.field]: rows },
        };
      });
      return {
        ...state,
        entries: snapBack(entries, state.baseline, action.entryUid),
      };
    }

    case 'revertOrder': {
      const baseUids = new Set(state.baseline.map((b) => b.uid));
      const kindEntries = state.entries.filter(
        (entry) => entry.kind === action.kind
      );
      const survivorByUid = new Map(
        kindEntries
          .filter((entry) => baseUids.has(entry.uid))
          .map((entry) => [entry.uid, entry])
      );
      const orderedSurvivors = state.baseline
        .filter((b) => b.kind === action.kind)
        .map((b) => survivorByUid.get(b.uid))
        .filter((entry): entry is EditorEntry => entry !== undefined);
      // Added entries have no baseline position: keep them at the end of the
      // kind group in their current relative order.
      const addedEntries = kindEntries.filter(
        (entry) => !baseUids.has(entry.uid)
      );
      const reordered = [...orderedSurvivors, ...addedEntries];
      let cursor = 0;
      return {
        ...state,
        entries: state.entries.map((entry) =>
          entry.kind === action.kind
            ? (reordered[cursor++] as EditorEntry)
            : entry
        ),
      };
    }

    default:
      return state;
  }
}

export type EntryStatus = 'clean' | 'modified' | 'added';

export interface RemovedEntry {
  entry: BaselineEntry;
  /**
   * uid of the nearest preceding same-kind baseline sibling still in the
   * buffer (where the tombstone row should render); null → top of section
   */
  afterUid: string | null;
}

export interface EditorDiff {
  dirty: boolean;
  statusByUid: Map<string, EntryStatus>;
  removed: RemovedEntry[];
  orderChanged: Record<ProcessorKind, boolean>;
  counts: {
    added: number;
    modified: number;
    removed: number;
    orderChanges: number;
  };
  /** Badge number: added + modified + removed + order changes */
  total: number;
  /** Human-readable one-liners for the save/discard tooltip */
  details: string[];
}

const SECTION_TITLES: Record<ProcessorKind, string> = {
  preprocessor: 'Structure',
  processor: 'Text',
};

const KINDS: ProcessorKind[] = ['preprocessor', 'processor'];

/** Derive the full dirty picture of the buffer vs the baseline. Pure. */
export function computeDiff(state: EditorState): EditorDiff {
  const baseByUid = new Map(state.baseline.map((b) => [b.uid, b]));
  const bufferUids = new Set(state.entries.map((entry) => entry.uid));

  const statusByUid = new Map<string, EntryStatus>();
  const details: string[] = [];
  let added = 0;
  let modified = 0;

  for (const entry of state.entries) {
    const base = baseByUid.get(entry.uid);
    if (!base) {
      statusByUid.set(entry.uid, 'added');
      added++;
      details.push(`Added: ${entry.name}`);
    } else if (!entryEquals(entry, base)) {
      statusByUid.set(entry.uid, 'modified');
      modified++;
      details.push(`Modified: ${entry.name}`);
    } else {
      statusByUid.set(entry.uid, 'clean');
    }
  }

  const removed: RemovedEntry[] = [];
  state.baseline.forEach((base, index) => {
    if (bufferUids.has(base.uid)) return;
    let afterUid: string | null = null;
    for (let j = index - 1; j >= 0 && afterUid === null; j--) {
      const prev = state.baseline[j] as BaselineEntry;
      if (prev.kind === base.kind && bufferUids.has(prev.uid)) {
        afterUid = prev.uid;
      }
    }
    removed.push({ entry: base, afterUid });
    details.push(`Removed: ${base.name}`);
  });

  const orderChanged = {
    preprocessor: false,
    processor: false,
  } as Record<ProcessorKind, boolean>;
  let orderChanges = 0;
  for (const kind of KINDS) {
    // Compare the surviving entries' sequence in both orders; adds/removes
    // don't count as order changes on their own.
    const baseSequence = state.baseline
      .filter((b) => b.kind === kind && bufferUids.has(b.uid))
      .map((b) => b.uid);
    const bufferSequence = state.entries
      .filter((entry) => entry.kind === kind && baseByUid.has(entry.uid))
      .map((entry) => entry.uid);
    const changed = baseSequence.some(
      (uid, index) => uid !== bufferSequence[index]
    );
    orderChanged[kind] = changed;
    if (changed) {
      orderChanges++;
      details.push(`Order changed: ${SECTION_TITLES[kind]}`);
    }
  }

  const total = added + modified + removed.length + orderChanges;
  return {
    dirty: total > 0,
    statusByUid,
    removed,
    orderChanged,
    counts: { added, modified, removed: removed.length, orderChanges },
    total,
    details,
  };
}

export type RowStatus = 'clean' | 'modified' | 'added';

export interface RemovedRow {
  /** The baseline row (row uid still attached) missing from the buffer */
  row: Record<string, unknown>;
  uid: string;
  /** Row uid of the nearest preceding surviving row; null → top of the list */
  afterRowUid: string | null;
}

export interface ListFieldDiff {
  statusByRowUid: Map<string, RowStatus>;
  removedRows: RemovedRow[];
}

/**
 * Per-row dirty status for an entry's list-of-object fields, matched by row
 * uid against the baseline twin. Rows without a baseline counterpart are
 * 'added'; baseline rows missing from the buffer surface as removedRows.
 */
export function computeRowDiff(
  entry: TextProcessorEntry,
  base: TextProcessorEntry | null | undefined
): Map<string, ListFieldDiff> {
  const result = new Map<string, ListFieldDiff>();
  const config = entry.config;
  if (!config) return result;

  const fieldKeys = new Set<string>();
  for (const [key, value] of Object.entries(config)) {
    if (isRowList(value)) fieldKeys.add(key);
  }
  for (const [key, value] of Object.entries(base?.config ?? {})) {
    if (isRowList(value)) fieldKeys.add(key);
  }

  for (const key of fieldKeys) {
    const bufferRows = (
      isRowList(config[key]) ? (config[key] as ConfigObject[]) : []
    ).filter((row) => rowUidOf(row) !== undefined);
    const baseRows = (
      isRowList(base?.config?.[key])
        ? ((base?.config?.[key] ?? []) as ConfigObject[])
        : []
    ).filter((row) => rowUidOf(row) !== undefined);

    const baseByUid = new Map(baseRows.map((row) => [rowUidOf(row), row]));
    const bufferUids = new Set(bufferRows.map((row) => rowUidOf(row)));

    const statusByRowUid = new Map<string, RowStatus>();
    for (const row of bufferRows) {
      const uid = rowUidOf(row) as string;
      const baseRow = baseByUid.get(uid);
      statusByRowUid.set(
        uid,
        !baseRow
          ? 'added'
          : deepEqual(stripRow(row), stripRow(baseRow))
            ? 'clean'
            : 'modified'
      );
    }

    const removedRows: RemovedRow[] = [];
    baseRows.forEach((row, index) => {
      const uid = rowUidOf(row) as string;
      if (bufferUids.has(uid)) return;
      let afterRowUid: string | null = null;
      for (let j = index - 1; j >= 0 && afterRowUid === null; j--) {
        const prevUid = rowUidOf(baseRows[j] as ConfigObject) as string;
        if (bufferUids.has(prevUid)) afterRowUid = prevUid;
      }
      removedRows.push({ row, uid, afterRowUid });
    });

    if (statusByRowUid.size > 0 || removedRows.length > 0) {
      result.set(key, { statusByRowUid, removedRows });
    }
  }
  return result;
}

/**
 * Top-level config fields (excluding row lists, which computeRowDiff covers)
 * whose value differs from the baseline — powers per-field dirty dots.
 */
export function changedScalarFields(
  entry: TextProcessorEntry,
  base: TextProcessorEntry | null | undefined
): Set<string> {
  const changed = new Set<string>();
  const bufferConfig = entry.config ?? {};
  const baseConfig = base?.config ?? {};
  const keys = new Set([
    ...Object.keys(bufferConfig),
    ...Object.keys(baseConfig),
  ]);
  for (const key of keys) {
    const bufferValue = bufferConfig[key];
    const baseValue = baseConfig[key];
    if (isRowList(bufferValue) || isRowList(baseValue)) continue;
    if (!deepEqual(bufferValue ?? null, baseValue ?? null)) changed.add(key);
  }
  return changed;
}

/** One dirty change, addressable for inline commit / test */
export type DirtyChangeRef =
  | { type: 'entry'; uid: string }
  | { type: 'removal'; uid: string }
  | { type: 'order'; kind: ProcessorKind };

/** One dirty row inside an entry's list field ('rowRemoval' = deleted row) */
export interface RowChangeRef {
  type: 'row' | 'rowRemoval';
  entryUid: string;
  field: string;
  rowUid: string;
}

export type AnyChangeRef = DirtyChangeRef | RowChangeRef;

/** Stable identity of a dirty change, for matching test results to their source */
export function changeKey(change: AnyChangeRef): string {
  switch (change.type) {
    case 'order':
      return `order-${change.kind}`;
    case 'row':
    case 'rowRemoval':
      return `${change.type}-${change.entryUid}-${change.field}-${change.rowUid}`;
    default:
      return `${change.type}-${change.uid}`;
  }
}

/** Whether a test-result key describes a change inside the given entry */
export function changeKeyBelongsToEntry(
  key: string,
  entryUid: string
): boolean {
  return (
    key === `entry-${entryUid}` ||
    key.startsWith(`row-${entryUid}-`) ||
    key.startsWith(`rowRemoval-${entryUid}-`)
  );
}

export interface SingleChangePayload {
  payload: EntryPayload[];
  /** uid per payload entry, for re-baselining against the PUT response */
  uidOrder: string[];
}

/**
 * Build a PUT payload equal to the baseline (what's on disk) with exactly one
 * dirty change applied — the write behind the inline "save this change"
 * buttons. Order commits use baseline entry data so uncommitted content edits
 * don't leak into them; added entries anchor after their nearest preceding
 * buffer sibling that exists in the baseline.
 */
export function buildSingleChangePayload(
  state: EditorState,
  change: DirtyChangeRef
): SingleChangePayload | null {
  const baseByUid = new Map(state.baseline.map((b) => [b.uid, b]));

  const toResult = (
    sequence: Array<TextProcessorEntry & { uid: string }>
  ): SingleChangePayload => ({
    payload: toEntryPayloads(sequence),
    uidOrder: sequence.map((entry) => entry.uid),
  });

  switch (change.type) {
    case 'entry': {
      const entry = state.entries.find((e) => e.uid === change.uid);
      if (!entry) return null;
      if (baseByUid.has(entry.uid)) {
        // Modified: replace in place, baseline order
        return toResult(
          state.baseline.map((b) => (b.uid === entry.uid ? entry : b))
        );
      }
      // Added: anchor after the nearest preceding same-kind buffer sibling
      // that exists in the baseline
      const bufferIndex = state.entries.indexOf(entry);
      let anchorUid: string | null = null;
      for (let j = bufferIndex - 1; j >= 0 && anchorUid === null; j--) {
        const prev = state.entries[j] as EditorEntry;
        if (prev.kind === entry.kind && baseByUid.has(prev.uid)) {
          anchorUid = prev.uid;
        }
      }
      const sequence: Array<TextProcessorEntry & { uid: string }> = [
        ...state.baseline,
      ];
      let insertAt: number;
      if (anchorUid !== null) {
        insertAt = sequence.findIndex((b) => b.uid === anchorUid) + 1;
      } else {
        const firstSameKind = sequence.findIndex((b) => b.kind === entry.kind);
        if (firstSameKind >= 0) {
          insertAt = firstSameKind;
        } else {
          // No same-kind entries on disk: preprocessors go before processors
          const firstProcessor = sequence.findIndex(
            (b) => b.kind === 'processor'
          );
          insertAt =
            entry.kind === 'preprocessor' && firstProcessor >= 0
              ? firstProcessor
              : sequence.length;
        }
      }
      sequence.splice(insertAt, 0, entry);
      return toResult(sequence);
    }

    case 'removal': {
      if (!baseByUid.has(change.uid)) return null;
      return toResult(state.baseline.filter((b) => b.uid !== change.uid));
    }

    case 'order': {
      // Surviving entries in buffer order fill the survivor slots of the
      // baseline kind subsequence; pending removals keep their positions.
      const survivorQueue = state.entries
        .filter(
          (entry) => entry.kind === change.kind && baseByUid.has(entry.uid)
        )
        .map((entry) => baseByUid.get(entry.uid) as BaselineEntry);
      const survivorUids = new Set(survivorQueue.map((b) => b.uid));
      let cursor = 0;
      return toResult(
        state.baseline.map((b) =>
          b.kind === change.kind && survivorUids.has(b.uid)
            ? (survivorQueue[cursor++] as BaselineEntry)
            : b
        )
      );
    }

    default:
      return null;
  }
}

/**
 * Build a PUT payload equal to the baseline with exactly one row change
 * applied inside one entry — the row-level analogue of
 * buildSingleChangePayload. The target entry's config becomes authoritative
 * (config_yaml cleared), matching what any form edit of that entry does.
 */
export function buildSingleRowChangePayload(
  state: EditorState,
  change: RowChangeRef
): SingleChangePayload | null {
  const base = state.baseline.find((b) => b.uid === change.entryUid);
  if (!base?.config) return null;
  const baseValue = base.config[change.field];
  const baseRows = isRowList(baseValue) ? baseValue : [];

  let nextRows: ConfigObject[] | null = null;
  if (change.type === 'rowRemoval') {
    if (!baseRows.some((row) => rowUidOf(row) === change.rowUid)) return null;
    nextRows = baseRows.filter((row) => rowUidOf(row) !== change.rowUid);
  } else {
    const bufferEntry = state.entries.find((e) => e.uid === change.entryUid);
    const bufferValue = bufferEntry?.config?.[change.field];
    const bufferRows = isRowList(bufferValue) ? bufferValue : [];
    const row = bufferRows.find((r) => rowUidOf(r) === change.rowUid);
    if (!row) return null;

    if (baseRows.some((r) => rowUidOf(r) === change.rowUid)) {
      // Modified: replace in place, baseline row order
      nextRows = baseRows.map((r) => (rowUidOf(r) === change.rowUid ? row : r));
    } else {
      // Added: anchor after the nearest preceding buffer sibling that exists
      // in the baseline (none → top of the list)
      const bufferIndex = bufferRows.indexOf(row);
      let anchorUid: string | null = null;
      for (let j = bufferIndex - 1; j >= 0 && anchorUid === null; j--) {
        const prevUid = rowUidOf(bufferRows[j] as ConfigObject);
        if (prevUid && baseRows.some((r) => rowUidOf(r) === prevUid)) {
          anchorUid = prevUid;
        }
      }
      const rows = [...baseRows];
      const insertAt =
        anchorUid === null
          ? 0
          : rows.findIndex((r) => rowUidOf(r) === anchorUid) + 1;
      rows.splice(insertAt, 0, row);
      nextRows = rows;
    }
  }

  const sequence = state.baseline.map((b) =>
    b.uid === change.entryUid
      ? {
          ...b,
          config: { ...base.config, [change.field]: nextRows },
          config_yaml: null,
        }
      : b
  );
  return {
    payload: toEntryPayloads(sequence),
    uidOrder: sequence.map((entry) => entry.uid),
  };
}

/** Strip client-only fields (entry uid, rawMode, row uids) for the API payload */
export function toEntryPayloads(
  entries: readonly TextProcessorEntry[]
): EntryPayload[] {
  return entries.map(({ kind, name, known, config, config_yaml }) => ({
    kind,
    name,
    known,
    config: stripRowUids(config),
    config_yaml,
  }));
}

/** Build a minimal starting config for a newly added processor */
export function buildDefaultConfig(
  schema: ProcessorSchema | null
): Record<string, unknown> | null {
  if (!schema) return null;

  const config: Record<string, unknown> = {};
  for (const field of schema.fields) {
    if (field.default !== undefined) {
      config[field.name] = field.default;
    } else if (field.required) {
      if (field.type === 'list') {
        config[field.name] = [];
      } else if (field.type === 'dict_of_string_lists') {
        config[field.name] = {};
      }
    }
  }
  return Object.keys(config).length > 0 ? config : null;
}
