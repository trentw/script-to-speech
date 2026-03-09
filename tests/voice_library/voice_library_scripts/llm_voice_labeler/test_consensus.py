"""Tests for consensus aggregation logic."""

from script_to_speech.voice_library.voice_library_scripts.llm_voice_labeler.consensus import (
    ENUM_PROPERTIES,
    RANGE_PROPERTIES,
    aggregate_runs,
    build_voice_consensus,
    merge_model_consensuses,
)

from .conftest import make_run


class TestAggregateRuns:
    """Tests for aggregate_runs()."""

    def test_all_errors_returns_error(self):
        # Arrange
        runs = [{"error": "fail1"}, {"error": "fail2"}]

        # Act
        consensus, flags = aggregate_runs(runs)

        # Assert
        assert "error" in consensus
        assert len(flags) > 0

    def test_filters_error_runs(self):
        # Arrange
        runs = [
            make_run(age=0.3, pitch=0.6),
            {"error": "some failure"},
            make_run(age=0.5, pitch=0.4),
        ]

        # Act
        consensus, flags = aggregate_runs(runs)

        # Assert
        assert "error" not in consensus
        assert "voice_properties" in consensus
        # Median of [0.3, 0.5] = 0.4
        assert consensus["voice_properties"]["age"] == 0.4

    def test_range_properties_median(self):
        # Arrange
        runs = [
            make_run(age=0.3, pitch=0.2),
            make_run(age=0.5, pitch=0.5),
            make_run(age=0.7, pitch=0.8),
        ]

        # Act
        consensus, flags = aggregate_runs(runs)

        # Assert
        assert consensus["voice_properties"]["age"] == 0.5
        assert consensus["voice_properties"]["pitch"] == 0.5

    def test_range_properties_rounds_to_005(self):
        # Arrange — 0.33 should round to 0.35, 0.47 to 0.45
        runs = [
            make_run(age=0.33),
            make_run(age=0.33),
            make_run(age=0.33),
        ]

        # Act
        consensus, _ = aggregate_runs(runs)

        # Assert
        result = consensus["voice_properties"]["age"]
        assert result == round(round(0.33 * 20) / 20, 2)

    def test_range_high_variance_flag(self):
        # Arrange — values [0.1, 0.5, 0.9] have high stdev
        runs = [
            make_run(age=0.1),
            make_run(age=0.5),
            make_run(age=0.9),
        ]

        # Act
        _, flags = aggregate_runs(runs)

        # Assert
        age_flags = [f for f in flags if "age" in f]
        assert len(age_flags) > 0

    def test_range_no_variance_flag_low_spread(self):
        # Arrange — values [0.5, 0.5, 0.55] have low stdev
        runs = [
            make_run(age=0.5),
            make_run(age=0.5),
            make_run(age=0.55),
        ]

        # Act
        _, flags = aggregate_runs(runs)

        # Assert
        age_flags = [f for f in flags if "age" in f]
        assert len(age_flags) == 0

    def test_range_no_variance_flag_with_two_values(self):
        # Arrange — fewer than 3 values, no variance check
        runs = [
            make_run(age=0.1),
            make_run(age=0.9),
        ]

        # Act
        _, flags = aggregate_runs(runs)

        # Assert — no variance flag because only 2 values
        age_flags = [f for f in flags if "age" in f]
        assert len(age_flags) == 0

    def test_range_skips_non_numeric(self):
        # Arrange
        run1 = make_run(age=0.3)
        run2 = make_run(age=0.7)
        run2["voice_properties"]["age"] = "old"  # non-numeric

        runs = [run1, run2]

        # Act
        consensus, _ = aggregate_runs(runs)

        # Assert — only the numeric value used
        assert consensus["voice_properties"]["age"] == 0.3

    def test_enum_mode(self):
        # Arrange
        runs = [
            make_run(gender="male"),
            make_run(gender="male"),
            make_run(gender="female"),
        ]

        # Act
        consensus, _ = aggregate_runs(runs)

        # Assert
        assert consensus["voice_properties"]["gender"] == "male"

    def test_enum_tie_flag(self):
        # Arrange
        runs = [
            make_run(gender="male"),
            make_run(gender="female"),
        ]

        # Act
        _, flags = aggregate_runs(runs)

        # Assert
        gender_flags = [f for f in flags if "gender" in f]
        assert len(gender_flags) > 0

    def test_text_properties_from_representative(self):
        # Arrange
        runs = [
            make_run(age=0.5, special_vocal_characteristics="slight rasp"),
            make_run(age=0.5, special_vocal_characteristics="breathy tone"),
            make_run(age=0.5, special_vocal_characteristics="warm quality"),
        ]

        # Act
        consensus, _ = aggregate_runs(runs)

        # Assert — should come from one of the runs
        svc = consensus["voice_properties"].get("special_vocal_characteristics")
        assert svc in ["slight rasp", "breathy tone", "warm quality"]

    def test_description_from_representative(self):
        # Arrange
        runs = [
            make_run(custom_description="desc_a", perceived_age="20-30"),
            make_run(custom_description="desc_b", perceived_age="30-40"),
        ]

        # Act
        consensus, _ = aggregate_runs(runs)

        # Assert
        assert consensus["description"]["custom_description"] in ["desc_a", "desc_b"]
        assert consensus["description"]["perceived_age"] in ["20-30", "30-40"]

    def test_reasoning_preserved(self):
        # Arrange
        reasoning = {"energy": "some analysis", "pitch": "another analysis"}
        runs = [
            make_run(reasoning=reasoning),
            make_run(reasoning={"energy": "different"}),
        ]

        # Act
        consensus, _ = aggregate_runs(runs)

        # Assert — reasoning from one of the representative runs
        assert "reasoning" in consensus

    def test_tags_50_percent_threshold(self):
        # Arrange — "narrator" in 2/3 runs (kept), "villain" in 1/3 (dropped)
        runs = [
            make_run(character_types=["narrator", "villain"]),
            make_run(character_types=["narrator"]),
            make_run(character_types=["hero"]),
        ]

        # Act
        consensus, _ = aggregate_runs(runs)

        # Assert
        ct = consensus["tags"]["character_types"]
        assert "narrator" in ct
        assert "villain" not in ct

    def test_tags_exact_50_percent(self):
        # Arrange — "narrator" in 2/4 runs (threshold=2.0, 2>=2.0 → kept)
        runs = [
            make_run(character_types=["narrator"]),
            make_run(character_types=["narrator"]),
            make_run(character_types=["hero"]),
            make_run(character_types=["hero"]),
        ]

        # Act
        consensus, _ = aggregate_runs(runs)

        # Assert
        ct = consensus["tags"]["character_types"]
        assert "narrator" in ct
        assert "hero" in ct

    def test_tags_non_list_ignored(self):
        # Arrange
        run1 = make_run(character_types=["narrator"])
        run2 = make_run()
        run2["tags"]["character_types"] = "not_a_list"

        runs = [run1, run2]

        # Act
        consensus, _ = aggregate_runs(runs)

        # Assert — no crash, narrator still counted from run1
        assert isinstance(consensus["tags"]["character_types"], list)

    def test_single_run(self):
        # Arrange
        runs = [make_run(age=0.47, pitch=0.63)]

        # Act
        consensus, flags = aggregate_runs(runs)

        # Assert
        assert "error" not in consensus
        assert "voice_properties" in consensus
        # Values should be rounded to nearest 0.05
        assert consensus["voice_properties"]["age"] == 0.45
        assert consensus["voice_properties"]["pitch"] == 0.65
        assert len(flags) == 0

    def test_empty_voice_properties(self):
        # Arrange
        runs = [{"description": {"custom_description": "test"}}]

        # Act
        consensus, _ = aggregate_runs(runs)

        # Assert — no crash
        assert isinstance(consensus["voice_properties"], dict)

    def test_returns_all_range_properties(self):
        # Arrange
        runs = [make_run(), make_run(), make_run()]

        # Act
        consensus, _ = aggregate_runs(runs)

        # Assert — all range properties present
        for prop in RANGE_PROPERTIES:
            assert prop in consensus["voice_properties"]

    def test_returns_all_enum_properties(self):
        # Arrange
        runs = [make_run(), make_run(), make_run()]

        # Act
        consensus, _ = aggregate_runs(runs)

        # Assert — all enum properties present
        for prop in ENUM_PROPERTIES:
            assert prop in consensus["voice_properties"]


class TestMergeModelConsensuses:
    """Tests for merge_model_consensuses()."""

    def test_single_model_passthrough(self):
        # Arrange
        consensus = make_run()
        per_model = {"model_a": (consensus, ["flag1"])}

        # Act
        result, flags = merge_model_consensuses(per_model)

        # Assert — result is the same consensus (structure preserved)
        assert result["voice_properties"]["age"] == consensus["voice_properties"]["age"]
        # Flags prefixed with model name
        assert all("[model_a]" in f for f in flags)

    def test_multiple_models_aggregates(self):
        # Arrange
        consensus_a = make_run(age=0.3, pitch=0.4)
        consensus_b = make_run(age=0.7, pitch=0.6)
        per_model = {
            "model_a": (consensus_a, []),
            "model_b": (consensus_b, []),
        }

        # Act
        result, flags = merge_model_consensuses(per_model)

        # Assert — merged via aggregate_runs, median of two
        assert "voice_properties" in result
        assert isinstance(result["voice_properties"]["age"], float)

    def test_flags_prefixed_with_model_name(self):
        # Arrange
        consensus_a = make_run()
        consensus_b = make_run()
        per_model = {
            "model_a": (consensus_a, ["some_flag"]),
            "model_b": (consensus_b, ["other_flag"]),
        }

        # Act
        _, flags = merge_model_consensuses(per_model)

        # Assert
        model_a_flags = [f for f in flags if "[model_a]" in f]
        model_b_flags = [f for f in flags if "[model_b]" in f]
        assert len(model_a_flags) >= 1
        assert len(model_b_flags) >= 1


class TestBuildVoiceConsensus:
    """Tests for build_voice_consensus()."""

    def test_single_model_single_voice(self):
        # Arrange
        all_results = {
            "model_a": {
                "voice1": [make_run(), make_run(), make_run()],
            }
        }

        # Act
        result = build_voice_consensus(all_results)

        # Assert
        assert "voice1" in result
        consensus, flags = result["voice1"]
        assert "voice_properties" in consensus
        assert isinstance(flags, list)

    def test_no_results_for_voice(self):
        # Arrange — voice appears in one model but not the other
        all_results = {
            "model_a": {
                "voice1": [make_run()],
                "voice2": [],
            }
        }

        # Act
        result = build_voice_consensus(all_results)

        # Assert — voice2 has error since empty list
        consensus2, flags2 = result["voice2"]
        assert "error" in consensus2

    def test_multiple_models(self):
        # Arrange
        all_results = {
            "model_a": {"voice1": [make_run(age=0.3)]},
            "model_b": {"voice1": [make_run(age=0.7)]},
        }

        # Act
        result = build_voice_consensus(all_results)

        # Assert
        consensus, _ = result["voice1"]
        assert "voice_properties" in consensus

    def test_voices_sorted(self):
        # Arrange
        all_results = {
            "model_a": {
                "zebra": [make_run()],
                "alpha": [make_run()],
                "middle": [make_run()],
            }
        }

        # Act
        result = build_voice_consensus(all_results)

        # Assert
        assert list(result.keys()) == sorted(result.keys())

    def test_result_keys_match_input_voices(self):
        # Arrange
        all_results = {
            "model_a": {
                "v1": [make_run()],
                "v2": [make_run()],
            },
            "model_b": {
                "v2": [make_run()],
                "v3": [make_run()],
            },
        }

        # Act
        result = build_voice_consensus(all_results)

        # Assert — all voice IDs from all models present
        assert set(result.keys()) == {"v1", "v2", "v3"}
