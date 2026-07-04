"""Unit tests for the text processor config service.

All file writes happen inside pytest tmp_path workspaces; the user default
config path is patched so no real user files are touched.
"""

import copy
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from script_to_speech.gui_backend.services import (
    text_processor_config_service as service_module,
)
from script_to_speech.gui_backend.services.text_processor_config_service import (
    ConfigConflictError,
    ConfigValidationError,
    TextProcessorConfigService,
)
from script_to_speech.text_processors import config_generation
from script_to_speech.text_processors.processor_manager import TextProcessorManager
from script_to_speech.text_processors.utils import (
    DEFAULT_TEXT_PROCESSOR_CONFIG,
    get_text_processor_configs,
)

LEGACY_YAML = """\
processors:
  - name: text_substitution
    config:
      substitutions:
        - from: "CU"
          to: "close up"
          fields:
            - text
"""

SAMPLE_CHUNKS = [
    {"type": "page_number", "speaker": "", "raw_text": "12", "text": "12"},
    {
        "type": "scene_heading",
        "speaker": "",
        "raw_text": "INT. CU LAB -- NIGHT",
        "text": "INT. CU LAB -- NIGHT",
    },
    {
        "type": "dialogue",
        "speaker": "BOB",
        "raw_text": "Look at the CU now.",
        "text": "Look at the CU now.",
    },
]


@pytest.fixture(autouse=True)
def user_default_path(tmp_path):
    """Redirect the user default config path into the test tmp dir."""
    path = (
        tmp_path
        / "user_workspace"
        / "text_processors"
        / "configs"
        / "user_default_text_processor_config.yaml"
    )
    with (
        patch.object(config_generation, "USER_DEFAULT_CONFIG_PATH", path),
        patch.object(service_module, "USER_DEFAULT_CONFIG_PATH", path),
    ):
        yield path


@pytest.fixture
def service(tmp_path):
    """Service bound to an isolated tmp workspace."""
    workspace = tmp_path / "workspace"
    (workspace / "input").mkdir(parents=True)
    return TextProcessorConfigService(workspace_dir=workspace)


@pytest.fixture
def project_dir(service):
    """A minimal parsed project inside the workspace."""
    project = service.input_dir / "my_script"
    project.mkdir()
    (project / "my_script.json").write_text("[]", encoding="utf-8")
    return project


class TestGetRegistry:
    """Tests for registry enumeration."""

    def test_registry_shape(self, service):
        """The registry lists all processors with schemas and chunk metadata."""
        registry = service.get_registry()

        assert {p["name"] for p in registry["preprocessors"]} == {
            "skip_and_merge",
            "dual_dialogue",
            "extract_dialogue_parentheticals",
            "speaker_merge",
        }
        assert {p["name"] for p in registry["processors"]} == {
            "skip_empty",
            "text_substitution",
            "pattern_replace",
            "capitalization_transform",
        }
        assert "dialogue" in registry["chunk_types"]
        assert registry["chunk_fields"] == ["type", "speaker", "text", "raw_text"]
        for item in registry["preprocessors"] + registry["processors"]:
            assert item["schema"] is not None
            assert item["label"]

    def test_dual_dialogue_reports_override_mode(self, service):
        """dual_dialogue is the only override-mode component."""
        registry = service.get_registry()

        by_name = {p["name"]: p for p in registry["preprocessors"]}
        assert by_name["dual_dialogue"]["multi_config_mode"] == "override"
        assert by_name["skip_and_merge"]["multi_config_mode"] == "chain"


class TestValidateEntries:
    """Tests for entry validation."""

    def test_valid_entries_pass(self, service):
        """Well-formed entries validate cleanly."""
        entries = [
            {
                "kind": "processor",
                "name": "skip_empty",
                "config": {"skip_types": ["page_number"]},
            }
        ]

        result = service.validate_entries(entries)

        assert result["valid"] is True
        assert result["errors"] == []

    def test_invalid_regex_fails(self, service):
        """A pattern_replace entry with an invalid regex is rejected."""
        entries = [
            {
                "kind": "processor",
                "name": "pattern_replace",
                "config": {
                    "replacements": [
                        {
                            "match_field": "type",
                            "match_pattern": "[unclosed",
                            "replace_field": "text",
                            "replace_pattern": ".*",
                            "replace_string": "",
                        }
                    ]
                },
            }
        ]

        result = service.validate_entries(entries)

        assert result["valid"] is False
        assert result["errors"][0]["name"] == "pattern_replace"

    def test_unknown_processor_warns_but_passes(self, service):
        """Unknown processor names warn instead of blocking the save."""
        entries = [{"kind": "processor", "name": "my_custom_thing", "config": {}}]

        result = service.validate_entries(entries)

        assert result["valid"] is True
        assert "my_custom_thing" in result["warnings"][0]["message"]

    def test_unparseable_config_yaml_fails(self, service):
        """A config_yaml snippet that isn't valid YAML is rejected."""
        entries = [
            {"kind": "processor", "name": "skip_empty", "config_yaml": "foo: [unclosed"}
        ]

        result = service.validate_entries(entries)

        assert result["valid"] is False
        assert "Invalid config YAML" in result["errors"][0]["message"]


class TestReadConfig:
    """Tests for reading (and auto-creating) the per-project config."""

    def test_read_auto_creates_standalone_config(self, service, project_dir):
        """Reading a project without a config seeds one from the defaults."""
        result = service.read_config(str(project_dir))

        config_file = project_dir / "my_script_text_processor_config.yaml"
        assert config_file.exists()
        assert result["metadata"]["mode"] == "standalone"
        assert result["is_legacy_additive"] is False
        assert result["stale"] is False
        assert result["file_hash"]
        entry_names = [e["name"] for e in result["entries"]]
        assert "skip_and_merge" in entry_names
        assert "capitalization_transform" in entry_names
        assert all(e["known"] for e in result["entries"])

    def test_read_legacy_config_flags_it(self, service, project_dir):
        """An unmarked config file is reported as legacy additive."""
        config_file = project_dir / "my_script_text_processor_config.yaml"
        config_file.write_text(LEGACY_YAML, encoding="utf-8")

        result = service.read_config(str(project_dir))

        assert result["is_legacy_additive"] is True
        assert result["metadata"] is None
        assert [e["name"] for e in result["entries"]] == ["text_substitution"]

    def test_read_rejects_paths_outside_workspace(self, service, tmp_path):
        """Paths outside the workspace input directory are rejected."""
        outside = tmp_path / "elsewhere"
        outside.mkdir()

        with pytest.raises(ValueError, match="outside the workspace"):
            service.read_config(str(outside))


class TestWriteConfig:
    """Tests for writing the per-project config."""

    def test_write_round_trip(self, service, project_dir):
        """Edited entries are written back and re-read consistently."""
        read = service.read_config(str(project_dir))
        entries = read["entries"]
        # Remove the first processor entry and add a new substitution processor
        entries = [e for e in entries if e["name"] != "skip_empty"]
        entries.append(
            {
                "kind": "processor",
                "name": "text_substitution",
                "config": {
                    "substitutions": [
                        {"from": "CU", "to": "close up", "fields": ["text"]}
                    ]
                },
                "config_yaml": None,
            }
        )

        result = service.write_config(str(project_dir), entries, read["file_hash"])

        names = [e["name"] for e in result["entries"]]
        assert "skip_empty" not in names
        assert names.count("text_substitution") == 2
        # Metadata block survives the write
        assert result["metadata"]["mode"] == "standalone"

    def test_write_preserves_comments_of_untouched_entries(self, service, project_dir):
        """Entries passed back with their config_yaml keep their comments."""
        # Seed the config, then hand-edit a comment into an entry's config
        # sub-tree the way a CLI user would
        service.read_config(str(project_dir))
        config_file = project_dir / "my_script_text_processor_config.yaml"
        config_file.write_text(
            config_file.read_text(encoding="utf-8").replace(
                "        - page_number\n",
                "        # my hand-written reminder\n        - page_number\n",
                1,
            ),
            encoding="utf-8",
        )
        read = service.read_config(str(project_dir))

        service.write_config(str(project_dir), read["entries"], read["file_hash"])

        text = config_file.read_text(encoding="utf-8")
        assert "my hand-written reminder" in text

    def test_write_with_stale_hash_conflicts(self, service, project_dir):
        """A write against a changed file raises ConfigConflictError."""
        read = service.read_config(str(project_dir))
        config_file = project_dir / "my_script_text_processor_config.yaml"
        config_file.write_text(
            config_file.read_text() + "\n# changed elsewhere\n", encoding="utf-8"
        )

        with pytest.raises(ConfigConflictError):
            service.write_config(str(project_dir), read["entries"], read["file_hash"])

    def test_write_with_invalid_entry_fails(self, service, project_dir):
        """Validation failures block the write."""
        read = service.read_config(str(project_dir))
        entries = read["entries"] + [
            {"kind": "processor", "name": "skip_empty", "config": {}}
        ]

        with pytest.raises(ConfigValidationError):
            service.write_config(str(project_dir), entries, read["file_hash"])

    def test_written_config_produces_identical_output(self, service, project_dir):
        """A no-op write leaves processing behavior unchanged."""
        read = service.read_config(str(project_dir))
        json_path = project_dir / "my_script.json"

        before = TextProcessorManager(
            get_text_processor_configs(json_path)
        ).process_chunks(copy.deepcopy(SAMPLE_CHUNKS))

        service.write_config(str(project_dir), read["entries"], read["file_hash"])

        after = TextProcessorManager(
            get_text_processor_configs(json_path)
        ).process_chunks(copy.deepcopy(SAMPLE_CHUNKS))

        assert before == after


class TestConvertLegacyToStandalone:
    """Tests for legacy -> standalone conversion."""

    def test_convert_is_behavior_preserving(self, service, project_dir):
        """Converted configs process chunks identically to the legacy chain."""
        config_file = project_dir / "my_script_text_processor_config.yaml"
        config_file.write_text(LEGACY_YAML, encoding="utf-8")
        json_path = project_dir / "my_script.json"

        before = TextProcessorManager(
            get_text_processor_configs(json_path)
        ).process_chunks(copy.deepcopy(SAMPLE_CHUNKS))

        result = service.convert_legacy_to_standalone(str(project_dir))

        after = TextProcessorManager(
            get_text_processor_configs(json_path)
        ).process_chunks(copy.deepcopy(SAMPLE_CHUNKS))

        assert before == after
        assert result["is_legacy_additive"] is False
        assert result["metadata"]["mode"] == "standalone"
        # Legacy entry appended after default entries
        assert [e["name"] for e in result["entries"]][-1] == "text_substitution"

    def test_convert_standalone_is_noop(self, service, project_dir):
        """Converting an already-standalone config changes nothing."""
        read = service.read_config(str(project_dir))

        result = service.convert_legacy_to_standalone(str(project_dir))

        assert result["file_hash"] == read["file_hash"]


class TestResetConfig:
    """Tests for re-seeding the per-project config."""

    def test_reset_restores_shipped_default(self, service, project_dir):
        """Reset from shipped defaults discards edits."""
        read = service.read_config(str(project_dir))
        entries = [e for e in read["entries"] if e["kind"] == "preprocessor"]
        service.write_config(str(project_dir), entries, read["file_hash"])

        result = service.reset_config(str(project_dir), "shipped_default")

        names = [e["name"] for e in result["entries"]]
        assert "capitalization_transform" in names
        assert result["stale"] is False

    def test_reset_from_missing_user_default_fails(self, service, project_dir):
        """Resetting from a nonexistent user default raises."""
        service.read_config(str(project_dir))

        with pytest.raises(FileNotFoundError):
            service.reset_config(str(project_dir), "user_default")


class TestGlobalDefault:
    """Tests for the user global default config."""

    def test_read_missing_global_default(self, service):
        """Reading with no saved global default reports exists=False."""
        result = service.read_global_default()

        assert result["exists"] is False

    def test_write_and_read_global_default(self, service, user_default_path):
        """Saving a global default creates the workspace file."""
        entries = [
            {
                "kind": "processor",
                "name": "skip_empty",
                "config": {"skip_types": ["page_number"]},
            }
        ]

        result = service.write_global_default(entries, based_on_default_sha256="abc")

        assert result["exists"] is True
        assert user_default_path.exists()
        data = yaml.safe_load(user_default_path.read_text())
        assert data["sts_metadata"]["mode"] == "user_default"
        assert data["sts_metadata"]["default_config_sha256"] == "abc"

    def test_global_default_seeds_new_projects(self, service, user_default_path):
        """New projects seed from the saved global default, carrying its hash."""
        entries = [
            {
                "kind": "processor",
                "name": "skip_empty",
                "config": {"skip_types": ["page_number"]},
            }
        ]
        service.write_global_default(entries, based_on_default_sha256="abc")

        project = service.input_dir / "next_script"
        project.mkdir()
        (project / "next_script.json").write_text("[]", encoding="utf-8")
        result = service.read_config(str(project))

        assert result["metadata"]["seeded_from"] == "user_default"
        assert result["metadata"]["default_config_sha256"] == "abc"
        assert [e["name"] for e in result["entries"]] == ["skip_empty"]
        # Carried hash no longer matches the shipped default -> stale
        assert result["stale"] is True

    def test_delete_global_default(self, service, user_default_path):
        """Deleting the global default removes the file."""
        service.write_global_default(
            [{"kind": "processor", "name": "skip_empty", "config": {"skip_types": []}}]
        )

        result = service.delete_global_default()

        assert result["exists"] is False
        assert not user_default_path.exists()


class TestRunPreviewForProject:
    """Tests for previewing a project's pipeline."""

    def _write_chunks(self, project_dir):
        chunks_json = (
            '[{"type": "scene_heading", "speaker": "", '
            '"raw_text": "INT. LAB", "text": "INT. LAB"}]'
        )
        (project_dir / "my_script.json").write_text(chunks_json, encoding="utf-8")

    def test_preview_saved_config(self, service, project_dir):
        """With no draft entries, the saved (auto-created) config is used."""
        self._write_chunks(project_dir)

        result = service.run_preview_for_project(str(project_dir))

        assert result["input_chunk_count"] == 1
        changed = result["changed_chunks"][0]
        # Default pipeline: INT. -> INTERIOR, then sentence_case
        assert changed["after"]["text"] == "Interior lab"

    def test_preview_draft_entries(self, service, project_dir):
        """Draft entries preview without touching the saved config."""
        self._write_chunks(project_dir)
        saved = service.read_config(str(project_dir))
        draft = [
            {
                "kind": "processor",
                "name": "text_substitution",
                "config": {
                    "substitutions": [
                        {"from": "LAB", "to": "LABORATORY", "fields": ["text"]}
                    ]
                },
            }
        ]

        result = service.run_preview_for_project(str(project_dir), entries=draft)

        assert result["changed_chunks"][0]["after"]["text"] == "INT. LABORATORY"
        # Saved config untouched
        assert service.read_config(str(project_dir))["file_hash"] == saved["file_hash"]

    def test_preview_invalid_draft_fails(self, service, project_dir):
        """Draft entries failing validation raise ConfigValidationError."""
        self._write_chunks(project_dir)
        draft = [{"kind": "processor", "name": "skip_empty", "config": {}}]

        with pytest.raises(ConfigValidationError):
            service.run_preview_for_project(str(project_dir), entries=draft)

    def test_preview_without_json_fails(self, service):
        """A project without a parsed screenplay JSON cannot be previewed."""
        project = service.input_dir / "empty_project"
        project.mkdir()

        with pytest.raises(ValueError, match="does not exist"):
            service.run_preview_for_project(str(project))


class TestRunPreviewDiffForProject:
    """Tests for diffing a draft pipeline against a baseline."""

    BASELINE = [
        {
            "kind": "processor",
            "name": "text_substitution",
            "config": {
                "substitutions": [
                    {"from": "INT.", "to": "INTERIOR", "fields": ["text"]}
                ]
            },
        }
    ]

    def _write_chunks(self, project_dir):
        chunks_json = (
            '[{"type": "scene_heading", "speaker": "", '
            '"raw_text": "INT. LAB", "text": "INT. LAB"},'
            ' {"type": "dialogue", "speaker": "BOB", '
            '"raw_text": "Hello.", "text": "Hello."}]'
        )
        (project_dir / "my_script.json").write_text(chunks_json, encoding="utf-8")

    def _draft(self):
        draft = copy.deepcopy(self.BASELINE)
        draft[0]["config"]["substitutions"].append(
            {"from": "Hello", "to": "Greetings", "fields": ["text"]}
        )
        return draft

    def test_diff_reports_only_the_additional_effect(self, service, project_dir):
        """Only chunks the draft changes differently from the baseline appear."""
        self._write_chunks(project_dir)

        result = service.run_preview_diff_for_project(
            str(project_dir),
            draft_entries=self._draft(),
            baseline_entries=copy.deepcopy(self.BASELINE),
        )

        assert result["alignment"] == "index"
        assert result["changed_chunk_count"] == 1
        changed = result["changed_chunks"][0]
        # The scene heading changes identically under both configs -> excluded
        assert changed["chunk_type"] == "dialogue"
        assert changed["before"]["text"] == "Hello."
        assert changed["after"]["text"] == "Greetings."

    def test_diff_against_disk_when_no_baseline_given(self, service, project_dir):
        """With no baseline entries, the on-disk resolved config is the baseline."""
        self._write_chunks(project_dir)
        # Materialize the saved (auto-created) config, then diff a draft that
        # matches it entry-for-entry: nothing should change.
        saved = service.read_config(str(project_dir))

        result = service.run_preview_diff_for_project(
            str(project_dir), draft_entries=saved["entries"]
        )

        assert result["changed_chunk_count"] == 0

    def test_diff_invalid_entries_fail(self, service, project_dir):
        """Draft or baseline entries failing validation raise ConfigValidationError."""
        self._write_chunks(project_dir)
        bad = [{"kind": "processor", "name": "skip_empty", "config": {}}]

        with pytest.raises(ConfigValidationError):
            service.run_preview_diff_for_project(str(project_dir), draft_entries=bad)
        with pytest.raises(ConfigValidationError):
            service.run_preview_diff_for_project(
                str(project_dir),
                draft_entries=self._draft(),
                baseline_entries=bad,
            )
