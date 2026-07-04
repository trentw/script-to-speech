"""Unit tests for text_processors.preview (stepwise pipeline preview)."""

import copy

import pytest

from script_to_speech.text_processors.preview import run_preview, run_preview_diff
from script_to_speech.text_processors.processor_manager import TextProcessorManager

SAMPLE_CHUNKS = [
    {"type": "page_number", "speaker": "", "raw_text": "12", "text": "12"},
    {
        "type": "scene_heading",
        "speaker": "",
        "raw_text": "INT. LAB -- NIGHT",
        "text": "INT. LAB -- NIGHT",
    },
    {
        "type": "dialogue",
        "speaker": "BOB",
        "raw_text": "Hello there.",
        "text": "Hello there.",
    },
]

PIPELINE_CONFIG = {
    "preprocessors": [
        {"name": "skip_and_merge", "config": {"skip_types": ["page_number"]}},
    ],
    "processors": [
        {
            "name": "text_substitution",
            "config": {
                "substitutions": [
                    {"from": "INT.", "to": "INTERIOR", "fields": ["text"]}
                ]
            },
        },
        {
            "name": "capitalization_transform",
            "config": {
                "transformations": [
                    {"chunk_type": "scene_heading", "case": "sentence_case"}
                ]
            },
        },
    ],
}


class TestRunPreview:
    """Tests for the run_preview function."""

    def test_requires_exactly_one_config_source(self):
        """Exactly one of config_paths / config_dicts must be provided."""
        with pytest.raises(ValueError, match="exactly one"):
            run_preview(SAMPLE_CHUNKS)

        with pytest.raises(ValueError, match="exactly one"):
            run_preview(SAMPLE_CHUNKS, config_paths=[], config_dicts=[])

    def test_preprocessor_stages_report_counts(self):
        """Preprocessor stages report per-stage chunk count changes."""
        result = run_preview(SAMPLE_CHUNKS, config_dicts=[PIPELINE_CONFIG])

        assert result["input_chunk_count"] == 3
        assert result["final_chunk_count"] == 2  # page_number removed
        stage = result["preprocessor_stages"][0]
        assert stage["name"] == "skip_and_merge"
        assert stage["modified"] is True
        assert stage["before_count"] == 3
        assert stage["after_count"] == 2
        assert "before" not in stage  # snapshots off by default

    def test_preprocessor_snapshots_included_when_requested(self):
        """Stage snapshots are included when include_preprocessor_snapshots."""
        result = run_preview(
            SAMPLE_CHUNKS,
            config_dicts=[PIPELINE_CONFIG],
            include_preprocessor_snapshots=True,
        )

        stage = result["preprocessor_stages"][0]
        assert len(stage["before"]) == 3
        assert len(stage["after"]) == 2

    def test_changed_chunks_attribute_processors(self):
        """Each changed chunk records which processors changed it, in order."""
        result = run_preview(SAMPLE_CHUNKS, config_dicts=[PIPELINE_CONFIG])

        assert result["changed_chunk_count"] == 1
        changed = result["changed_chunks"][0]
        assert changed["chunk_type"] == "scene_heading"
        assert changed["before"]["text"] == "INT. LAB -- NIGHT"
        assert changed["after"]["text"] == "Interior lab -- night"
        step_names = [s["name"] for s in changed["steps"]]
        assert step_names == ["text_substitution", "capitalization_transform"]
        # Steps chain: each step's after is the next step's before
        assert changed["steps"][0]["after"] == changed["steps"][1]["before"]
        assert changed["steps"][0]["after"]["text"] == "INTERIOR LAB -- NIGHT"

    def test_unchanged_chunks_not_reported(self):
        """Chunks the pipeline doesn't touch are omitted from changed_chunks."""
        result = run_preview(SAMPLE_CHUNKS, config_dicts=[PIPELINE_CONFIG])

        changed_indices = [c["index"] for c in result["changed_chunks"]]
        # The dialogue chunk (index 1 post-preprocessing) is untouched
        assert changed_indices == [0]

    def test_input_chunks_not_mutated(self):
        """run_preview never mutates the caller's chunk list."""
        original = copy.deepcopy(SAMPLE_CHUNKS)

        run_preview(SAMPLE_CHUNKS, config_dicts=[PIPELINE_CONFIG])

        assert SAMPLE_CHUNKS == original

    def test_invalid_config_raises(self):
        """Configs that fail processor validation raise ValueError."""
        bad_config = {"processors": [{"name": "skip_empty", "config": {}}]}

        with pytest.raises(ValueError, match="Invalid configuration"):
            run_preview(SAMPLE_CHUNKS, config_dicts=[bad_config])

    def test_empty_pipeline_reports_no_changes(self):
        """An empty pipeline changes nothing."""
        result = run_preview(SAMPLE_CHUNKS, config_dicts=[{}])

        assert result["changed_chunk_count"] == 0
        assert result["preprocessor_stages"] == []
        assert result["final_chunk_count"] == 3

    def test_max_changed_chunks_caps_list_not_count(self):
        """The cap truncates changed_chunks but reports the full count."""
        chunks = [
            {"type": "dialogue", "speaker": "BOB", "text": f"INT. {i}"}
            for i in range(5)
        ]
        config = {
            "processors": [
                {
                    "name": "text_substitution",
                    "config": {
                        "substitutions": [
                            {"from": "INT.", "to": "INTERIOR", "fields": ["text"]}
                        ]
                    },
                }
            ]
        }

        result = run_preview(chunks, config_dicts=[config], max_changed_chunks=2)

        assert result["changed_chunk_count"] == 5
        assert len(result["changed_chunks"]) == 2
        assert result["truncated"] is True

    def test_no_cap_by_default(self):
        """Without a cap, all changed chunks are returned untruncated."""
        result = run_preview(SAMPLE_CHUNKS, config_dicts=[PIPELINE_CONFIG])

        assert result["truncated"] is False
        assert len(result["changed_chunks"]) == result["changed_chunk_count"]


# A draft that adds one substitution on top of PIPELINE_CONFIG
DRAFT_CONFIG = {
    "preprocessors": copy.deepcopy(PIPELINE_CONFIG["preprocessors"]),
    "processors": [
        {
            "name": "text_substitution",
            "config": {
                "substitutions": [
                    {"from": "INT.", "to": "INTERIOR", "fields": ["text"]},
                    {"from": "Hello", "to": "Greetings", "fields": ["text"]},
                ]
            },
        },
        copy.deepcopy(PIPELINE_CONFIG["processors"][1]),
    ],
}


class TestRunPreviewDiff:
    """Tests for the run_preview_diff function."""

    def test_requires_exactly_one_baseline_source(self):
        """Exactly one baseline source must be provided."""
        with pytest.raises(ValueError, match="exactly one"):
            run_preview_diff(SAMPLE_CHUNKS, draft_config_dicts=[DRAFT_CONFIG])

        with pytest.raises(ValueError, match="exactly one"):
            run_preview_diff(
                SAMPLE_CHUNKS,
                draft_config_dicts=[DRAFT_CONFIG],
                baseline_config_paths=[],
                baseline_config_dicts=[],
            )

    def test_reports_only_chunks_the_draft_changes_differently(self):
        """Only chunks whose final output differs between the runs appear."""
        result = run_preview_diff(
            SAMPLE_CHUNKS,
            draft_config_dicts=[DRAFT_CONFIG],
            baseline_config_dicts=[PIPELINE_CONFIG],
        )

        assert result["alignment"] == "index"
        assert result["changed_chunk_count"] == 1
        changed = result["changed_chunks"][0]
        # The scene heading is transformed identically by both pipelines and
        # must NOT appear; only the dialogue the new substitution touches does.
        assert changed["chunk_type"] == "dialogue"
        assert changed["speaker"] == "BOB"
        assert changed["before"]["text"] == "Hello there."
        assert changed["after"]["text"] == "Greetings there."
        assert result["truncated"] is False

    def test_identical_pipelines_report_no_changes(self):
        """Draft == baseline means an empty diff."""
        result = run_preview_diff(
            SAMPLE_CHUNKS,
            draft_config_dicts=[copy.deepcopy(PIPELINE_CONFIG)],
            baseline_config_dicts=[PIPELINE_CONFIG],
        )

        assert result["alignment"] == "index"
        assert result["changed_chunk_count"] == 0
        assert result["changed_chunks"] == []

    def test_counts_differ_falls_back_to_stage_summaries(self):
        """A preprocessor change that alters chunk counts skips per-chunk diffing."""
        draft = copy.deepcopy(PIPELINE_CONFIG)
        draft["preprocessors"] = [
            {
                "name": "skip_and_merge",
                "config": {"skip_types": ["page_number", "scene_heading"]},
            }
        ]

        result = run_preview_diff(
            SAMPLE_CHUNKS,
            draft_config_dicts=[draft],
            baseline_config_dicts=[PIPELINE_CONFIG],
        )

        assert result["alignment"] == "counts_differ"
        assert result["baseline_final_count"] == 2
        assert result["draft_final_count"] == 1
        assert result["changed_chunks"] == []
        assert result["changed_chunk_count"] == 0
        # Both runs' stage summaries are available for the stage-level story
        assert result["baseline_stages"][0]["after_count"] == 2
        assert result["draft_stages"][0]["after_count"] == 1

    def test_max_changed_chunks_caps_diff(self):
        """The diff respects the cap and flags truncation."""
        chunks = [
            {"type": "dialogue", "speaker": "BOB", "text": f"Hello {i}"}
            for i in range(5)
        ]
        baseline = {"processors": []}
        draft = {
            "processors": [
                {
                    "name": "text_substitution",
                    "config": {
                        "substitutions": [
                            {"from": "Hello", "to": "Hi", "fields": ["text"]}
                        ]
                    },
                }
            ]
        }

        result = run_preview_diff(
            chunks,
            draft_config_dicts=[draft],
            baseline_config_dicts=[baseline],
            max_changed_chunks=2,
        )

        assert result["changed_chunk_count"] == 5
        assert len(result["changed_chunks"]) == 2
        assert result["truncated"] is True

    def test_input_chunks_not_mutated(self):
        """run_preview_diff never mutates the caller's chunk list."""
        original = copy.deepcopy(SAMPLE_CHUNKS)

        run_preview_diff(
            SAMPLE_CHUNKS,
            draft_config_dicts=[DRAFT_CONFIG],
            baseline_config_dicts=[PIPELINE_CONFIG],
        )

        assert SAMPLE_CHUNKS == original


class TestPreviewMatchesPipeline:
    """The stepwise preview must reproduce the real pipeline's output exactly.

    Preview applies preprocessors then processors chunk-by-chunk to build its
    attribution; this guards against that stepwise walk drifting from what
    TextProcessorManager.process_chunks actually produces for audio.
    """

    def test_preview_final_matches_manager_process_chunks(self):
        manager = TextProcessorManager.from_dicts([PIPELINE_CONFIG])
        real_final = manager.process_chunks(copy.deepcopy(SAMPLE_CHUNKS))
        preprocessed = manager.preprocess_chunks(copy.deepcopy(SAMPLE_CHUNKS))

        preview = run_preview(SAMPLE_CHUNKS, config_dicts=[PIPELINE_CONFIG])

        # Reconstruct the preview's full final list by overlaying each reported
        # changed chunk (keyed by post-preprocessing index) onto the baseline.
        preview_final = [dict(chunk) for chunk in preprocessed]
        for changed in preview["changed_chunks"]:
            preview_final[changed["index"]] = changed["after"]

        assert preview["final_chunk_count"] == len(real_final)
        assert preview_final == real_final
