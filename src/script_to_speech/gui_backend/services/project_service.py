"""Project discovery and status service."""

import json
import logging
import math
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from script_to_speech.parser.header_footer.detector import HeaderFooterDetector

from ..config import settings
from ..models import (
    AUTO_APPLY_THRESHOLD,
    SUGGESTION_THRESHOLD,
    DetectedPatternResponse,
    ProjectMeta,
    ProjectStatus,
)

logger = logging.getLogger(__name__)


class ProjectService:
    """Service for project discovery and status checking."""

    def __init__(self, workspace_dir: Optional[Path] = None) -> None:
        """Initialize the project service.

        Args:
            workspace_dir: Root directory for project workspace. If None, uses settings.WORKSPACE_DIR.
        """
        # Use provided workspace_dir or fall back to settings
        if workspace_dir is None:
            workspace_dir = settings.WORKSPACE_DIR

        if workspace_dir is None:
            raise ValueError(
                "Workspace directory is not configured. Set STS_WORKSPACE_DIR environment variable."
            )

        self.workspace_dir = Path(workspace_dir)
        self.input_dir = self.workspace_dir / "input"
        self.output_dir = self.workspace_dir / "output"
        self.source_screenplays_dir = self.workspace_dir / "source_screenplays"

        # Ensure directories exist
        try:
            self.input_dir.mkdir(parents=True, exist_ok=True)
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self.source_screenplays_dir.mkdir(parents=True, exist_ok=True)
        except (PermissionError, OSError) as e:
            logger.error(
                f"Failed to create workspace directories at {self.workspace_dir}: {e}"
            )
            raise

    def _validate_path_security(self, path: str) -> Path:
        """Validate and resolve path to prevent directory traversal attacks.

        Args:
            path: The path to validate

        Returns:
            Resolved Path object

        Raises:
            ValueError: If path is outside allowed directories
        """
        try:
            # Convert to Path and resolve
            resolved_path = Path(path).resolve()

            # Check if path is within allowed workspace directories
            allowed_parents = [
                self.input_dir.resolve(),
                self.output_dir.resolve(),
                self.source_screenplays_dir.resolve(),
            ]

            # Check if resolved path is within any allowed parent directory
            for allowed_parent in allowed_parents:
                try:
                    resolved_path.relative_to(allowed_parent)
                    return resolved_path
                except ValueError:
                    continue

            # If we get here, path is not within any allowed directory
            raise ValueError(f"Path {path} is outside allowed workspace directories")

        except Exception as e:
            logger.warning(f"Path validation failed for {path}: {e}")
            raise ValueError(f"Invalid path: {path}")

    def discover_projects(
        self, limit: int = 100, cursor: Optional[str] = None
    ) -> List[ProjectMeta]:
        """Discover existing projects in the input directory.

        Args:
            limit: Maximum number of projects to return
            cursor: Optional cursor for pagination (not implemented yet)

        Returns:
            List of discovered projects sorted by last modified date (descending)
        """
        try:
            projects: List[ProjectMeta] = []

            if not self.input_dir.exists():
                logger.info(
                    "Input directory does not exist, returning empty project list"
                )
                return projects

            # Scan all subdirectories in input/
            for project_dir in self.input_dir.iterdir():
                if not project_dir.is_dir():
                    continue

                try:
                    project_name = project_dir.name

                    # Skip hidden directories and system directories
                    if project_name.startswith("."):
                        continue

                    # Check for key files to determine if this is a valid project
                    json_file = project_dir / f"{project_name}.json"
                    voice_config_file = (
                        project_dir / f"{project_name}_voice_config.yaml"
                    )

                    # At minimum, we need either a JSON file or voice config to consider it a project
                    has_json = json_file.exists()
                    has_voice_config = voice_config_file.exists()

                    if not (has_json or has_voice_config):
                        continue

                    # Get last modified time (use the most recent file in the directory)
                    last_modified_time = project_dir.stat().st_mtime
                    for file_path in project_dir.iterdir():
                        if file_path.is_file():
                            file_mtime = file_path.stat().st_mtime
                            last_modified_time = max(last_modified_time, file_mtime)

                    last_modified = datetime.fromtimestamp(
                        last_modified_time, tz=timezone.utc
                    ).isoformat()

                    # Determine output path
                    output_path = str(self.output_dir / project_name)

                    project_meta = ProjectMeta(
                        name=project_name,
                        input_path=str(project_dir),
                        output_path=output_path,
                        has_json=has_json,
                        has_voice_config=has_voice_config,
                        last_modified=last_modified,
                    )

                    projects.append(project_meta)

                except Exception as e:
                    logger.warning(
                        f"Error processing project directory {project_dir}: {e}"
                    )
                    continue

            # Sort by last modified date (descending - most recent first)
            projects.sort(key=lambda p: p.last_modified, reverse=True)

            # Apply limit
            if limit and len(projects) > limit:
                projects = projects[:limit]

            logger.info(f"Discovered {len(projects)} projects")
            return projects

        except Exception as e:
            logger.error(f"Error discovering projects: {e}")
            raise

    def get_project_status(self, input_path: str) -> ProjectStatus:
        """Get detailed status for a specific project.

        Args:
            input_path: Path to the project's input directory

        Returns:
            ProjectStatus with detailed file existence and metadata

        Raises:
            ValueError: If project path is invalid or doesn't exist
        """
        try:
            # Validate and resolve the input path
            project_dir = self._validate_path_security(input_path)

            if not project_dir.exists():
                raise ValueError(f"Project directory does not exist: {input_path}")

            if not project_dir.is_dir():
                raise ValueError(f"Project path is not a directory: {input_path}")

            project_name = project_dir.name

            # Check file existence
            pdf_file = project_dir / f"{project_name}.pdf"
            json_file = project_dir / f"{project_name}.json"
            voice_config_file = project_dir / f"{project_name}_voice_config.yaml"
            optional_config_file = project_dir / f"{project_name}_optional_config.yaml"

            # Check output directory
            output_project_dir = self.output_dir / project_name
            output_mp3_file = output_project_dir / f"{project_name}.mp3"

            has_pdf = pdf_file.exists()
            has_json = json_file.exists()
            has_voice_config = voice_config_file.exists()
            has_optional_config = optional_config_file.exists()
            has_output_mp3 = output_mp3_file.exists()

            # Derived states
            screenplay_parsed = has_json
            audio_generated = has_output_mp3

            # Initialize metadata
            speaker_count = None
            dialogue_chunks = None
            voices_assigned = None
            json_error = None
            voice_config_error = None

            # Parse JSON file for metadata if it exists
            if has_json:
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        json_data = json.load(f)

                    # Count dialogue chunks
                    if isinstance(json_data, list):
                        dialogue_chunks = len(json_data)

                        # Extract unique speakers
                        speakers = set()
                        for chunk in json_data:
                            if isinstance(chunk, dict) and "speaker" in chunk:
                                speakers.add(chunk["speaker"])
                        speaker_count = len(speakers)

                except json.JSONDecodeError as e:
                    json_error = f"JSON parse error: {str(e)}"
                    logger.warning(f"JSON parse error in {json_file}: {e}")
                except Exception as e:
                    json_error = f"Error reading JSON file: {str(e)}"
                    logger.warning(f"Error reading JSON file {json_file}: {e}")

            # Parse voice config file for metadata if it exists
            voices_cast = False
            if has_voice_config:
                try:
                    with open(voice_config_file, "r", encoding="utf-8") as f:
                        voice_config = yaml.safe_load(f)

                    # Count assigned voices
                    if isinstance(voice_config, dict):
                        # Count speakers with assigned voices
                        assigned_count = 0
                        for speaker, config in voice_config.items():
                            if isinstance(config, dict) and config.get("provider"):
                                # Consider assigned if has provider and either sts_id or custom config
                                if config.get("sts_id") or len(config) > 1:
                                    assigned_count += 1

                        voices_assigned = assigned_count
                        voices_cast = assigned_count > 0

                except yaml.YAMLError as e:
                    voice_config_error = f"YAML parse error: {str(e)}"
                    logger.warning(f"YAML parse error in {voice_config_file}: {e}")
                except Exception as e:
                    voice_config_error = f"Error reading voice config file: {str(e)}"
                    logger.warning(
                        f"Error reading voice config file {voice_config_file}: {e}"
                    )

            status = ProjectStatus(
                has_pdf=has_pdf,
                has_json=has_json,
                has_voice_config=has_voice_config,
                has_optional_config=has_optional_config,
                has_output_mp3=has_output_mp3,
                screenplay_parsed=screenplay_parsed,
                voices_cast=voices_cast,
                audio_generated=audio_generated,
                speaker_count=speaker_count,
                dialogue_chunks=dialogue_chunks,
                voices_assigned=voices_assigned,
                json_error=json_error,
                voice_config_error=voice_config_error,
            )

            logger.debug(f"Project status for {project_name}: {status}")
            return status

        except Exception as e:
            logger.error(f"Error getting project status for {input_path}: {e}")
            raise

    def create_new_project_from_upload(
        self, source_file_path: str, original_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new project from an uploaded screenplay file.

        For PDF files, this will:
        1. Run header/footer detection with 20% threshold
        2. Auto-apply removal for patterns >= 40%
        3. Return detection metadata for popover display

        Args:
            source_file_path: Path to the uploaded screenplay file
            original_filename: Original filename from the upload (optional, if not provided uses source_file_path)

        Returns:
            Dictionary with project metadata including:
            - inputPath, outputPath, screenplayName
            - autoRemovedPatterns: patterns that were auto-removed (>= 40%)
            - suggestedPatterns: patterns that are suggestions (20-40%)

        Raises:
            ValueError: If file is invalid or project creation fails
            RuntimeError: If CLI parsing fails
        """
        try:
            source_path = Path(source_file_path)
            if not source_path.exists():
                raise ValueError(f"Source file does not exist: {source_file_path}")

            # Validate file type
            if not source_path.suffix.lower() in [".pdf", ".txt"]:
                raise ValueError(
                    f"Invalid file type. Only PDF and TXT files are allowed."
                )

            # Generate screenplay name from original filename if provided, otherwise from temp file
            if original_filename:
                screenplay_name = self._sanitize_filename(Path(original_filename).stem)
            else:
                screenplay_name = self._sanitize_filename(source_path.stem)
            if not screenplay_name:
                raise ValueError("Invalid filename - cannot generate project name")

            # Check for duplicate project
            input_project_dir = self.input_dir / screenplay_name
            if input_project_dir.exists():
                # Generate unique name
                counter = 1
                while (self.input_dir / f"{screenplay_name}_{counter}").exists():
                    counter += 1
                screenplay_name = f"{screenplay_name}_{counter}"
                input_project_dir = self.input_dir / screenplay_name

            # Copy file to source_screenplays directory
            target_filename = f"{screenplay_name}{source_path.suffix}"
            target_path = self.source_screenplays_dir / target_filename

            # Copy the file
            import shutil

            shutil.copy2(source_path, target_path)
            logger.info(f"Copied {source_path} to {target_path}")

            # Initialize detection results
            auto_removed_patterns: List[DetectedPatternResponse] = []
            suggested_patterns: List[DetectedPatternResponse] = []
            strings_to_remove: List[str] = []

            # Run header/footer detection for PDFs
            if source_path.suffix.lower() == ".pdf":
                try:
                    detection_result = self._detect_headers_footers(target_path)
                    auto_removed_patterns = detection_result["auto_removed"]
                    suggested_patterns = detection_result["suggested"]
                    strings_to_remove = detection_result["strings_to_remove"]

                    if strings_to_remove:
                        logger.info(
                            f"Auto-removing {len(strings_to_remove)} header/footer patterns"
                        )
                except Exception as e:
                    # Log but don't fail - detection is optional
                    logger.warning(
                        f"Header/footer detection failed, continuing without: {e}"
                    )

            # Run CLI parser with auto-removal patterns
            try:
                self._run_cli_parser(
                    target_path,
                    strings_to_remove=strings_to_remove if strings_to_remove else None,
                    remove_lines=2,
                )
            except Exception as e:
                # Clean up on failure
                if target_path.exists():
                    target_path.unlink()
                raise RuntimeError(f"Failed to parse screenplay: {str(e)}")

            # Create output directory
            output_project_dir = self.output_dir / screenplay_name
            output_project_dir.mkdir(parents=True, exist_ok=True)

            # Return project metadata with detection results
            # Use by_alias=True to serialize with camelCase for frontend compatibility
            return {
                "inputPath": str(input_project_dir),
                "outputPath": str(output_project_dir),
                "screenplayName": screenplay_name,
                "autoRemovedPatterns": [
                    p.model_dump(by_alias=True) for p in auto_removed_patterns
                ],
                "suggestedPatterns": [
                    p.model_dump(by_alias=True) for p in suggested_patterns
                ],
            }

        except Exception as e:
            logger.error(f"Failed to create project from {source_file_path}: {e}")
            raise

    def _detect_headers_footers(self, pdf_path: Path) -> Dict[str, Any]:
        """Detect header/footer patterns in a PDF.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Dictionary with:
            - auto_removed: patterns >= 40% (to be auto-removed)
            - suggested: patterns 20-40% (suggestions)
            - strings_to_remove: list of pattern texts to remove
        """
        # Create detector with lenient threshold for suggestions
        # Use adjusted min_occurrences for short scripts
        detector = HeaderFooterDetector(
            lines_to_scan=2,
            min_occurrences=2,  # Start low, we'll filter by percentage
        )
        result = detector.detect(str(pdf_path))

        # Adjust min_occurrences based on page count
        if result.total_pages > 0:
            adjusted_min = max(2, math.floor(result.total_pages * 0.15))
            if adjusted_min > 2:
                # Re-run with adjusted min if needed
                detector = HeaderFooterDetector(
                    lines_to_scan=2,
                    min_occurrences=adjusted_min,
                )
                result = detector.detect(str(pdf_path))

        auto_removed: List[DetectedPatternResponse] = []
        suggested: List[DetectedPatternResponse] = []
        strings_to_remove: List[str] = []

        for pattern in result.patterns:
            # Skip blacklisted patterns for auto-removal
            if pattern.is_blacklisted:
                continue

            # Skip patterns below suggestion threshold
            if pattern.occurrence_percentage < SUGGESTION_THRESHOLD:
                continue

            # Create response object
            pattern_response = DetectedPatternResponse(
                text=pattern.text,
                position=pattern.position.value,
                occurrence_count=pattern.occurrence_count,
                total_pages=pattern.total_pages,
                occurrence_percentage=pattern.occurrence_percentage,
                is_blacklisted=pattern.is_blacklisted,
                example_full_lines=pattern.example_full_lines[:3],
                variations=pattern.variations,
                is_auto_applied=pattern.occurrence_percentage >= AUTO_APPLY_THRESHOLD,
                is_suggestion=(
                    SUGGESTION_THRESHOLD
                    <= pattern.occurrence_percentage
                    < AUTO_APPLY_THRESHOLD
                ),
            )

            if pattern.occurrence_percentage >= AUTO_APPLY_THRESHOLD:
                auto_removed.append(pattern_response)
                # Use variations if available (they include page numbers etc.)
                if pattern.variations:
                    strings_to_remove.extend(pattern.variations)
                else:
                    strings_to_remove.append(pattern.text)
            elif pattern.occurrence_percentage >= SUGGESTION_THRESHOLD:
                suggested.append(pattern_response)

        return {
            "auto_removed": auto_removed,
            "suggested": suggested,
            "strings_to_remove": strings_to_remove,
        }

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for use as project name.

        Args:
            filename: Raw filename to sanitize

        Returns:
            Sanitized filename safe for filesystem use
        """
        # Use pathvalidate for consistent sanitization with CLI
        from pathvalidate import sanitize_filename

        sanitized = sanitize_filename(filename)
        # Limit length for practicality
        return str(sanitized[:200]) if sanitized else ""

    def _run_cli_parser(
        self,
        screenplay_path: Path,
        strings_to_remove: Optional[List[str]] = None,
        remove_lines: int = 2,
    ) -> Dict[str, Any]:
        """Run the screenplay parser directly.

        Args:
            screenplay_path: Path to the screenplay file to parse
            strings_to_remove: Optional list of header/footer patterns to remove
            remove_lines: Number of lines from top/bottom to check for removal

        Returns:
            Parser result dictionary

        Raises:
            RuntimeError: If parsing fails
        """
        try:
            # Import parser function directly
            from script_to_speech.parser.process import process_screenplay

            # Call parser function with workspace as base_path
            result = process_screenplay(
                input_file=str(screenplay_path),
                base_path=self.workspace_dir,
                text_only=False,
                strings_to_remove=strings_to_remove,
                remove_lines=remove_lines,
            )

            logger.info(f"Successfully parsed screenplay: {screenplay_path}")
            logger.debug(f"Parser result: {result}")

            return result

        except Exception as e:
            error_msg = f"Screenplay parsing failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg)

    def get_id3_tag_config(self, input_path: str) -> Dict[str, str]:
        """Get ID3 tag configuration for a project.

        Args:
            input_path: Path to the project's input directory

        Returns:
            Dictionary with id3 tag config fields (title, screenplay_author, date)
        """
        project_dir = self._validate_path_security(input_path)
        if not project_dir.exists() or not project_dir.is_dir():
            raise ValueError(f"Project directory does not exist: {input_path}")

        project_name = project_dir.name
        json_path = str(project_dir / f"{project_name}.json")

        # Auto-create optional config if missing
        from script_to_speech.utils.optional_config_generation import (
            generate_optional_config,
            get_optional_config_path,
        )

        generate_optional_config(json_path)
        config_path = get_optional_config_path(json_path)

        # Read the YAML config
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

        id3_config = config.get("id3_tag_config", {})
        return {
            "title": id3_config.get("title", ""),
            "screenplay_author": id3_config.get("screenplay_author", ""),
            "date": id3_config.get("date", ""),
        }

    def update_id3_tag_config(
        self, input_path: str, updates: Dict[str, Optional[str]]
    ) -> Dict[str, str]:
        """Update ID3 tag configuration for a project.

        Args:
            input_path: Path to the project's input directory
            updates: Dictionary of fields to update (only non-None values are applied)

        Returns:
            Full updated id3 tag config dictionary
        """
        project_dir = self._validate_path_security(input_path)
        if not project_dir.exists() or not project_dir.is_dir():
            raise ValueError(f"Project directory does not exist: {input_path}")

        project_name = project_dir.name
        json_path = str(project_dir / f"{project_name}.json")

        from script_to_speech.utils.optional_config_generation import (
            generate_optional_config,
            get_optional_config_path,
            write_config_file,
        )

        generate_optional_config(json_path)
        config_path = get_optional_config_path(json_path)

        # Read existing config
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

        if "id3_tag_config" not in config:
            config["id3_tag_config"] = {"title": "", "screenplay_author": "", "date": ""}

        # Apply only non-None updates
        for key, value in updates.items():
            if value is not None:
                config["id3_tag_config"][key] = value

        # Write back
        write_config_file(config_path, config)

        return {
            "title": config["id3_tag_config"].get("title", ""),
            "screenplay_author": config["id3_tag_config"].get("screenplay_author", ""),
            "date": config["id3_tag_config"].get("date", ""),
        }


# Create service instance
project_service = ProjectService()
