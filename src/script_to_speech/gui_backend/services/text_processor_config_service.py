"""Service for reading and writing text processor configuration files.

Follows the thin-wrapper principle: the per-screenplay config file on disk
(shared with the CLI) is the source of truth. Reads parse the file into a
structured "entries" view the frontend can edit without a YAML library;
writes rebuild the file with ruamel.yaml so comments survive round-trips.

Concurrency follows the voice-casting optimistic-locking pattern, with the
file content hash as the version token: reads return file_hash, writes
require the matching base_file_hash and fail with ConfigConflictError (HTTP
409) when the file changed out from under the editor.
"""

import hashlib
import json
import logging
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq

from script_to_speech._version import __version__
from script_to_speech.text_processors.config_generation import (
    MODE_STANDALONE,
    MODE_USER_DEFAULT,
    USER_DEFAULT_CONFIG_PATH,
    generate_text_processor_config,
    get_current_default_hash,
    get_text_processor_config_path,
    is_config_stale,
    seed_config_text,
)
from script_to_speech.text_processors.preview import run_preview, run_preview_diff
from script_to_speech.text_processors.registry import (
    AVAILABLE_PREPROCESSORS,
    AVAILABLE_PROCESSORS,
    CHUNK_FIELDS,
    get_chunk_types,
    load_processor_class,
)
from script_to_speech.text_processors.utils import (
    DEFAULT_TEXT_PROCESSOR_CONFIG,
    get_text_processor_configs,
)

from ..config import settings

logger = logging.getLogger(__name__)

_SECTIONS = (("preprocessor", "preprocessors"), ("processor", "processors"))


class ConfigConflictError(Exception):
    """The config file changed since the client last read it (stale hash)."""


class ConfigValidationError(Exception):
    """One or more config entries failed validation."""

    def __init__(self, errors: List[Dict[str, Any]]):
        super().__init__("Text processor config validation failed")
        self.errors = errors


def _create_yaml() -> YAML:
    """Create a ruamel YAML instance configured like voice casting's editor."""
    ruamel_yaml = YAML()
    ruamel_yaml.preserve_quotes = True
    ruamel_yaml.width = 4096  # Prevent line wrapping
    ruamel_yaml.indent(mapping=2, sequence=4, offset=2)
    return ruamel_yaml


class TextProcessorConfigService:
    """Service for text processor config CRUD, validation, and registry data."""

    def __init__(self, workspace_dir: Optional[Path] = None) -> None:
        if workspace_dir is None:
            workspace_dir = settings.WORKSPACE_DIR
        if workspace_dir is None:
            raise ValueError(
                "Workspace directory is not configured. Set STS_WORKSPACE_DIR environment variable."
            )
        self.workspace_dir = Path(workspace_dir)
        self.input_dir = self.workspace_dir / "input"

    # ------------------------------------------------------------------
    # Registry
    # ------------------------------------------------------------------

    def get_registry(self) -> Dict[str, Any]:
        """Enumerate available processors with their schemas and chunk metadata."""
        return {
            "preprocessors": [
                self._describe("preprocessor", name) for name in AVAILABLE_PREPROCESSORS
            ],
            "processors": [
                self._describe("processor", name) for name in AVAILABLE_PROCESSORS
            ],
            "chunk_types": get_chunk_types(),
            "chunk_fields": CHUNK_FIELDS,
        }

    def _describe(self, kind: str, name: str) -> Dict[str, Any]:
        """Describe one processor for the registry response."""
        loaded_class = load_processor_class(kind, name)  # type: ignore[arg-type]
        try:
            multi_config_mode = loaded_class({}).multi_config_mode
        except Exception:
            multi_config_mode = "chain"

        schema = loaded_class.get_config_schema()
        return {
            "name": name,
            "kind": kind,
            "label": (schema or {}).get("label", name),
            "description": (schema or {}).get("description", ""),
            "multi_config_mode": multi_config_mode,
            "schema": schema,
        }

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_entries(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate config entries against their processor implementations.

        Known processors are instantiated and their validate_config() is run
        (the authoritative check, including Python regex compilation). Unknown
        processor names produce a warning, not an error, so files referencing
        them can still be edited and saved.
        """
        errors: List[Dict[str, Any]] = []
        warnings: List[Dict[str, Any]] = []

        for index, entry in enumerate(entries):
            kind = entry["kind"]
            name = entry["name"]
            context = {"entry_index": index, "kind": kind, "name": name}

            try:
                config = self._resolve_entry_config(entry)
            except Exception as e:
                errors.append({**context, "message": f"Invalid config YAML: {e}"})
                continue

            available = (
                AVAILABLE_PREPROCESSORS
                if kind == "preprocessor"
                else AVAILABLE_PROCESSORS
            )
            if name not in available:
                warnings.append(
                    {
                        **context,
                        "message": (
                            f"Unknown {kind} '{name}'; its configuration cannot "
                            f"be validated and will be kept as-is"
                        ),
                    }
                )
                continue

            try:
                loaded_class = load_processor_class(kind, name)  # type: ignore[arg-type]
                instance = loaded_class(config or {})
                if not instance.validate_config():
                    errors.append(
                        {**context, "message": f"Invalid configuration for {name}"}
                    )
            except ValueError as e:
                errors.append({**context, "message": str(e)})

        return {"valid": not errors, "errors": errors, "warnings": warnings}

    def _resolve_entry_config(self, entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Resolve an entry's config, preferring config_yaml when present.

        config_yaml is authoritative because it preserves comments across
        round-trips; the structured form editor clears it after edits.
        """
        config_yaml = entry.get("config_yaml")
        if config_yaml is not None and config_yaml.strip():
            parsed = yaml.safe_load(config_yaml)
            if parsed is not None and not isinstance(parsed, dict):
                raise ValueError("Config must be a YAML mapping")
            return parsed
        config = entry.get("config")
        if config is not None and not isinstance(config, dict):
            raise ValueError("Config must be a mapping")
        return config

    # ------------------------------------------------------------------
    # Per-project config
    # ------------------------------------------------------------------

    def read_config(self, input_path: str) -> Dict[str, Any]:
        """Read (auto-creating if missing) a project's text processor config."""
        config_path = self._project_config_path(input_path, auto_create=True)
        result = self._read_config_file(config_path)
        return result

    def _load_project_chunks(self, input_path: str) -> Tuple[List[Dict], Path]:
        """Load a project's parsed screenplay chunks (and the JSON path)."""
        project_dir = self._validate_project_dir(input_path)
        project_name = project_dir.name
        json_path = project_dir / f"{project_name}.json"
        if not json_path.exists():
            raise ValueError(f"Screenplay JSON does not exist: {json_path}")

        with open(json_path, "r", encoding="utf-8") as f:
            chunks = json.load(f)
        if not isinstance(chunks, list):
            raise ValueError(f"Screenplay JSON is not a chunk list: {json_path}")
        return chunks, json_path

    def _validated_plain_config(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate entries and convert them to a plain config dict.

        Raises:
            ConfigValidationError: If any entry fails validation
        """
        validation = self.validate_entries(entries)
        if not validation["valid"]:
            raise ConfigValidationError(validation["errors"])
        return self._entries_to_plain_config(entries)

    def run_preview_for_project(
        self,
        input_path: str,
        entries: Optional[List[Dict[str, Any]]] = None,
        include_preprocessor_snapshots: bool = False,
        max_changed_chunks: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Run a preview of the pipeline over a project's screenplay chunks.

        Args:
            input_path: Path to the project's input directory
            entries: Draft entries to preview (unsaved edits). When None, the
                configs are resolved exactly as audio generation would resolve
                them (standalone / legacy additive / default)
            include_preprocessor_snapshots: Include per-stage chunk snapshots
            max_changed_chunks: Cap on returned changed chunks (None = all)

        Raises:
            ConfigValidationError: If draft entries fail validation
        """
        chunks, json_path = self._load_project_chunks(input_path)

        if entries is not None:
            draft_config = self._validated_plain_config(entries)
            return run_preview(
                chunks,
                config_dicts=[draft_config],
                include_preprocessor_snapshots=include_preprocessor_snapshots,
                max_changed_chunks=max_changed_chunks,
            )

        config_paths = get_text_processor_configs(json_path, None)
        return run_preview(
            chunks,
            config_paths=config_paths,
            include_preprocessor_snapshots=include_preprocessor_snapshots,
            max_changed_chunks=max_changed_chunks,
        )

    def run_preview_diff_for_project(
        self,
        input_path: str,
        draft_entries: List[Dict[str, Any]],
        baseline_entries: Optional[List[Dict[str, Any]]] = None,
        max_changed_chunks: int = 50,
    ) -> Dict[str, Any]:
        """Diff a draft pipeline against a baseline over a project's chunks.

        Answers "what do these unsaved changes add on top of the saved
        config": only chunks whose final output differs between the two runs
        are reported.

        Args:
            input_path: Path to the project's input directory
            draft_entries: The pipeline including unsaved changes
            baseline_entries: The reference pipeline (typically the editor's
                snapshot of what's on disk). When None, the baseline is
                resolved from disk exactly as audio generation would
            max_changed_chunks: Cap on returned changed chunks

        Raises:
            ConfigValidationError: If draft or baseline entries fail validation
        """
        chunks, json_path = self._load_project_chunks(input_path)
        draft_config = self._validated_plain_config(draft_entries)

        if baseline_entries is not None:
            baseline_config = self._validated_plain_config(baseline_entries)
            return run_preview_diff(
                chunks,
                draft_config_dicts=[draft_config],
                baseline_config_dicts=[baseline_config],
                max_changed_chunks=max_changed_chunks,
            )

        config_paths = get_text_processor_configs(json_path, None)
        return run_preview_diff(
            chunks,
            draft_config_dicts=[draft_config],
            baseline_config_paths=config_paths,
            max_changed_chunks=max_changed_chunks,
        )

    def _entries_to_plain_config(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build a plain config dict (as yaml.safe_load would produce) from entries."""
        config: Dict[str, List[Dict[str, Any]]] = {
            "preprocessors": [],
            "processors": [],
        }
        for entry in entries:
            item: Dict[str, Any] = {"name": entry["name"]}
            entry_config = self._resolve_entry_config(entry)
            if entry_config is not None:
                item["config"] = entry_config
            section = (
                "preprocessors" if entry["kind"] == "preprocessor" else "processors"
            )
            config[section].append(item)
        return config

    def write_config(
        self, input_path: str, entries: List[Dict[str, Any]], base_file_hash: str
    ) -> Dict[str, Any]:
        """Write a project's text processor config from structured entries.

        Raises:
            ConfigConflictError: If the file changed since base_file_hash was read
            ConfigValidationError: If any entry fails validation
        """
        config_path = self._project_config_path(input_path, auto_create=True)

        current_text = config_path.read_text(encoding="utf-8")
        current_hash = _hash_text(current_text)
        if current_hash != base_file_hash:
            raise ConfigConflictError(
                "The config file has been modified by another source. "
                "Please refresh and retry your changes."
            )

        validation = self.validate_entries(entries)
        if not validation["valid"]:
            raise ConfigValidationError(validation["errors"])

        ruamel_yaml = _create_yaml()
        document = ruamel_yaml.load(StringIO(current_text))
        if not isinstance(document, CommentedMap):
            document = CommentedMap()

        self._apply_entries_to_document(document, entries)

        output = StringIO()
        ruamel_yaml.dump(document, output)
        config_path.write_text(output.getvalue(), encoding="utf-8")
        logger.info(f"Wrote text processor config at {config_path}")

        return self._read_config_file(config_path)

    def convert_legacy_to_standalone(self, input_path: str) -> Dict[str, Any]:
        """Convert a legacy additive config into an equivalent standalone config.

        The manager concatenates config entry lists in order before applying
        override filtering, so [shipped default entries] + [legacy entries] is
        semantically identical to the legacy [default, custom] chain.
        """
        config_path = self._project_config_path(input_path, auto_create=True)

        legacy_data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        if (
            isinstance(legacy_data, dict)
            and isinstance(legacy_data.get("sts_metadata"), dict)
            and legacy_data["sts_metadata"].get("mode") == MODE_STANDALONE
        ):
            # Already standalone; nothing to convert
            return self._read_config_file(config_path)

        ruamel_yaml = _create_yaml()
        legacy_document = ruamel_yaml.load(
            StringIO(config_path.read_text(encoding="utf-8"))
        )
        if not isinstance(legacy_document, CommentedMap):
            legacy_document = CommentedMap()

        # Start from a fresh standalone seed of the shipped default, then
        # append the legacy entries after the default ones (chain order)
        seeded_text = seed_config_text("shipped_default")
        merged = ruamel_yaml.load(StringIO(seeded_text))
        for _, section in _SECTIONS:
            legacy_section = legacy_document.get(section)
            if not legacy_section:
                continue
            if section not in merged or merged[section] is None:
                merged[section] = CommentedSeq()
            for item in legacy_section:
                merged[section].append(item)

        output = StringIO()
        ruamel_yaml.dump(merged, output)
        config_path.write_text(output.getvalue(), encoding="utf-8")
        logger.info(f"Converted legacy text processor config at {config_path}")

        return self._read_config_file(config_path)

    def reset_config(self, input_path: str, source: str) -> Dict[str, Any]:
        """Overwrite a project's config by re-seeding from the given source.

        Writes the seed regardless of whether a config already exists, so reset
        also works to (re)create the file for a project that has none yet.
        """
        project_dir = self._validate_project_dir(input_path)
        json_path = str(project_dir / f"{project_dir.name}.json")
        config_path = Path(get_text_processor_config_path(json_path))
        config_text = seed_config_text(source)
        config_path.write_text(config_text, encoding="utf-8")
        logger.info(f"Reset text processor config at {config_path} from {source}")
        return self._read_config_file(config_path)

    # ------------------------------------------------------------------
    # User global default config
    # ------------------------------------------------------------------

    def read_global_default(self) -> Dict[str, Any]:
        """Read the user's global default config, if any."""
        if not USER_DEFAULT_CONFIG_PATH.exists():
            return {
                "exists": False,
                "path": str(USER_DEFAULT_CONFIG_PATH),
                "file_hash": None,
            }
        result = self._read_config_file(USER_DEFAULT_CONFIG_PATH)
        result["exists"] = True
        return result

    def _global_default_hash(self) -> Optional[str]:
        """Current content hash of the global default file, or None if absent."""
        if not USER_DEFAULT_CONFIG_PATH.exists():
            return None
        return _hash_text(USER_DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))

    def _check_global_default_hash(self, base_file_hash: Optional[str]) -> None:
        """Enforce optimistic locking on the global default file.

        The check is opt-in: callers that pass base_file_hash=None (e.g. a
        first-time create) skip it; callers that read the file first pass the
        hash they saw and get a conflict if it changed underneath them.
        """
        if base_file_hash is None:
            return
        if self._global_default_hash() != base_file_hash:
            raise ConfigConflictError(
                "The global default config has been modified by another source. "
                "Please refresh and retry your changes."
            )

    def write_global_default(
        self,
        entries: List[Dict[str, Any]],
        based_on_default_sha256: Optional[str] = None,
        base_file_hash: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Write the user's global default config from structured entries.

        Args:
            entries: Pipeline entries to save
            based_on_default_sha256: Shipped-default hash the content derives
                from (carried from the source config); defaults to the current
                shipped default's hash
            base_file_hash: Content hash the client last read; when provided,
                a mismatch raises ConfigConflictError (optimistic locking)

        Raises:
            ConfigConflictError: If the file changed since base_file_hash was read
            ConfigValidationError: If any entry fails validation
        """
        self._check_global_default_hash(base_file_hash)

        validation = self.validate_entries(entries)
        if not validation["valid"]:
            raise ConfigValidationError(validation["errors"])

        document = CommentedMap()
        document["sts_metadata"] = CommentedMap(
            {
                "mode": MODE_USER_DEFAULT,
                "seeded_by_version": __version__,
                "default_config_sha256": (
                    based_on_default_sha256 or get_current_default_hash()
                ),
            }
        )
        document.yaml_set_comment_before_after_key(
            "sts_metadata",
            before=(
                "User default text processor configuration.\n"
                "Used to seed the config of newly parsed screenplays instead "
                "of the built-in defaults."
            ),
        )
        self._apply_entries_to_document(document, entries)

        USER_DEFAULT_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        ruamel_yaml = _create_yaml()
        output = StringIO()
        ruamel_yaml.dump(document, output)
        USER_DEFAULT_CONFIG_PATH.write_text(output.getvalue(), encoding="utf-8")
        logger.info(f"Wrote user default text processor config")

        return self.read_global_default()

    def delete_global_default(
        self, base_file_hash: Optional[str] = None
    ) -> Dict[str, Any]:
        """Delete the user's global default config, reverting to shipped defaults.

        Raises:
            ConfigConflictError: If base_file_hash is provided and the file
                changed since it was read
        """
        self._check_global_default_hash(base_file_hash)
        if USER_DEFAULT_CONFIG_PATH.exists():
            USER_DEFAULT_CONFIG_PATH.unlink()
            logger.info("Deleted user default text processor config")
        return {
            "exists": False,
            "path": str(USER_DEFAULT_CONFIG_PATH),
            "file_hash": None,
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _validate_project_dir(self, input_path: str) -> Path:
        """Resolve and validate a project input directory path."""
        try:
            resolved = Path(input_path).resolve()
            resolved.relative_to(self.input_dir.resolve())
        except ValueError:
            raise ValueError(
                f"Path {input_path} is outside the workspace input directory"
            )

        if not resolved.exists() or not resolved.is_dir():
            raise ValueError(f"Project directory does not exist: {input_path}")
        return resolved

    def _project_config_path(self, input_path: str, auto_create: bool) -> Path:
        """Get a project's config path, optionally auto-creating the file."""
        project_dir = self._validate_project_dir(input_path)
        project_name = project_dir.name
        json_path = str(project_dir / f"{project_name}.json")

        if auto_create:
            generate_text_processor_config(json_path)

        config_path = Path(get_text_processor_config_path(json_path))
        if not config_path.exists():
            raise ValueError(f"Text processor config does not exist: {config_path}")
        return config_path

    def _read_config_file(self, config_path: Path) -> Dict[str, Any]:
        """Parse a config file into the structured response shape."""
        text = config_path.read_text(encoding="utf-8")
        file_hash = _hash_text(text)

        data = yaml.safe_load(text)
        if data is None:
            data = {}
        if not isinstance(data, dict):
            raise ValueError(f"Config at {config_path} is not a YAML mapping")

        ruamel_yaml = _create_yaml()
        document = ruamel_yaml.load(StringIO(text))
        if not isinstance(document, CommentedMap):
            document = CommentedMap()

        metadata = data.get("sts_metadata")
        if not isinstance(metadata, dict):
            metadata = None

        entries = []
        for kind, section in _SECTIONS:
            plain_items = data.get(section) or []
            ruamel_items = document.get(section) or []
            for index, plain_item in enumerate(plain_items):
                if not isinstance(plain_item, dict) or "name" not in plain_item:
                    raise ValueError(
                        f"Malformed {section} entry at index {index} in {config_path}"
                    )
                name = plain_item["name"]
                available = (
                    AVAILABLE_PREPROCESSORS
                    if kind == "preprocessor"
                    else AVAILABLE_PROCESSORS
                )

                config_yaml = ""
                ruamel_config = None
                if index < len(ruamel_items) and isinstance(ruamel_items[index], dict):
                    ruamel_config = ruamel_items[index].get("config")
                if ruamel_config is not None:
                    snippet = StringIO()
                    ruamel_yaml.dump(ruamel_config, snippet)
                    config_yaml = snippet.getvalue()

                entries.append(
                    {
                        "id": f"{kind}-{index}",
                        "kind": kind,
                        "name": name,
                        "known": name in available,
                        "config": plain_item.get("config"),
                        "config_yaml": config_yaml,
                    }
                )

        mode = (metadata or {}).get("mode")
        return {
            "path": str(config_path),
            "yaml_text": text,
            "file_hash": file_hash,
            "entries": entries,
            "metadata": metadata,
            "stale": is_config_stale(data),
            "is_legacy_additive": mode != MODE_STANDALONE and mode != MODE_USER_DEFAULT,
            "current_default_hash": get_current_default_hash(),
        }

    def _apply_entries_to_document(
        self, document: CommentedMap, entries: List[Dict[str, Any]]
    ) -> None:
        """Rebuild the document's preprocessors/processors sections from entries."""
        ruamel_yaml = _create_yaml()
        sections: Dict[str, CommentedSeq] = {
            "preprocessors": CommentedSeq(),
            "processors": CommentedSeq(),
        }

        for entry in entries:
            node = CommentedMap()
            node["name"] = entry["name"]

            config_yaml = entry.get("config_yaml")
            config = entry.get("config")
            if config_yaml is not None and config_yaml.strip():
                # config_yaml is authoritative: ruamel round-trip preserves
                # comments for entries the form editor didn't touch
                node["config"] = ruamel_yaml.load(StringIO(config_yaml))
            elif config is not None:
                node["config"] = config

            section = (
                "preprocessors" if entry["kind"] == "preprocessor" else "processors"
            )
            sections[section].append(node)

        for section, seq in sections.items():
            document[section] = seq


def _hash_text(text: str) -> str:
    """Hash file text for optimistic-locking version tokens."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# Global service instance
text_processor_config_service = TextProcessorConfigService()
