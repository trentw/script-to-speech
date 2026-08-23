# Plan: Chunk-Level Audio Editing → Screenplay Viewer → PDF Overlay → Editor Mode

Status: agreed 2026-07-05. M0 + M1 shipped 2026-07-05; M2 first pass
implemented 2026-07-05; M3 (PDF overlay only; raw-chunk lens deferred)
implemented 2026-07-06.

## Vision

Let users work with the screenplay at the chunk level, end to end:

1. Search and pull up any chunk (not just missing/silent ones) and re-record it —
   either re-running generation with current settings or editing the text sent to
   the provider (pronunciation fixes) — reusing the review-audio flow UI.
2. See how many dialogue items share a single cached audio file (dedup via the
   hash-based cache) when editing.
3. A sequential, readable listing of all chunks with audio status and playback,
   including play-in-sequence.
4. A PDF overlay view: chunks anchored onto the rendered screenplay PDF, with a
   toggle back to the sequential view.
5. Editor mode: change chunk text/type/speaker, split/insert/delete chunks, with
   the chunk JSON as source of truth and cache regeneration "just working" via
   the existing hash mechanics.
6. Guardrails: warnings before re-parsing or bulk operations that would blow away
   manual work.

## Design principles

- **Files are the source of truth.** Everything recomputes from the chunk JSON,
  voice config, text-processor config, and hash-named cache files. In-memory
  caches are allowed but explicitly cleared and rebuilt on mutation — never
  incrementally synced.
- **GUI backend imports the library; never forks logic.** `plan_audio_generation()`
  is the single planning brain (the review page already uses it as a dry run).
- **Minimal, additive core changes.** The CLI pipeline is battle-tested. The
  whole arc requires exactly two small additive core changes (cache filename
  resolution in the planner; an optional parameter on
  `generate_standalone_speech`) plus, later, optional in-memory provenance
  annotations in preprocessors.
- **Follow the Text Processor editor conventions** for frontend features:
  `types/<feature>.ts` → `services/<feature>Api.ts` → `hooks/queries|mutations/`
  → `components/<feature>/`, edit-buffer reducer state, optimistic locking via
  file hash, colocated tests, docs updates.

## Cache filename convention (the one one-way door)

```
Pipeline-generated:      {original_hash}~~{processed_hash}~~{provider_id}~~{speaker_id}.mp3
User re-roll committed:  {original_hash}~~{processed_hash}~~{provider_id}~~{speaker_id}~~retake.mp3
User edited-text commit: {original_hash}~~{processed_hash}~~{provider_id}~~{speaker_id}~~edit.mp3
```

- `original_hash` = md5(pre-processor text + speaker); `processed_hash` =
  md5(post-processor text + speaker). Both are computed on **post-preprocessed**
  chunks (`processing.py`). No normalization is applied.
- The optional 5th `~~` field is the **user-modified flag**. Only `edit` and
  `retake` are defined; readers treat the field as an extensible token (unknown
  values parse as "user-modified, unknown flavor").
- **Flags never affect cache behavior.** A chunk is a cache hit if any flavor of
  its base name exists.
- **Authority ladder** when multiple flavors of one base name coexist:
  `edit` > `retake` > plain (manual work wins). Commit maintains the invariant of
  at most one file per base name by removing superseded siblings; the ladder is
  the deterministic tiebreak for anomalies (hand-copied files, interrupted ops).
- **Backwards compatible:** old 4-field names remain the primary match; nothing
  is migrated. Pre-existing files and untagged variants stay unmarked ("fix
  forward" only).
- Central definition: `src/script_to_speech/audio_generation/cache_filenames.py`
  owns the delimiter, flags, ladder, and all build/parse/resolve helpers.
  Nothing else may split on `~~`. The frontend never parses filenames; it gets
  flags via API fields.

### Provenance is fixed at generation time

Predictability rule: user-modified status is decided **once, when audio is
generated**, and only ever copied after that.

1. The GUI generation request carries an explicit `generation_kind`
   (`retake` | `edit`). The frontend sets it by strict text equality against the
   clip's processed text at the moment Generate is clicked — never by which UI
   component is open.
2. `generate_standalone_speech` accepts the kind as an optional parameter and
   encodes it as a trailing `--retake` / `--edit` token in the variant filename.
   It also stamps the generation text + kind into ID3 `TXXX` frames, so the
   text that produced the audio travels with the file (commit copies it along).
   Default (no kind) behavior is byte-identical to today, including the
   `sts-generate-standalone-speech` CLI.
3. Commit is a pure, inference-free rename: parse the token off the variant
   filename → map to the cache flag → write `{base}~~{flag}.mp3` → remove
   superseded siblings. Untagged variants (including all pre-existing ones)
   commit to the plain name exactly as today.

### "Full filename match" audit

Every site that constructs or compares cache filenames:

| Site | Behavior |
|---|---|
| `plan_audio_generation` hit check (`processing.py`) | resolve expected plain name via ladder; task's `cache_filename`/`cache_filepath` point at the resolved file; `user_modified_flag` recorded on the task. **The core change.** |
| Duplicate tracking (`processing.py`) | unchanged — identical chunks resolve identically |
| `apply_cache_overrides` | unchanged — keyed by `task.cache_filename` (resolved), consistent with reported names; override replaces the resolved file in place |
| `check_for_silence` | user-modified files are scanned and reported like any other clip, but never flipped to a miss (auto-regeneration would overwrite manual work) |
| `download_manager` write | unchanged — misses always carry the plain name |
| Reporting keys | unchanged — misses have no file to resolve |
| `ReviewService.commit_variant` | computes target name from variant token; strips flags from the requested target to get the base; removes superseded siblings |
| `get_cache_audio` route | unchanged — clients pass the actual on-disk name they got from the backend |
| Frontend `clip.cacheFilename` | still the literal actual name; `user_modified` arrives as a separate API field |

Silence-check semantics for user-modified files: they are scanned and reported
exactly like every other clip (consistency over the small time saving), but a
silent result never flips them to a cache miss — auto-regeneration would
silently overwrite deliberate manual work. The review UI surfaces them with
their user-modified badge so the user decides.

## Milestones

### M0 — Chunk inventory service (foundation) — first pass

Read-only inventory computed on demand from `plan_audio_generation()`:

- `gui_backend/services/chunk_inventory_service.py` +
  `routers/chunks.py` → `GET /api/chunks/{project}/inventory`.
- Per entry: task idx, type, speaker, original/processed text, resolved cache
  filename, status (`cached` / `missing` / `expected_silence`), `user_modified`
  flag, and occurrences (indices of tasks sharing the same audio file).
- Response carries a per-speaker config map (provider, config, sts_id) so the
  frontend can build generation requests without a per-chunk payload bloat.
- Module-level per-project cache, explicitly invalidated on variant commit,
  text-processor config write, parse, audiobook-run completion; `?refresh=true`
  escape hatch. Search/filtering is client-side (~1–2k chunks is small).
- Shared project-loading helper extracted from `ReviewService` (used by both).

### M1 — Search + edit any chunk in Review Audio, and the sentinel — first pass

- Core: `cache_filenames.py` module; ladder resolution in
  `plan_audio_generation`; silence-check protection for user-modified files
  (scanned + reported, never auto-regenerated); `generation_kind` on
  `generate_standalone_speech` (+ variant token + ID3 stamp). Full unit tests.
- Backend: commit rework (token → flag, sibling removal, inventory
  invalidation); `generation_kind` through the generation request model.
- Frontend: "Find chunks" section on the review page (text/speaker/type/status
  filters over the inventory); clip cards generalized to any chunk; occurrence
  badge ("audio shared by N chunks") and user-modified badge; `generation_kind`
  computed at generate time.
- Docs: filename convention (public contract), user guide, changelog.

### M2 — Sequential screenplay viewer — first pass

- Route `/project/viewer` (`/project/screenplay` was already taken by the
  Screenplay Info page): virtualized list (`@tanstack/react-virtual`) of
  post-preprocessed chunks styled for reading (screenplay-flavored: emphasized
  scene headings with dividers, speaker above indented dialogue, centered
  italic parentheticals); status markers + play per chunk.
- Click a chunk → a persistent split panel (list narrows, clicking rows swaps
  content) hosting the M1 chunk-audio editor plus the advanced details
  (original vs processed text, cache filename, shared-audio occurrences with
  jump links). Details live only in the panel — no global advanced toggle.
- All playback flows through the app-wide `AudioService` singleton, with the
  built-in footer transport (`UniversalAudioPlayer`) visible on the route.
  Additive core-frontend change: `AudioService` gained a monotonic
  `endedCount` + `subscribeEnded()` (natural end-of-audio events) that the
  sequential controller chains on.
- Sequential playback (`useSequentialPlayback`): row play plays one chunk;
  per-row "play from here" and toolbar "Play all" chain chunks with the
  concatenator's 500 ms gap (suppressed after expected-silence chunks, which
  contribute their 10 ms clip length); missing chunks are skipped (persistent
  row marker); highlight + auto-scroll follows the active row until the user
  scrolls (a "Jump to current" pill restores follow); playing any other clip
  in the app cancels the sequence; footer pause halts the chain, resume
  continues it.
- Raw-JSON view mode deferred to M3; the viewer takes its list as a prop so the
  second lens slots in without rework.

### M3 — PDF overlay view — implemented 2026-07-06

**Scope decision (2026-07-06): PDF overlay only.** The raw-chunk lens and its
`source_idxs` preprocessor provenance were **deferred out of M3** — the PDF
anchoring matches post-preprocessed `raw_text` directly and did not need
provenance, so the four preprocessors were left untouched. The raw-chunk
sequential lens remains a future pass.

- `react-pdf` (pdf.js, worker bundled locally via Vite `?url` — Tauri is
  offline; CSP is `null`) with a **List | PDF** `ToggleGroup` inside
  `/project/viewer`. `PdfLens` is `React.lazy`-loaded (own `pdf-vendor` chunk).
- Chunk→position mapping computed at view time (nothing persisted):
  `extract_words_by_page` (new, in `parser/utils/text_utils.py`, same
  `dedupe_chars` + tolerances as parse time) feeds a pure monotonic matcher
  (`gui_backend/services/pdf_anchor_service.py`) that walks each chunk's
  `raw_text` against the page word stream, tolerating header/footer/merge gaps
  and reusing a recent-match cache for shared-`raw_text` chunks (parenthetical
  splits, dual dialogue). Endpoints on `routers/chunks.py`:
  `GET /chunks/{p}/pdf-anchors` (line rects + page dims + unanchored idxs) and
  `GET /chunks/{p}/source-pdf` (FileResponse). In-memory per-project cache,
  invalidated on re-parse and text-processor config write only (audio
  mutations can't move a chunk on the page). Real screenplays anchor at
  99.8–100%. Chunks that can't be anchored aren't drawn (an "N chunks not
  shown" indicator); the sequential list remains the complete fallback.
- Frontend: `ScreenplayViewer` became the shell (selection + sequential
  playback + detail panel live there, surviving lens switches); the list moved
  to `ChunkListView`; the PDF lens is `components/viewer/pdf/` (`PdfLens`,
  `PdfPageView`, `SourceRegionOverlay`, pure `pdfOverlayLogic`). PDF clicks are
  intentionally selection-only: playback and editing stay in the persistent
  panel. Chunks derived from identical source geometry share one composite
  overlay with a count and a panel navigator, avoiding stacked controls. Overlay
  color communicates availability; separate persistent markers communicate
  edited-text/custom-take provenance.
- Also folded in three M2 review fixes: idx-vs-position resolution
  (`buildPositionByIdx`), a shared `formatRelativeTime` (was triplicated), and
  a single-sourced playback-failure toast in `useSequentialPlayback`. Fixed a
  latent `ToggleGroup` import bug surfaced by first use.

### M4 — Editor mode

- Chunk CRUD on `input/{p}/{p}.json` via gui_backend endpoints: edit
  text/speaker/type, split, insert, delete, merge. Optimistic locking via file
  hash (409 pattern), edit-buffer reducer with in-memory row uids. No persisted
  IDs; order stays positional.
- Cache regeneration "just works": edited text → new `original_hash` → miss.
- Keep `text` and `raw_text` in sync on edits; v1 restricts direct text-editing
  of `dual_*` chunks (the dual-dialogue preprocessor parses `raw_text` layout).
- New speakers flow into the existing voice-casting "needs casting" path.

### M5 — Guardrails

- GUI re-parse warnings when user-modified audio exists (and, post-M4, when the
  JSON was hand-edited — detection mechanism TBD, likely a gui_backend sidecar
  parse-snapshot hash; CLI parse behavior untouched initially).
- Reconciliation helper: when a text-processor config change shifts
  `processed_hash` but `original_hash` matches, find orphaned user-modified
  files by prefix and offer to carry them forward.
- Bulk operations (clear cache / regenerate all) surface user-modified counts
  first; orphan report for multi-flavor base names.

## Decision log

- Sentinel = filename suffix (5th `~~` field), two flags: `edit` / `retake`.
- Flags have zero effect on cache-hit behavior; audit table above.
- Authority ladder: `edit` > `retake` > plain — manual work wins anomalies.
- Kind fixed at generation time via explicit enum; opening the edit UI never
  affects status; strict text equality decides `retake` vs `edit`.
- Fix forward only: pre-existing variants/files stay unmarked; untagged commits
  land on the plain name.
- User-modified files are scanned and reported for silence like any other
  clip, but never auto-regenerated.
- Viewer starts on post-preprocessed chunks; raw lens arrives with the PDF work
  using derived (never stored) provenance.
- No persisted chunk IDs; identity = content hash + position, recomputed freely.
- M3 (2026-07-06): shipped the PDF overlay only. Anchoring matches
  post-preprocessed `raw_text` against PDF word boxes directly, so the
  `source_idxs` preprocessor provenance and the raw-chunk lens were deferred —
  the four preprocessors stay untouched. Anchors are backend-computed line
  rects (PDF points, top-left origin), in-memory cached, never persisted.
- Post-M3 review pass (2026-08-13): play affordances unified across lenses —
  the detail panel header hosts play + play-from-here for both lenses (PDF
  overlay clicks remain selection-only); a shell-owned **reading anchor**
  (topmost visible chunk idx, sessionStorage-persisted per project) preserves
  and syncs the scroll position across lens switches; selection is stored by
  chunk idx, not list position, so inventory refreshes can't retarget the
  panel; anchor matcher gained proximity-guarded raw_text reuse and
  desync recovery (`RAW_TEXT_REUSE_WINDOW_WORDS`, `RECOVERY_*` tunables);
  voice-config writes now invalidate the chunk inventory.
- Post-M3 correctness pass (2026-08-23): inventory and PDF-anchor responses
  carry the same cheap hash of the ordered post-preprocessed chunk layout, so
  same-length stale anchor sets are hidden and refreshed instead of addressing
  the wrong current chunks. This is a coherence token rather than a
  transactional lock; if overlapping writes still cause repeated skew, add
  per-project invalidation generations and discard/retry older in-flight
  computations. PDFs with cropped or shifted visible page boxes now keep the
  rendered PDF available but disable overlays with a user-visible warning until
  the coordinate translation can be fixture-tested.
- Pre-commit review pass (2026-08-23): both revision hashes now come from the
  same full preprocessed list (planning may drop chunks that raise), and the
  PDF lens attempts exactly one anchor refresh per distinct revision-pair skew
  before showing a terminal notice. Anchor recovery scans are budgeted
  (`RECOVERY_MAX_FAILED_SCANS`) so a non-matching PDF can't trigger a scan per
  chunk. Anchoring loads only chunks + text processor (no voice config), and
  path-security rejections surface as path-free not-found errors. Panel
  selection is strictly user-driven: sequential playback never retargets the
  detail panel (it's keyed by idx; retargeting would discard editor state).
  Voice mutations invalidate only the session's project inventory.

## Known gotchas

- `original_hash` is computed post-preprocessing, so preprocessor config changes
  re-key the cache mapping (already true today; inventory invalidation is tied
  to the text-processor config).
- Re-recording a chunk whose audio is shared by N chunks changes all N — hence
  the prominent occurrence badge. Changing one occurrence requires a chunk-text
  edit (M4).
- Edited generation text was historically unrecoverable; the ID3 stamp fixes
  this going forward only.
- GUI+CLI concurrency: recompute-on-demand + refresh affordances; only M4's
  JSON writes need real locking (existing 409 pattern).
- PDF anchoring is heuristic (unidecode, header removal); mitigated by
  monotonic alignment, hide-if-unanchored, and the sequential-view fallback.
