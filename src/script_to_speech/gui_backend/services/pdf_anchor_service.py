"""Service for anchoring screenplay chunks onto the rendered PDF.

The overlay view draws each post-preprocessed chunk on top of the source PDF.
This service computes, at view time, where each chunk sits: it re-opens the
PDF, extracts per-page word boxes with the *same* pdfplumber settings the
parser used, and walks each chunk's ``raw_text`` against the word stream to
produce per-line bounding boxes.

Nothing is persisted. Results are cached in memory per project and cleared
when the underlying text moves on the page -- i.e. on re-parse and on
text-processor config changes. Audio mutations (variant commits, audiobook
runs) never move a chunk on the page, so they do NOT invalidate anchors.

Chunk idx alignment with the chunk inventory is by construction: both call
``processor.preprocess_chunks(dialogues)`` (the same list ``plan_audio_generation``
enumerates), so ``ChunkAnchor.idx`` and ``ChunkInventoryEntry.idx`` refer to
the same chunk.
"""

import logging
import threading
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from unidecode import unidecode

from script_to_speech.parser.utils.text_utils import (
    PageWords,
    extract_words_by_page,
)
from script_to_speech.utils.file_system_utils import PathSecurityValidator

from ..config import settings
from ..models import AnchorRect, ChunkAnchor, ChunkAnchorsResponse, PdfPageInfo
from .project_analysis_cache import compute_chunk_layout_revision
from .project_loader import load_project_text_context

logger = logging.getLogger(__name__)


# --- Matching tunables -------------------------------------------------------
# Window scanned past the cursor for a chunk's first token.
MAX_START_SKIP_WORDS = 80
# First-token candidate positions tried before giving up on a fresh match.
MAX_START_CANDIDATES = 5
# Words skippable mid-chunk (interleaved headers/footers/page numbers, dropped
# merge chunks, page-break furniture) while still counting as a match.
MAX_GAP_WORDS = 15
# Matched-token fraction required to accept an anchor.
MIN_MATCH_RATIO = 0.8
# Below this token count a chunk must match *every* token (guards one/two-word
# chunks -- page numbers, "YES." -- from anchoring to a coincidental word).
SMALL_CHUNK_TOKENS = 3
# Words whose `top` differs by more than this share no line rect (PDF points).
LINE_CLUSTER_TOLERANCE = 3.0
# Recent fresh matches kept so shared-raw_text chunks (parenthetical splits,
# dual-dialogue synthesized chunks) reuse the same region.
RAW_TEXT_MATCH_CACHE_SIZE = 8
# A cached shared-raw_text region may only be reused while the cursor is still
# near it: splits and dual dialogue are near-adjacent. Without this guard a
# repeated short line ("(beat)", "CONTINUED:") that fails its fresh match would
# silently anchor onto an unrelated earlier page.
RAW_TEXT_REUSE_WINDOW_WORDS = 200
# Consecutive fresh-match failures tolerated before assuming the cursor has
# desynced (e.g. an un-chunked stretch of front matter longer than
# MAX_START_SKIP_WORDS, which would otherwise strand every later chunk).
RECOVERY_FAILURE_STREAK = 3
# Recovery searches the whole remaining stream, so only chunks long enough to
# be positionally unambiguous may re-sync the cursor.
RECOVERY_MIN_TOKENS = 4
RECOVERY_MAX_CANDIDATES = 50
# Failed whole-stream recovery scans allowed per document. Recovery exists for
# occasional desyncs (e.g. a long un-chunked stretch); when the PDF simply
# doesn't correspond to the chunks at all, every remaining chunk would
# otherwise trigger an O(words) rescan. Successful recoveries don't count
# against the budget.
RECOVERY_MAX_FAILED_SCANS = 10


@dataclass
class _StreamWord:
    """A page word with its normalized text, in the flat matching stream."""

    page: int
    x0: float
    x1: float
    top: float
    bottom: float
    norm: str


@dataclass
class _CachedMatch:
    """A prior fresh match kept for shared-raw_text reuse."""

    words: List[_StreamWord]
    ratio: float
    # Stream index of the match's last word; reuse is only allowed while the
    # cursor remains within RAW_TEXT_REUSE_WINDOW_WORDS of it.
    end_index: int


def _normalize_word(text: str) -> str:
    """Normalize a word/token for comparison.

    Collapses any whitespace unidecode might introduce and lowercases, so the
    two extraction paths (layout text -> raw_text, and word boxes) compare
    equal despite incidental case/spacing differences.
    """
    return "".join(unidecode(text).split()).lower()


def _tokenize(raw_text: str) -> List[str]:
    """Split a chunk's raw_text into normalized, non-empty tokens."""
    tokens = []
    for piece in unidecode(raw_text).split():
        norm = _normalize_word(piece)
        if norm:
            tokens.append(norm)
    return tokens


def _build_word_stream(pages: List[PageWords]) -> List[_StreamWord]:
    """Flatten all pages' words into one page-ordered stream (empties dropped)."""
    stream: List[_StreamWord] = []
    for page in pages:
        for word in page.words:
            norm = _normalize_word(word.text)
            if not norm:
                continue
            stream.append(
                _StreamWord(
                    page=page.page_number,
                    x0=word.x0,
                    x1=word.x1,
                    top=word.top,
                    bottom=word.bottom,
                    norm=norm,
                )
            )
    return stream


def _align_from(
    stream: List[_StreamWord], start: int, tokens: List[str]
) -> Optional[Tuple[List[int], int]]:
    """Greedily align `tokens` to the word stream starting at `start`.

    On a token mismatch, scans ahead up to ``MAX_GAP_WORDS`` for the token
    (skipping interleaved words); if not found, skips the token. The caller
    guarantees ``stream[start].norm == tokens[0]``.

    Returns (matched_stream_indices, last_matched_index) or None if nothing
    matched.
    """
    n = len(stream)
    matched_indices: List[int] = []
    j = start
    for token in tokens:
        if j < n and stream[j].norm == token:
            matched_indices.append(j)
            j += 1
            continue
        found = None
        scan_limit = min(n, j + 1 + MAX_GAP_WORDS)
        for jj in range(j + 1, scan_limit):
            if stream[jj].norm == token:
                found = jj
                break
        if found is not None:
            matched_indices.append(found)
            j = found + 1
        # else: token has no word (hyphenation/ligature drift) -- skip it,
        # leaving the cursor put so the next token can still match here.
    if not matched_indices:
        return None
    return matched_indices, matched_indices[-1]


def _fresh_match(
    stream: List[_StreamWord],
    cursor: int,
    tokens: List[str],
    max_skip: int = MAX_START_SKIP_WORDS,
    max_candidates: int = MAX_START_CANDIDATES,
) -> Optional[Tuple[List[_StreamWord], int, float]]:
    """Attempt a fresh match for `tokens` at or after `cursor`.

    Returns (matched_words, last_matched_index, ratio) on success, else None.
    Never mutates the cursor; the caller advances it on acceptance.
    """
    n = len(stream)
    required = MIN_MATCH_RATIO if len(tokens) >= SMALL_CHUNK_TOKENS else 1.0
    limit = min(n, cursor + max_skip)
    candidates_tried = 0
    p = cursor
    while p < limit and candidates_tried < max_candidates:
        if stream[p].norm == tokens[0]:
            candidates_tried += 1
            aligned = _align_from(stream, p, tokens)
            if aligned is not None:
                matched_indices, last_index = aligned
                ratio = len(matched_indices) / len(tokens)
                if ratio >= required:
                    matched_words = [stream[k] for k in matched_indices]
                    return matched_words, last_index, ratio
        p += 1
    return None


def _line_rect(page: int, line: List[_StreamWord]) -> AnchorRect:
    """Bounding box enclosing all words clustered onto one line."""
    return AnchorRect(
        page=page,
        x0=min(w.x0 for w in line),
        top=min(w.top for w in line),
        x1=max(w.x1 for w in line),
        bottom=max(w.bottom for w in line),
    )


def _build_rects(words: List[_StreamWord]) -> List[AnchorRect]:
    """Group matched words into per-line rects (by page, then by `top`)."""
    by_page: "OrderedDict[int, List[_StreamWord]]" = OrderedDict()
    for word in words:
        by_page.setdefault(word.page, []).append(word)

    rects: List[AnchorRect] = []
    for page, page_words in by_page.items():
        line: List[_StreamWord] = []
        line_top: Optional[float] = None
        for word in sorted(page_words, key=lambda w: w.top):
            if line_top is None or abs(word.top - line_top) <= LINE_CLUSTER_TOLERANCE:
                if line_top is None:
                    line_top = word.top
                line.append(word)
            else:
                rects.append(_line_rect(page, line))
                line = [word]
                line_top = word.top
        if line:
            rects.append(_line_rect(page, line))
    return rects


def match_chunks_to_words(
    chunks: List[Dict], pages: List[PageWords]
) -> Tuple[List[ChunkAnchor], List[int]]:
    """Anchor each chunk's raw_text onto the PDF word stream.

    A single monotonic cursor walks the page-ordered word stream as chunks are
    processed in idx order. Each chunk first tries a fresh match from the
    cursor; on success the cursor advances past the match and the region is
    cached by exact raw_text. On failure the cursor never moves, and the chunk
    falls back to the recent-match cache (so parenthetical splits and
    dual-dialogue chunks that share one raw_text reuse the same region) --
    only while the cursor is still near the cached region; otherwise it is
    left unanchored. After several consecutive failures a sufficiently long
    chunk may re-sync the cursor by searching the whole remaining stream;
    ``RECOVERY_MAX_FAILED_SCANS`` bounds how many such scans may fail per
    document before recovery stops being attempted.

    Chunks with no tokens (empty raw_text, e.g. expected-silence chunks) have
    nothing to place: they are skipped entirely and NOT reported in
    ``unanchored_idxs``, which counts only real anchoring misses.

    Returns (anchors, unanchored_idxs).
    """
    stream = _build_word_stream(pages)
    anchors: List[ChunkAnchor] = []
    unanchored_idxs: List[int] = []
    cursor = 0
    fail_streak = 0
    failed_recovery_scans = 0
    recent: "OrderedDict[str, _CachedMatch]" = OrderedDict()

    for idx, chunk in enumerate(chunks):
        raw_text = chunk.get("raw_text", "") or ""
        tokens = _tokenize(raw_text)
        if not tokens:
            continue

        fresh = _fresh_match(stream, cursor, tokens)
        if (
            fresh is None
            and fail_streak >= RECOVERY_FAILURE_STREAK
            and len(tokens) >= RECOVERY_MIN_TOKENS
            and failed_recovery_scans < RECOVERY_MAX_FAILED_SCANS
        ):
            fresh = _fresh_match(
                stream,
                cursor,
                tokens,
                max_skip=len(stream),
                max_candidates=RECOVERY_MAX_CANDIDATES,
            )
            if fresh is None:
                failed_recovery_scans += 1
        if fresh is not None:
            matched_words, last_index, ratio = fresh
            cursor = last_index + 1
            fail_streak = 0
            anchors.append(
                ChunkAnchor(
                    idx=idx, rects=_build_rects(matched_words), match_ratio=ratio
                )
            )
            recent[raw_text] = _CachedMatch(
                words=matched_words, ratio=ratio, end_index=last_index
            )
            recent.move_to_end(raw_text)
            while len(recent) > RAW_TEXT_MATCH_CACHE_SIZE:
                recent.popitem(last=False)
            continue

        cached = recent.get(raw_text)
        if (
            cached is not None
            and cursor - cached.end_index <= RAW_TEXT_REUSE_WINDOW_WORDS
        ):
            recent.move_to_end(raw_text)
            anchors.append(
                ChunkAnchor(
                    idx=idx,
                    rects=_build_rects(cached.words),
                    match_ratio=cached.ratio,
                )
            )
            continue

        unanchored_idxs.append(idx)
        fail_streak += 1

    return anchors, unanchored_idxs


def resolve_project_pdf_path(project_name: str) -> Path:
    """Resolve and security-validate a project's source PDF path.

    Only ``input/{project}/{project}.pdf`` counts: parsing always copies the
    source PDF into the project directory, and the UI's PDF-lens gate
    (``ProjectStatus.has_pdf``) checks exactly this location — the resolver
    must agree with the gate.

    Raises:
        FileNotFoundError: If no PDF exists for the project, or the resolved
            path fails security validation (reported identically so hostile
            names learn nothing and no filesystem path reaches the client).
    """
    validator = PathSecurityValidator(settings.WORKSPACE_DIR)

    project_pdf = (
        settings.WORKSPACE_DIR / "input" / project_name / f"{project_name}.pdf"
    )
    if project_pdf.exists():
        try:
            return validator.validate_existing_path(project_pdf)
        except ValueError:
            raise FileNotFoundError(f"No source PDF found for project: {project_name}")

    raise FileNotFoundError(f"No source PDF found for project: {project_name}")


class PdfAnchorService:
    """Computes and caches per-project chunk-to-PDF anchors."""

    def __init__(self) -> None:
        self._cache: Dict[str, ChunkAnchorsResponse] = {}
        self._lock = threading.Lock()
        # Per-project compute locks: extraction takes seconds, so concurrent
        # cold requests should wait for one computation, not duplicate it
        self._compute_locks: Dict[str, threading.Lock] = {}

    def get_anchors(
        self, project_name: str, refresh: bool = False
    ) -> ChunkAnchorsResponse:
        """Get chunk-to-PDF anchors for a project.

        Args:
            project_name: Name of the project
            refresh: When True, bypass the in-memory cache and recompute

        Returns:
            ChunkAnchorsResponse for the project

        Raises:
            FileNotFoundError: If the project or its PDF does not exist
        """
        if not refresh:
            with self._lock:
                cached = self._cache.get(project_name)
            if cached is not None:
                logger.info(f"Returning cached PDF anchors for '{project_name}'")
                return cached

        with self._lock:
            compute_lock = self._compute_locks.setdefault(
                project_name, threading.Lock()
            )
        with compute_lock:
            if not refresh:
                # A concurrent request may have computed while we waited
                with self._lock:
                    cached = self._cache.get(project_name)
                if cached is not None:
                    return cached
            anchors = self._compute_anchors(project_name)
            with self._lock:
                self._cache[project_name] = anchors
            return anchors

    def invalidate(self, project_name: Optional[str] = None) -> None:
        """Drop cached anchors so the next request recomputes from disk.

        Args:
            project_name: Project to invalidate, or None for all projects
        """
        with self._lock:
            if project_name is None:
                self._cache.clear()
            else:
                self._cache.pop(project_name, None)
        logger.info(f"Invalidated PDF anchor cache for: {project_name or 'all'}")

    def _compute_anchors(self, project_name: str) -> ChunkAnchorsResponse:
        """Compute anchors by matching preprocessed chunks against the PDF."""
        logger.info(f"Computing PDF anchors for project: {project_name}")

        # Anchoring never plans audio, so only the chunks and text processor
        # are loaded -- no voice config required.
        dialogues, processor = load_project_text_context(project_name)
        chunks = processor.preprocess_chunks(dialogues)
        chunk_layout_revision = compute_chunk_layout_revision(chunks)

        pdf_path = resolve_project_pdf_path(project_name)
        pages = extract_words_by_page(str(pdf_path))

        anchors, unanchored_idxs = match_chunks_to_words(chunks, pages)

        page_infos = [
            PdfPageInfo(page=page.page_number, width=page.width, height=page.height)
            for page in pages
        ]

        logger.info(
            f"PDF anchors for '{project_name}': {len(chunks)} chunks, "
            f"{len(anchors)} anchored, {len(unanchored_idxs)} unanchored, "
            f"{len(pages)} pages"
        )

        return ChunkAnchorsResponse(
            project_name=project_name,
            pages=page_infos,
            anchors=anchors,
            unanchored_idxs=unanchored_idxs,
            total_chunks=len(chunks),
            anchored_count=len(anchors),
            chunk_layout_revision=chunk_layout_revision,
            unsupported_geometry_pages=[
                page.page_number
                for page in pages
                if not page.overlay_geometry_supported
            ],
            generated_at=datetime.now(timezone.utc).isoformat(),
        )


# Singleton instance
pdf_anchor_service = PdfAnchorService()
