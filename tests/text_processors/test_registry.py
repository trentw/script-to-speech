"""Unit tests for text_processors.registry (processor enumeration and loading)."""

from pathlib import Path

import pytest

from script_to_speech.text_processors.registry import (
    AVAILABLE_PREPROCESSORS,
    AVAILABLE_PROCESSORS,
    CHUNK_FIELDS,
    get_chunk_types,
    load_processor_class,
)
from script_to_speech.text_processors.text_preprocessor_base import TextPreProcessor
from script_to_speech.text_processors.text_processor_base import TextProcessor

TEXT_PROCESSORS_DIR = (
    Path(__file__).parents[2] / "src" / "script_to_speech" / "text_processors"
)

# Valid field types for config schemas (the GUI's rendering vocabulary)
VALID_FIELD_TYPES = {
    "string",
    "integer",
    "boolean",
    "enum",
    "list",
    "object",
    "dict_of_string_lists",
}


def _scan_names(directory: Path, suffix: str) -> set:
    """Scan a directory for processor module names (dev-mode drift guard)."""
    return {
        path.name.removesuffix(f"_{suffix}.py")
        for path in directory.glob(f"*_{suffix}.py")
    }


def _assert_valid_field_spec(field: dict, context: str) -> None:
    """Assert a schema field spec is structurally valid (recursively)."""
    assert "name" in field, f"{context}: field missing name"
    assert (
        field.get("type") in VALID_FIELD_TYPES
    ), f"{context}: field {field.get('name')} has invalid type {field.get('type')}"
    if field["type"] == "enum":
        assert field.get("enum"), f"{context}: enum field {field['name']} missing enum"
    if field["type"] == "list":
        item_schema = field.get("item_schema")
        assert item_schema, f"{context}: list field {field['name']} missing item_schema"
        if item_schema.get("type") == "object":
            for nested in item_schema.get("fields", []):
                _assert_valid_field_spec(nested, f"{context}.{field['name']}")
        else:
            assert item_schema.get("type") in VALID_FIELD_TYPES


class TestAvailableLists:
    """Tests that the static registry lists track the modules on disk."""

    def test_available_preprocessors_match_filesystem(self):
        """AVAILABLE_PREPROCESSORS matches the preprocessor modules on disk."""
        scanned = _scan_names(TEXT_PROCESSORS_DIR / "preprocessors", "preprocessor")

        assert set(AVAILABLE_PREPROCESSORS) == scanned

    def test_available_processors_match_filesystem(self):
        """AVAILABLE_PROCESSORS matches the processor modules on disk."""
        scanned = _scan_names(TEXT_PROCESSORS_DIR / "processors", "processor")

        assert set(AVAILABLE_PROCESSORS) == scanned


class TestLoadProcessorClass:
    """Tests for the load_processor_class function."""

    @pytest.mark.parametrize("name", AVAILABLE_PREPROCESSORS)
    def test_loads_every_preprocessor(self, name):
        """Every registered preprocessor loads as a TextPreProcessor subclass."""
        loaded = load_processor_class("preprocessor", name)

        assert issubclass(loaded, TextPreProcessor)

    @pytest.mark.parametrize("name", AVAILABLE_PROCESSORS)
    def test_loads_every_processor(self, name):
        """Every registered processor loads as a TextProcessor subclass."""
        loaded = load_processor_class("processor", name)

        assert issubclass(loaded, TextProcessor)

    def test_unknown_name_raises(self):
        """An unknown processor name raises ValueError."""
        with pytest.raises(ValueError, match="Error loading processor"):
            load_processor_class("processor", "does_not_exist")

    def test_unknown_kind_raises(self):
        """An unknown processor kind raises ValueError."""
        with pytest.raises(ValueError, match="Unknown processor kind"):
            load_processor_class("widget", "skip_empty")  # type: ignore[arg-type]


class TestConfigSchemas:
    """Tests that every shipped processor declares a structurally valid schema."""

    @pytest.mark.parametrize(
        "kind, name",
        [("preprocessor", name) for name in AVAILABLE_PREPROCESSORS]
        + [("processor", name) for name in AVAILABLE_PROCESSORS],
    )
    def test_schema_is_structurally_valid(self, kind, name):
        """Each shipped processor's schema has label, description, and valid fields."""
        loaded = load_processor_class(kind, name)

        schema = loaded.get_config_schema()

        assert schema is not None, f"{name} has no config schema"
        assert schema.get("label"), f"{name} schema missing label"
        assert schema.get("description"), f"{name} schema missing description"
        for field in schema.get("fields", []):
            _assert_valid_field_spec(field, name)


class TestChunkMetadata:
    """Tests for chunk type / field enumeration."""

    def test_chunk_types_include_known_types(self):
        """Chunk types come from the parser State enum."""
        chunk_types = get_chunk_types()

        for expected in ["dialogue", "scene_heading", "page_number", "dual_dialogue"]:
            assert expected in chunk_types

    def test_chunk_fields(self):
        """Chunk fields match the parser Chunk dataclass."""
        assert CHUNK_FIELDS == ["type", "speaker", "text", "raw_text"]
