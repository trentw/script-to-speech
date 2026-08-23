"""Tests for the PDF anchor service.

Covers the pure chunk->word matcher (exact matches, header/footer skips,
page-break spanning, confidence thresholds, shared-raw_text reuse for
parenthetical splits and dual dialogue, line clustering) and the
cache/invalidate lifecycle. PDF extraction and project loading are mocked.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from script_to_speech.gui_backend.services.pdf_anchor_service import (
    PdfAnchorService,
    match_chunks_to_words,
    resolve_project_pdf_path,
)
from script_to_speech.parser.utils.text_utils import PageWord, PageWords

# --- Builders ---------------------------------------------------------------


def word(text: str, x0: float, top: float) -> PageWord:
    """A page word with width proportional to its text and a 10pt line height."""
    return PageWord(text=text, x0=x0, x1=x0 + 6 * len(text), top=top, bottom=top + 10)


def line(texts, top: float, x_start: float = 100.0, gap: float = 8.0):
    """Lay out `texts` left-to-right on one line at `top`."""
    words = []
    x = x_start
    for t in texts:
        w = word(t, x, top)
        words.append(w)
        x = w.x1 + gap
    return words


def make_page(words, page_number: int = 0, width: float = 612.0, height: float = 792.0):
    return PageWords(page_number=page_number, width=width, height=height, words=words)


def chunk(raw_text: str, chunk_type: str = "action"):
    return {"type": chunk_type, "speaker": "", "text": raw_text, "raw_text": raw_text}


# --- Pure matcher tests -----------------------------------------------------


class TestMatchChunksToWords:
    def test_exact_single_line_match(self):
        pages = [make_page(line(["INT.", "HOUSE", "-", "DAY"], top=72))]
        anchors, unanchored = match_chunks_to_words(
            [chunk("INT. HOUSE - DAY", "scene_heading")], pages
        )
        assert unanchored == []
        assert len(anchors) == 1
        assert anchors[0].idx == 0
        assert anchors[0].match_ratio == 1.0
        assert len(anchors[0].rects) == 1
        rect = anchors[0].rects[0]
        assert rect.page == 0
        assert rect.x0 == 100.0
        assert rect.top == 72.0

    def test_multi_line_chunk_produces_one_rect_per_line(self):
        words = line(["The", "quick", "brown"], top=72) + line(
            ["fox", "jumps", "over"], top=84
        )
        pages = [make_page(words)]
        anchors, unanchored = match_chunks_to_words(
            [chunk("The quick brown\nfox jumps over")], pages
        )
        assert unanchored == []
        assert len(anchors[0].rects) == 2
        assert {r.top for r in anchors[0].rects} == {72.0, 84.0}

    def test_skips_interleaved_header_footer_words(self):
        # A stray page-number word sits between the chunk's words
        words = [
            word("Alpha", 100, 72),
            word("99", 500, 40),  # header/page number, not in raw_text
            word("Beta", 160, 72),
            word("Gamma", 220, 72),
        ]
        pages = [make_page(words)]
        anchors, unanchored = match_chunks_to_words([chunk("Alpha Beta Gamma")], pages)
        assert unanchored == []
        assert anchors[0].match_ratio == 1.0

    def test_chunk_spanning_page_break_gets_rects_on_both_pages(self):
        page0 = make_page(line(["alpha", "beta"], top=700), page_number=0)
        page1 = make_page(line(["gamma", "delta"], top=72), page_number=1)
        anchors, unanchored = match_chunks_to_words(
            [chunk("alpha beta gamma delta")], [page0, page1]
        )
        assert unanchored == []
        rects = anchors[0].rects
        assert {r.page for r in rects} == {0, 1}

    def test_low_ratio_chunk_unanchored_and_cursor_not_advanced(self):
        # Chunk 0 only partially matches (2 of its 4 tokens are absent), so it
        # must be unanchored AND must not consume the words chunk 1 needs.
        pages = [make_page(line(["real", "words", "here", "now"], top=72))]
        chunks = [
            chunk("missing absent real words"),  # 2/4 present -> below 0.8
            chunk("real words here now"),  # fully present
        ]
        anchors, unanchored = match_chunks_to_words(chunks, pages)
        assert unanchored == [0]
        assert len(anchors) == 1
        assert anchors[0].idx == 1
        assert anchors[0].match_ratio == 1.0

    def test_parenthetical_split_reuses_same_region(self):
        # Two consecutive chunks share one raw_text (the parenthetical-split
        # pattern): first fresh-matches, second reuses the same rects.
        pages = [make_page(line(["hello", "there", "friend"], top=72))]
        shared = "hello there friend"
        anchors, unanchored = match_chunks_to_words(
            [chunk(shared), chunk(shared)], pages
        )
        assert unanchored == []
        assert len(anchors) == 2
        assert anchors[0].rects[0].top == anchors[1].rects[0].top
        assert anchors[0].rects[0].x0 == anchors[1].rects[0].x0

    def test_distinct_identical_chunks_match_distinct_regions(self):
        # Genuinely repeated text (not a split) fresh-matches each occurrence
        # in order rather than collapsing onto the first.
        words = line(["beat"], top=72) + line(["beat"], top=200)
        pages = [make_page(words)]
        anchors, _ = match_chunks_to_words([chunk("beat"), chunk("beat")], pages)
        assert len(anchors) == 2
        assert anchors[0].rects[0].top == 72.0
        assert anchors[1].rects[0].top == 200.0

    def test_dual_dialogue_style_shared_raw_texts(self):
        # Two raw_text values reused across several synthesized chunks: a
        # speaker line and a two-column dialogue block.
        speaker_line = line(["JOHN", "MARY"], top=72)
        block = line(["left1", "right1"], top=84) + line(["left2", "right2"], top=96)
        pages = [make_page(speaker_line + block)]

        speaker_raw = "JOHN                    MARY"
        dialogue_raw = "left1        right1\nleft2        right2"
        chunks = [
            chunk(speaker_raw, "speaker_attribution"),  # left speaker
            chunk(dialogue_raw, "dialogue"),  # left column dialogue
            chunk(speaker_raw, "speaker_attribution"),  # right speaker (reuse)
            chunk(dialogue_raw, "dialogue"),  # right column dialogue (reuse)
        ]
        anchors, unanchored = match_chunks_to_words(chunks, pages)
        assert unanchored == []
        assert len(anchors) == 4
        # speaker chunks share the speaker-line region; dialogue chunks share
        # the two-line block region
        assert anchors[0].rects[0].top == anchors[2].rects[0].top == 72.0
        assert {r.top for r in anchors[1].rects} == {84.0, 96.0}
        assert {r.top for r in anchors[3].rects} == {84.0, 96.0}

    def test_small_chunk_requires_exact_match(self):
        # A 2-token chunk with only 1 token present is below the exact bar
        pages = [make_page(line(["yes"], top=72))]
        anchors, unanchored = match_chunks_to_words([chunk("yes indeed")], pages)
        assert unanchored == [0]
        assert anchors == []

    def test_small_chunk_single_token_anchors(self):
        pages = [make_page(line(["yes"], top=72))]
        anchors, unanchored = match_chunks_to_words([chunk("YES")], pages)
        assert unanchored == []
        assert anchors[0].match_ratio == 1.0

    def test_line_clustering_tolerance(self):
        # Words whose tops differ within tolerance share a line; beyond it split
        words = [
            word("a", 100, 72.0),
            word("b", 130, 74.0),  # within 3pt of 72 -> same line
            word("c", 160, 90.0),  # beyond tolerance -> new line
        ]
        pages = [make_page(words)]
        anchors, _ = match_chunks_to_words([chunk("a b c")], pages)
        rects = anchors[0].rects
        assert len(rects) == 2

    def test_empty_raw_text_is_skipped_not_reported(self):
        # Empty chunks (expected-silence) have nothing to place: they are not
        # anchoring failures, so they must not inflate the "not shown" count
        pages = [make_page(line(["hello"], top=72))]
        anchors, unanchored = match_chunks_to_words(
            [chunk(""), chunk("   \n  ")], pages
        )
        assert unanchored == []
        assert anchors == []

    def test_counts_partition_nonempty_indices(self):
        pages = [make_page(line(["present", "words"], top=72))]
        chunks = [
            chunk("present words"),
            chunk("totally different absent text here"),
            chunk(""),  # skipped: neither anchored nor unanchored
        ]
        anchors, unanchored = match_chunks_to_words(chunks, pages)
        anchored_idxs = [a.idx for a in anchors]
        assert sorted(anchored_idxs + unanchored) == [0, 1]
        assert set(anchored_idxs).isdisjoint(unanchored)

    def test_cache_reuse_requires_proximity(self):
        # A repeated short line far behind the cursor must NOT be reused: that
        # would draw the chunk on an unrelated earlier page. Layout: "beat" on
        # page 0, then ~300 words of content, then a chunk whose raw_text
        # repeats "beat" but has no remaining occurrence in the stream.
        filler_words = [f"w{i}" for i in range(300)]
        words = line(["beat"], top=72)
        for row in range(30):
            words += line(filler_words[row * 10 : (row + 1) * 10], top=100 + row * 12)
        pages = [make_page(words)]

        chunks = [chunk("beat")]
        chunks += [
            chunk(" ".join(filler_words[row * 10 : (row + 1) * 10]))
            for row in range(30)
        ]
        chunks.append(chunk("beat"))  # far from the cached region

        anchors, unanchored = match_chunks_to_words(chunks, pages)
        assert unanchored == [31]
        # ...and the near-adjacent reuse (splits/dual dialogue) still works:
        # covered by test_parenthetical_split_reuses_same_region above.

    def test_recovers_after_long_unmatched_gap(self):
        # An un-chunked stretch longer than the fresh-match window (e.g. a
        # title/front-matter page) must not strand every later chunk: after a
        # few failures, a long chunk re-syncs the cursor via a full search.
        front_matter = [f"fm{i}" for i in range(120)]
        words = []
        for row in range(12):
            words += line(front_matter[row * 10 : (row + 1) * 10], top=40 + row * 12)
        words += line(["alpha", "beta"], top=300)
        words += line(["gamma", "delta"], top=312)
        words += line(["epsilon", "zeta"], top=324)
        words += line(["one", "two", "three", "four", "five"], top=336)
        words += line(["ending", "words", "here", "now"], top=348)
        pages = [make_page(words)]

        chunks = [
            chunk("alpha beta"),  # beyond the 80-word window -> fails
            chunk("gamma delta"),  # fails
            chunk("epsilon zeta"),  # fails (streak reaches 3)
            chunk("one two three four five"),  # long enough -> recovery re-sync
            chunk("ending words here now"),  # normal match resumes
        ]
        anchors, unanchored = match_chunks_to_words(chunks, pages)
        assert unanchored == [0, 1, 2]
        assert [a.idx for a in anchors] == [3, 4]
        assert anchors[0].rects[0].top == 336.0
        assert anchors[1].rects[0].top == 348.0

    def test_failed_recovery_scans_are_budgeted(self, monkeypatch):
        # A PDF that doesn't correspond to the chunks at all must not trigger
        # a whole-stream recovery scan per chunk: after
        # RECOVERY_MAX_FAILED_SCANS failed scans, recovery stops being tried.
        from script_to_speech.gui_backend.services import pdf_anchor_service as svc

        pages = [make_page(line(["alpha", "beta", "gamma"], top=72))]
        chunks = [
            chunk(f"totally unrelated words number {i} nothing here matches")
            for i in range(30)
        ]

        real_fresh_match = svc._fresh_match
        recovery_scans = 0

        def counting_fresh_match(stream, cursor, tokens, **kwargs):
            nonlocal recovery_scans
            if kwargs.get("max_candidates") == svc.RECOVERY_MAX_CANDIDATES:
                recovery_scans += 1
            return real_fresh_match(stream, cursor, tokens, **kwargs)

        monkeypatch.setattr(svc, "_fresh_match", counting_fresh_match)

        anchors, unanchored = svc.match_chunks_to_words(chunks, pages)

        assert anchors == []
        assert len(unanchored) == len(chunks)
        assert recovery_scans == svc.RECOVERY_MAX_FAILED_SCANS


# --- Service cache/lifecycle tests ------------------------------------------


@pytest.fixture
def mock_context():
    """Patch project loading, PDF resolution, and word extraction."""
    processor = MagicMock()
    processor.preprocess_chunks.return_value = [
        chunk("hello world"),
        chunk("missing text"),
    ]
    pages = [make_page(line(["hello", "world"], top=72))]

    with (
        patch(
            "script_to_speech.gui_backend.services.pdf_anchor_service.load_project_text_context"
        ) as mock_load,
        patch(
            "script_to_speech.gui_backend.services.pdf_anchor_service.resolve_project_pdf_path"
        ) as mock_resolve,
        patch(
            "script_to_speech.gui_backend.services.pdf_anchor_service.extract_words_by_page"
        ) as mock_extract,
    ):
        mock_load.return_value = ([], processor)
        mock_resolve.return_value = Path("/tmp/proj/proj.pdf")
        mock_extract.return_value = pages
        yield mock_load, mock_resolve, mock_extract


class TestPdfAnchorService:
    def test_compute_anchors_shape(self, mock_context):
        service = PdfAnchorService()
        response = service.get_anchors("proj")

        assert response.project_name == "proj"
        assert response.total_chunks == 2
        assert response.anchored_count == 1
        assert len(response.chunk_layout_revision) == 64
        assert response.unsupported_geometry_pages == []
        assert response.unanchored_idxs == [1]
        assert len(response.pages) == 1
        assert response.pages[0].width == 612.0
        assert response.anchors[0].idx == 0

    def test_caches_until_refresh(self, mock_context):
        mock_load, _mock_resolve, mock_extract = mock_context
        service = PdfAnchorService()

        service.get_anchors("proj")
        service.get_anchors("proj")
        assert mock_extract.call_count == 1  # second call served from cache

        service.get_anchors("proj", refresh=True)
        assert mock_extract.call_count == 2

    def test_invalidate_forces_recompute(self, mock_context):
        _mock_load, _mock_resolve, mock_extract = mock_context
        service = PdfAnchorService()

        service.get_anchors("proj")
        service.invalidate("proj")
        service.get_anchors("proj")
        assert mock_extract.call_count == 2

    def test_invalidate_all(self, mock_context):
        service = PdfAnchorService()
        service.get_anchors("proj")
        service.invalidate()  # None -> all projects
        with service._lock:
            assert service._cache == {}

    def test_reports_pages_with_unsupported_crop_geometry(self, mock_context):
        _mock_load, _mock_resolve, mock_extract = mock_context
        mock_extract.return_value = [
            make_page(
                line(["hello", "world"], top=72),
            )
        ]
        mock_extract.return_value[0].overlay_geometry_supported = False

        response = PdfAnchorService().get_anchors("proj")

        assert response.unsupported_geometry_pages == [0]


class TestResolveProjectPdfPath:
    def test_missing_pdf_raises(self, tmp_path):
        with patch(
            "script_to_speech.gui_backend.services.pdf_anchor_service.settings"
        ) as mock_settings:
            mock_settings.WORKSPACE_DIR = tmp_path
            with pytest.raises(FileNotFoundError):
                resolve_project_pdf_path("nope")

    def test_prefers_project_local_pdf(self, tmp_path):
        project_pdf = tmp_path / "input" / "proj" / "proj.pdf"
        project_pdf.parent.mkdir(parents=True)
        project_pdf.write_bytes(b"%PDF-1.4\n")

        with patch(
            "script_to_speech.gui_backend.services.pdf_anchor_service.settings"
        ) as mock_settings:
            mock_settings.WORKSPACE_DIR = tmp_path
            resolved = resolve_project_pdf_path("proj")
        assert resolved == project_pdf.resolve()

    def test_source_screenplays_copy_is_not_served(self, tmp_path):
        # The UI's PDF gate (ProjectStatus.has_pdf) only checks input/, so the
        # resolver must agree: a PDF only in source_screenplays/ is not found
        source_pdf = tmp_path / "source_screenplays" / "proj.pdf"
        source_pdf.parent.mkdir(parents=True)
        source_pdf.write_bytes(b"%PDF-1.4\n")

        with patch(
            "script_to_speech.gui_backend.services.pdf_anchor_service.settings"
        ) as mock_settings:
            mock_settings.WORKSPACE_DIR = tmp_path
            with pytest.raises(FileNotFoundError):
                resolve_project_pdf_path("proj")

    def test_security_rejection_raises_path_free_not_found(self, tmp_path):
        # A path-security rejection must surface exactly like a missing PDF,
        # with no filesystem path in the message (routes relay it to clients)
        project_pdf = tmp_path / "input" / "proj" / "proj.pdf"
        project_pdf.parent.mkdir(parents=True)
        project_pdf.write_bytes(b"%PDF-1.4\n")

        with (
            patch(
                "script_to_speech.gui_backend.services.pdf_anchor_service.settings"
            ) as mock_settings,
            patch(
                "script_to_speech.gui_backend.services.pdf_anchor_service.PathSecurityValidator"
            ) as mock_validator_cls,
        ):
            mock_settings.WORKSPACE_DIR = tmp_path
            mock_validator_cls.return_value.validate_existing_path.side_effect = (
                ValueError(f"Path {project_pdf} is outside the allowed base path")
            )
            with pytest.raises(FileNotFoundError) as exc_info:
                resolve_project_pdf_path("proj")

        assert str(tmp_path) not in str(exc_info.value)
