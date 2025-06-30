"""Tests for dictionary utility functions."""

import pytest

from script_to_speech.utils.dict_utils import deep_merge


class TestDeepMerge:
    """Tests for the deep_merge function."""

    def test_simple_merge_no_overlap(self):
        """Tests merging dictionaries with no common keys."""
        # Arrange
        d1 = {"a": 1}
        d2 = {"b": 2}

        # Act
        result = deep_merge(d1, d2)

        # Assert
        assert result == {"a": 1, "b": 2}

    def test_value_overwrite(self):
        """Tests that values from the second dictionary overwrite the first."""
        # Arrange
        d1 = {"a": 1, "b": 2}
        d2 = {"b": 3, "c": 4}

        # Act
        result = deep_merge(d1, d2)

        # Assert
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_list_merging_and_deduplication(self):
        """Tests that lists are merged and duplicates are removed."""
        # Arrange
        d1 = {"a": ["apple", "banana"], "b": [1]}
        d2 = {"a": ["banana", "cherry"], "c": [3]}

        # Act
        result = deep_merge(d1, d2)

        # Assert
        assert sorted(result["a"]) == ["apple", "banana", "cherry"]
        assert result["b"] == [1]
        assert result["c"] == [3]

    def test_nested_dictionary_merging(self):
        """Tests recursive merging of nested dictionaries."""
        # Arrange
        d1 = {"a": {"x": 1, "y": 2}, "b": {"z": 3}}
        d2 = {"a": {"y": 10, "z": 11}, "c": {"w": 12}}

        # Act
        result = deep_merge(d1, d2)

        # Assert
        assert result == {
            "a": {"x": 1, "y": 10, "z": 11},
            "b": {"z": 3},
            "c": {"w": 12},
        }

    def test_type_mismatch_overwrite_dict_to_scalar(self):
        """Tests that a scalar value overwrites a dictionary."""
        # Arrange
        d1 = {"a": {"x": 1}}
        d2 = {"a": "scalar_value"}

        # Act
        result = deep_merge(d1, d2)

        # Assert
        assert result == {"a": "scalar_value"}

    def test_type_mismatch_overwrite_scalar_to_dict(self):
        """Tests that a dictionary overwrites a scalar value."""
        # Arrange
        d1 = {"a": "scalar_value"}
        d2 = {"a": {"x": 1}}

        # Act
        result = deep_merge(d1, d2)

        # Assert
        assert result == {"a": {"x": 1}}

    def test_type_mismatch_overwrite_list_to_scalar(self):
        """Tests that a scalar value overwrites a list."""
        # Arrange
        d1 = {"a": [1, 2]}
        d2 = {"a": "scalar_value"}

        # Act
        result = deep_merge(d1, d2)

        # Assert
        assert result == {"a": "scalar_value"}

    def test_type_mismatch_overwrite_scalar_to_list(self):
        """Tests that a list overwrites a scalar value."""
        # Arrange
        d1 = {"a": "scalar_value"}
        d2 = {"a": [1, 2]}

        # Act
        result = deep_merge(d1, d2)

        # Assert
        assert result == {"a": [1, 2]}

    def test_merging_with_empty_dicts(self):
        """Tests merging with empty dictionaries."""
        # Arrange
        d1 = {"a": 1}
        empty_dict = {}

        # Act
        result1 = deep_merge(d1, empty_dict)
        result2 = deep_merge(empty_dict, d1)

        # Assert
        assert result1 == {"a": 1}
        assert result2 == {"a": 1}

    def test_complex_deeply_nested_merge(self):
        """Tests a complex scenario with multiple levels of nesting."""
        # Arrange
        base_schema = {
            "properties": {
                "age": {"description": "Original age", "type": "range"},
                "accent": {"type": "enum", "values": ["american", "british"]},
            },
            "settings": {"mode": "default"},
        }
        provider_schema = {
            "properties": {
                "age": {"description": "Updated age"},
                "accent": {"values": ["british", "australian"]},
                "humor": {"type": "range"},
            },
            "settings": {"mode": "override", "retries": 3},
        }

        # Act
        result = deep_merge(base_schema, provider_schema)

        # Assert
        expected = {
            "properties": {
                "age": {"description": "Updated age", "type": "range"},
                "accent": {
                    "type": "enum",
                    "values": ["american", "british", "australian"],
                },
                "humor": {"type": "range"},
            },
            "settings": {"mode": "override", "retries": 3},
        }
        assert sorted(result["properties"]["accent"]["values"]) == sorted(
            expected["properties"]["accent"]["values"]
        )
        # Adjust for list comparison before deep comparison
        result["properties"]["accent"]["values"].sort()
        expected["properties"]["accent"]["values"].sort()
        assert result == expected

    def test_input_dictionaries_are_not_mutated(self):
        """Ensures that the original input dictionaries are not modified."""
        # Arrange
        d1 = {"a": [1], "b": {"x": 10}}
        d2 = {"a": [2], "b": {"y": 20}}

        # Create copies for comparison after the merge
        d1_original = {"a": [1], "b": {"x": 10}}
        d2_original = {"a": [2], "b": {"y": 20}}

        # Act
        deep_merge(d1, d2)

        # Assert
        assert d1 == d1_original
        assert d2 == d2_original
