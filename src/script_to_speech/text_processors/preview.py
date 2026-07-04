"""Preview engine for text processor pipelines.

Runs a pipeline over parsed screenplay chunks the same way audio generation
does, but stepwise: preprocessors stage-by-stage and processors chunk-by-chunk,
capturing which processor changed which chunk (with before/after snapshots).
Used by the GUI to show what a config -- saved or draft -- would actually do
to a screenplay before generating audio.

Preprocessors can merge, split, add, and remove chunks, so per-chunk change
attribution across them is ill-posed; they get stage-level counts (and,
optionally, full before/after snapshots). Processors transform chunks
one-by-one and get exact per-chunk, per-processor attribution.
"""

import copy
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .processor_manager import TextProcessorManager


def _run_preprocessor_stages(
    chunks: List[Dict],
    manager: TextProcessorManager,
    include_snapshots: bool = False,
) -> Tuple[List[Dict], List[Dict[str, Any]]]:
    """Run all preprocessors and return (working chunks, stage summaries).

    Preprocessors are whole-list transforms, reported stage-by-stage. The
    input chunk list is not mutated. When include_snapshots is set each stage
    also carries full before/after chunk lists.
    """
    working = copy.deepcopy(chunks)
    stages: List[Dict[str, Any]] = []
    for preprocessor in manager.preprocessors:
        before_count = len(working)
        before_snapshot = copy.deepcopy(working) if include_snapshots else None

        working, modified = preprocessor.process(working)

        stage: Dict[str, Any] = {
            "name": preprocessor.sts_config_name,
            "modified": bool(modified),
            "before_count": before_count,
            "after_count": len(working),
        }
        if include_snapshots:
            stage["before"] = before_snapshot
            stage["after"] = copy.deepcopy(working)
        stages.append(stage)
    return working, stages


def _run_final(
    chunks: List[Dict], manager: TextProcessorManager
) -> Tuple[List[Dict], List[Dict[str, Any]]]:
    """Run a full pipeline and return (final chunks, preprocessor stage summaries).

    The input chunk list is not mutated.
    """
    working, stages = _run_preprocessor_stages(chunks, manager)

    finals: List[Dict] = []
    for chunk in working:
        current = dict(chunk)
        for processor in manager.processors:
            current, _ = processor.process(current)
        finals.append(current)
    return finals, stages


def run_preview(
    chunks: List[Dict],
    config_paths: Optional[List[Path]] = None,
    config_dicts: Optional[List[Dict]] = None,
    include_preprocessor_snapshots: bool = False,
    max_changed_chunks: Optional[int] = None,
) -> Dict[str, Any]:
    """Run a text processor pipeline stepwise and report its effects.

    Args:
        chunks: Parsed screenplay chunks (not mutated)
        config_paths: Config files to load (mutually exclusive with config_dicts)
        config_dicts: Already-parsed config dicts, e.g. an unsaved GUI draft
        include_preprocessor_snapshots: Include full before/after chunk lists
            per preprocessor stage (larger payload)
        max_changed_chunks: Cap on returned changed chunks (None = unbounded);
            changed_chunk_count always reflects the full count

    Returns:
        Dict with input/final chunk counts, per-preprocessor stage summaries,
        and the changed chunks with per-processor attribution steps:
        {
            "input_chunk_count": int,
            "final_chunk_count": int,
            "preprocessor_stages": [
                {"name", "modified", "before_count", "after_count",
                 "before"?, "after"?},
            ],
            "changed_chunks": [
                {"index", "chunk_type", "speaker", "before", "after",
                 "steps": [{"name", "before", "after"}]},
            ],
            "changed_chunk_count": int,
            "truncated": bool,
        }

    Raises:
        ValueError: If not exactly one of config_paths / config_dicts is given,
            or if the configs fail to load/validate
    """
    if (config_paths is None) == (config_dicts is None):
        raise ValueError("Provide exactly one of config_paths or config_dicts")

    if config_paths is not None:
        manager = TextProcessorManager(config_paths)
    else:
        manager = TextProcessorManager.from_dicts(config_dicts or [])

    input_chunk_count = len(chunks)

    # Preprocessors: whole-list transforms, reported stage-by-stage
    working, preprocessor_stages = _run_preprocessor_stages(
        chunks, manager, include_snapshots=include_preprocessor_snapshots
    )

    # Processors: per-chunk transforms with per-processor attribution.
    # Changes are detected by comparing chunk contents (not the returned
    # bool) so attribution can't drift from what actually changed.
    changed_chunks: List[Dict[str, Any]] = []
    for index, chunk in enumerate(working):
        original = dict(chunk)
        current = dict(chunk)
        steps: List[Dict[str, Any]] = []

        for processor in manager.processors:
            before = dict(current)
            current, _ = processor.process(current)
            if current != before:
                steps.append(
                    {
                        "name": processor.sts_config_name,
                        "before": before,
                        "after": dict(current),
                    }
                )

        if current != original:
            changed_chunks.append(
                {
                    "index": index,
                    "chunk_type": original.get("type", ""),
                    "speaker": original.get("speaker", ""),
                    "before": original,
                    "after": dict(current),
                    "steps": steps,
                }
            )

    changed_chunk_count = len(changed_chunks)
    truncated = (
        max_changed_chunks is not None and changed_chunk_count > max_changed_chunks
    )
    if truncated:
        changed_chunks = changed_chunks[:max_changed_chunks]

    return {
        "input_chunk_count": input_chunk_count,
        "final_chunk_count": len(working),
        "preprocessor_stages": preprocessor_stages,
        "changed_chunks": changed_chunks,
        "changed_chunk_count": changed_chunk_count,
        "truncated": truncated,
    }


def run_preview_diff(
    chunks: List[Dict],
    draft_config_dicts: List[Dict],
    baseline_config_paths: Optional[List[Path]] = None,
    baseline_config_dicts: Optional[List[Dict]] = None,
    max_changed_chunks: int = 50,
) -> Dict[str, Any]:
    """Diff the final output of two pipelines over the same chunks.

    Answers "what would my unsaved changes add on top of the saved config":
    both pipelines run to completion and only chunks whose final output
    differs between the runs are reported.

    When the two runs produce different chunk counts (a preprocessor change
    altered merges/splits), per-index chunk pairing is ill-posed; the result
    then carries alignment="counts_differ" with no chunk list, and the two
    runs' stage summaries tell the story at the stage level.

    Args:
        chunks: Parsed screenplay chunks (not mutated)
        draft_config_dicts: The draft pipeline (e.g. buffer with dirty changes)
        baseline_config_paths: Baseline configs as files (mutually exclusive
            with baseline_config_dicts)
        baseline_config_dicts: Baseline pipeline as parsed dicts
        max_changed_chunks: Cap on returned changed chunks;
            changed_chunk_count always reflects the full count

    Returns:
        {
            "alignment": "index" | "counts_differ",
            "input_chunk_count": int,
            "baseline_final_count": int,
            "draft_final_count": int,
            "baseline_stages": [{"name", "modified", "before_count", "after_count"}],
            "draft_stages": [...],
            "changed_chunks": [{"index", "chunk_type", "speaker", "before", "after"}],
            "changed_chunk_count": int,
            "truncated": bool,
        }

    Raises:
        ValueError: If not exactly one baseline source is given, or if the
            configs fail to load/validate
    """
    if (baseline_config_paths is None) == (baseline_config_dicts is None):
        raise ValueError(
            "Provide exactly one of baseline_config_paths or baseline_config_dicts"
        )

    if baseline_config_paths is not None:
        baseline_manager = TextProcessorManager(baseline_config_paths)
    else:
        baseline_manager = TextProcessorManager.from_dicts(baseline_config_dicts or [])
    draft_manager = TextProcessorManager.from_dicts(draft_config_dicts)

    baseline_final, baseline_stages = _run_final(chunks, baseline_manager)
    draft_final, draft_stages = _run_final(chunks, draft_manager)

    result: Dict[str, Any] = {
        "input_chunk_count": len(chunks),
        "baseline_final_count": len(baseline_final),
        "draft_final_count": len(draft_final),
        "baseline_stages": baseline_stages,
        "draft_stages": draft_stages,
    }

    if len(baseline_final) != len(draft_final):
        result.update(
            {
                "alignment": "counts_differ",
                "changed_chunks": [],
                "changed_chunk_count": 0,
                "truncated": False,
            }
        )
        return result

    changed_chunks: List[Dict[str, Any]] = []
    changed_chunk_count = 0
    for index, (before, after) in enumerate(zip(baseline_final, draft_final)):
        if before != after:
            changed_chunk_count += 1
            if len(changed_chunks) < max_changed_chunks:
                changed_chunks.append(
                    {
                        "index": index,
                        "chunk_type": before.get("type", ""),
                        "speaker": before.get("speaker", ""),
                        "before": before,
                        "after": after,
                    }
                )

    result.update(
        {
            "alignment": "index",
            "changed_chunks": changed_chunks,
            "changed_chunk_count": changed_chunk_count,
            "truncated": changed_chunk_count > len(changed_chunks),
        }
    )
    return result
