"""Shared revision and invalidation for derived screenplay analysis.

Chunk inventories and PDF anchors are both rebuilt from the chunk JSON and
text-processor configuration. Mutations that can reshape either source must
drop both snapshots together so clients never observe mismatched idxs.
"""

import hashlib
import json
from typing import Any, Mapping, Optional, Sequence


def compute_chunk_layout_revision(chunks: Sequence[Mapping[str, Any]]) -> str:
    """Fingerprint the ordered preprocessed chunk layout shared by the views.

    Inventory and PDF-anchor requests run independently. A reparse can retain
    the same chunk count while changing chunk order or content, so count alone
    cannot prove that an anchor idx addresses the inventory entry beside it.
    Hashing this small canonical projection is effectively free compared with
    audio planning or PDF extraction and lets the frontend detect that skew.

    Cache filenames are not sufficient for this purpose: their chunk hashes
    omit ``raw_text`` and chunk type, both of which matter to PDF placement.

    This revision is a coherence/detection token, not a transactional lock. If
    revision mismatches remain common because writes repeatedly overlap an
    in-flight computation, harden the service caches with per-project
    invalidation generations and discard/retry computations from an old
    generation rather than adding more fields to this fingerprint.
    """
    layout = [
        {
            "type": chunk.get("type"),
            "speaker": chunk.get("speaker"),
            "text": chunk.get("text"),
            "raw_text": chunk.get("raw_text"),
        }
        for chunk in chunks
    ]
    canonical = json.dumps(
        layout,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def invalidate_project_analysis(project_name: Optional[str] = None) -> None:
    """Invalidate derived inventory and PDF-anchor snapshots.

    Args:
        project_name: Project to invalidate, or ``None`` for every project.
    """
    # Local imports keep the cache singletons independent and avoid import
    # cycles with services that invoke this helper after a write.
    from .chunk_inventory_service import chunk_inventory_service
    from .pdf_anchor_service import pdf_anchor_service

    chunk_inventory_service.invalidate(project_name)
    pdf_anchor_service.invalidate(project_name)
