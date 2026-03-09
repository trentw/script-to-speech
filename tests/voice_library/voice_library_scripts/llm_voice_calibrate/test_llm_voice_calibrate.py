"""Tests for calibration report building logic."""

import pytest

from script_to_speech.voice_library.voice_library_scripts.llm_voice_calibrate.llm_voice_calibrate import (
    build_calibration_report,
    print_calibration_report,
)


def _make_run_result(age=0.5, pitch=0.5, gender="male", accent="american"):
    """Build a minimal LLM run result dict."""
    return {
        "voice_properties": {
            "age": age,
            "authority": 0.5,
            "energy": 0.5,
            "pace": 0.5,
            "performative": 0.5,
            "pitch": pitch,
            "quality": 0.9,
            "range": 0.5,
            "gender": gender,
            "accent": accent,
        },
        "description": {"custom_description": "test"},
        "tags": {"character_types": ["narrator"]},
    }


def _make_ground_truth(age=0.5, pitch=0.5, gender="male", accent="american"):
    """Build a ground truth voice entry."""
    return {
        "voice_properties": {
            "age": age,
            "authority": 0.5,
            "energy": 0.5,
            "pace": 0.5,
            "performative": 0.5,
            "pitch": pitch,
            "quality": 0.9,
            "range": 0.5,
            "gender": gender,
            "accent": accent,
        },
    }


class TestBuildCalibrationReport:
    """Tests for build_calibration_report()."""

    def test_range_mae_calculation(self):
        # Arrange — predicted age=0.6 vs ground truth age=0.5 → error=0.1
        all_model_results = {
            "model_a": {
                "v1": [
                    _make_run_result(age=0.6),
                    _make_run_result(age=0.6),
                    _make_run_result(age=0.6),
                ],
            }
        }
        ground_truth = {"v1": _make_ground_truth(age=0.5)}

        # Act
        report = build_calibration_report(all_model_results, ground_truth)

        # Assert
        model_report = report["models"]["model_a"]
        assert "age" in model_report["range_properties"]
        age_stats = model_report["range_properties"]["age"]
        assert age_stats["mean_absolute_error"] == pytest.approx(0.1, abs=0.05)

    def test_enum_accuracy_perfect_match(self):
        # Arrange
        all_model_results = {
            "model_a": {
                "v1": [_make_run_result(gender="male")] * 3,
            }
        }
        ground_truth = {"v1": _make_ground_truth(gender="male")}

        # Act
        report = build_calibration_report(all_model_results, ground_truth)

        # Assert
        model_report = report["models"]["model_a"]
        assert model_report["enum_properties"]["gender"]["accuracy"] == 1.0

    def test_enum_accuracy_mismatch(self):
        # Arrange
        all_model_results = {
            "model_a": {
                "v1": [_make_run_result(gender="female")] * 3,
            }
        }
        ground_truth = {"v1": _make_ground_truth(gender="male")}

        # Act
        report = build_calibration_report(all_model_results, ground_truth)

        # Assert
        model_report = report["models"]["model_a"]
        assert model_report["enum_properties"]["gender"]["accuracy"] == 0.0

    def test_skips_unknown_voices(self):
        # Arrange — model produced results for v2 but ground_truth only has v1
        all_model_results = {
            "model_a": {
                "v1": [_make_run_result()] * 3,
                "v2": [_make_run_result()] * 3,
            }
        }
        ground_truth = {"v1": _make_ground_truth()}

        # Act
        report = build_calibration_report(all_model_results, ground_truth)

        # Assert
        per_voice = report["models"]["model_a"]["per_voice"]
        assert "v1" in per_voice
        assert "v2" not in per_voice

    def test_overall_range_mae(self):
        # Arrange
        all_model_results = {
            "model_a": {
                "v1": [_make_run_result(age=0.6, pitch=0.7)] * 3,
            }
        }
        ground_truth = {"v1": _make_ground_truth(age=0.5, pitch=0.5)}

        # Act
        report = build_calibration_report(all_model_results, ground_truth)

        # Assert
        assert "overall_range_mae" in report["models"]["model_a"]
        assert report["models"]["model_a"]["overall_range_mae"] > 0

    def test_multi_model_summary_picks_best(self):
        # Arrange — model_a has lower error than model_b
        all_model_results = {
            "model_a": {
                "v1": [_make_run_result(age=0.55)] * 3,  # close to truth
            },
            "model_b": {
                "v1": [_make_run_result(age=0.9)] * 3,  # far from truth
            },
        }
        ground_truth = {"v1": _make_ground_truth(age=0.5)}

        # Act
        report = build_calibration_report(all_model_results, ground_truth)

        # Assert
        assert "best_range_model" in report["summary"]
        assert report["summary"]["best_range_model"] == "model_a"

    def test_single_model_no_best_model_summary(self):
        # Arrange
        all_model_results = {
            "model_a": {
                "v1": [_make_run_result()] * 3,
            }
        }
        ground_truth = {"v1": _make_ground_truth()}

        # Act
        report = build_calibration_report(all_model_results, ground_truth)

        # Assert
        assert "best_range_model" not in report["summary"]

    def test_per_voice_errors_have_expected_keys(self):
        # Arrange
        all_model_results = {
            "model_a": {
                "v1": [_make_run_result(age=0.6, gender="male")] * 3,
            }
        }
        ground_truth = {"v1": _make_ground_truth(age=0.5, gender="male")}

        # Act
        report = build_calibration_report(all_model_results, ground_truth)

        # Assert
        voice_report = report["models"]["model_a"]["per_voice"]["v1"]
        assert "errors" in voice_report
        assert "flags" in voice_report
        # Range props have ground_truth, predicted, error
        age_error = voice_report["errors"]["age"]
        assert "ground_truth" in age_error
        assert "predicted" in age_error
        assert "error" in age_error
        # Enum props have ground_truth, predicted, match
        gender_error = voice_report["errors"]["gender"]
        assert "ground_truth" in gender_error
        assert "predicted" in gender_error
        assert "match" in gender_error


class TestPrintCalibrationReport:
    """Tests for print_calibration_report()."""

    def test_runs_without_error(self, capsys):
        # Arrange
        report = {
            "models": {
                "test-model": {
                    "overall_range_mae": 0.05,
                    "range_properties": {
                        "age": {
                            "mean_absolute_error": 0.05,
                            "median_absolute_error": 0.05,
                            "max_error": 0.1,
                            "n": 3,
                        },
                    },
                    "enum_properties": {
                        "gender": {"accuracy": 1.0, "correct": 3, "total": 3},
                    },
                    "per_voice": {},
                }
            },
            "summary": {},
        }

        # Act
        print_calibration_report(report)

        # Assert — just verify it ran without error
        output = capsys.readouterr().out
        assert len(output) > 0
