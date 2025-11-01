"""Project discovery and status service."""

import json
import logging
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from ..config import settings
from ..models import ProjectMeta, ProjectStatus

logger = logging.getLogger(__name__)


class ProjectService:
    """Service for project discovery and status checking."""

    def __init__(self) -> None:
        """Initialize the project service."""
        # Use absolute paths from the project root
        self.project_root = Path.cwd()
        self.input_dir = self.project_root / "input"
        self.output_dir = self.project_root / "output"
        self.source_screenplays_dir = self.project_root / "source_screenplays"

        # Ensure directories exist
        self.input_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
        self.source_screenplays_dir.mkdir(exist_ok=True)

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

    def create_new_project_from_upload(self, source_file_path: str) -> Dict[str, str]:
        """Create a new project from an uploaded screenplay file.

        Args:
            source_file_path: Path to the uploaded screenplay file

        Returns:
            Dictionary with project metadata (inputPath, outputPath, screenplayName)

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

            # Generate screenplay name from filename
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

            # Run CLI parser
            try:
                self._run_cli_parser(target_path)
            except Exception as e:
                # Clean up on failure
                if target_path.exists():
                    target_path.unlink()
                raise RuntimeError(f"Failed to parse screenplay: {str(e)}")

            # Create output directory
            output_project_dir = self.output_dir / screenplay_name
            output_project_dir.mkdir(parents=True, exist_ok=True)

            # Return project metadata
            return {
                "inputPath": str(input_project_dir),
                "outputPath": str(output_project_dir),
                "screenplayName": screenplay_name,
            }

        except Exception as e:
            logger.error(f"Failed to create project from {source_file_path}: {e}")
            raise

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for use as project name.

        Args:
            filename: Raw filename to sanitize

        Returns:
            Sanitized filename safe for filesystem use
        """
        # Remove or replace invalid characters
        import re

        # Keep alphanumeric, spaces, hyphens, underscores
        sanitized = re.sub(r"[^\w\s-]", "", filename)
        # Replace spaces with underscores
        sanitized = re.sub(r"\s+", "_", sanitized.strip())
        # Remove leading/trailing underscores and limit length
        sanitized = sanitized.strip("_")[:50]
        return sanitized

    def _run_cli_parser(self, screenplay_path: Path) -> None:
        """Run the CLI screenplay parser.

        Args:
            screenplay_path: Path to the screenplay file to parse

        Raises:
            RuntimeError: If parsing fails
        """
        try:
            # Run the CLI parser
            cmd = ["uv", "run", "sts-parse-screenplay", str(screenplay_path)]

            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            if result.returncode != 0:
                error_msg = f"CLI parser failed with exit code {result.returncode}"
                if result.stderr:
                    error_msg += f": {result.stderr}"
                raise RuntimeError(error_msg)

            logger.info(f"Successfully parsed screenplay: {screenplay_path}")

            if result.stdout:
                logger.debug(f"Parser output: {result.stdout}")

        except subprocess.TimeoutExpired:
            raise RuntimeError("Screenplay parsing timed out after 5 minutes")
        except Exception as e:
            raise RuntimeError(f"Failed to run CLI parser: {str(e)}")


# Create service instance
project_service = ProjectService()
