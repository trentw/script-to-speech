"""Voice casting service implementation."""

import asyncio
import json
import os
import tempfile
import uuid
from datetime import datetime
from io import StringIO
from pathlib import Path

# Import these types directly to avoid circular imports
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.constructor import DuplicateKeyError

from script_to_speech.tts_providers.base.exceptions import VoiceNotFoundError
from script_to_speech.tts_providers.tts_provider_manager import TTSProviderManager
from script_to_speech.utils.dialogue_stats_utils import get_speaker_statistics
from script_to_speech.utils.file_system_utils import PathSecurityValidator
from script_to_speech.utils.logging import get_screenplay_logger
from script_to_speech.voice_casting.character_notes_utils import (
    generate_voice_casting_prompt_file,
)
from script_to_speech.voice_casting.voice_library_casting_utils import (
    generate_voice_library_casting_prompt_file,
)
from script_to_speech.voice_library.voice_library import VoiceLibrary

from ..config import settings


class VoiceCastingSession(BaseModel):
    """Voice casting session data."""

    session_id: str
    screenplay_json_path: str
    screenplay_name: str
    screenplay_source_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    status: str = "active"  # active, completed, expired


class CharacterInfo(BaseModel):
    """Information about a character from screenplay."""

    name: str
    line_count: int
    total_characters: int
    longest_dialogue: int
    casting_notes: Optional[str] = None
    role: Optional[str] = None


class ExtractCharactersResponse(BaseModel):
    """Response with extracted character information."""

    characters: List[CharacterInfo]
    total_lines: int
    default_lines: int


class ValidateYamlResponse(BaseModel):
    """Response from YAML validation."""

    is_valid: bool
    missing_speakers: List[str] = Field(default_factory=list)
    extra_speakers: List[str] = Field(default_factory=list)
    duplicate_speakers: List[str] = Field(default_factory=list)
    invalid_configs: Dict[str, str] = Field(default_factory=dict)
    message: str


class VoiceAssignment(BaseModel):
    """Voice assignment for a character."""

    character: str
    provider: str
    sts_id: str = ""  # Primary field, may be empty
    casting_notes: Optional[str] = None
    role: Optional[str] = None
    provider_config: Optional[Dict[str, Any]] = None
    additional_notes: Optional[List[str]] = None
    # Character stats from comments (parsed but not stored in YAML)
    line_count: Optional[int] = None
    total_characters: Optional[int] = None
    longest_dialogue: Optional[int] = None

    class Config:
        populate_by_name = True


class GenerateYamlResponse(BaseModel):
    """Response with generated YAML content."""

    yaml_content: str


class ParseYamlResponse(BaseModel):
    """Response with parsed voice assignments."""

    assignments: List[VoiceAssignment]
    has_errors: bool = False
    errors: List[str] = Field(default_factory=list)


class GenerateCharacterNotesPromptResponse(BaseModel):
    """Response with generated character notes prompt."""

    prompt_content: str
    privacy_notice: str


class GenerateVoiceLibraryPromptResponse(BaseModel):
    """Response with generated voice library prompt."""

    prompt_content: str
    privacy_notice: str


# Constants for YAML comment parsing
YAML_COMMENT_PATTERNS = {
    "LINE_COUNT": r"#\s*(\w+):\s*(\d+)\s*lines?",
    "CHAR_STATS": r"#\s*Total characters:\s*(\d+),\s*Longest dialogue:\s*(\d+)\s*characters",
    "CASTING_NOTES": r"#\s*(?:casting\s*notes?|CASTING\s*NOTES?)\s*[:=\-]?\s*(.+)",
    "ROLE": r"#\s*(?:role|ROLE)\s*[:=\-]?\s*(.+)",
}

logger = get_screenplay_logger("voice_casting_service")


class VoiceCastingService:
    """Service for voice casting operations."""

    def __init__(self) -> None:
        """Initialize the voice casting service."""
        self._voice_library = VoiceLibrary()
        self._sessions: Dict[str, VoiceCastingSession] = {}  # In-memory session storage
        # Initialize path validator for secure file access
        self._path_validator = PathSecurityValidator(settings.STS_ROOT_DIR)

    async def extract_characters(
        self, screenplay_json_path: str
    ) -> ExtractCharactersResponse:
        """
        Extract character information from screenplay JSON file.

        Args:
            screenplay_json_path: Path to screenplay JSON file

        Returns:
            ExtractCharactersResponse with character information
        """
        # Validate and resolve path to prevent traversal attacks
        try:
            safe_path = self._path_validator.validate_existing_path(
                Path(screenplay_json_path)
            )
        except ValueError as e:
            raise ValueError(f"Invalid screenplay path: {e}")

        # Load JSON from file
        with open(safe_path, "r", encoding="utf-8") as f:
            screenplay_json = json.load(f)

        # Get speaker statistics using existing utility
        speaker_stats = get_speaker_statistics(screenplay_json)

        characters = []
        total_lines = 0
        default_lines = 0

        # Convert stats to CharacterInfo objects
        for speaker_name, stats in speaker_stats.items():
            character_info = CharacterInfo(
                name=speaker_name,
                line_count=stats.line_count,
                total_characters=stats.total_characters,
                longest_dialogue=stats.longest_dialogue,
            )
            characters.append(character_info)

            total_lines += stats.line_count
            if speaker_name == "default":
                default_lines = stats.line_count

        # Sort characters: default first, then by line count descending
        characters.sort(key=lambda c: (c.name != "default", -c.line_count, c.name))

        return ExtractCharactersResponse(
            characters=characters, total_lines=total_lines, default_lines=default_lines
        )

    async def validate_yaml(
        self, yaml_content: str, screenplay_json_path: str
    ) -> ValidateYamlResponse:
        """
        Validate YAML configuration against screenplay characters.

        Args:
            yaml_content: YAML configuration content
            screenplay_json_path: Path to screenplay JSON file

        Returns:
            ValidateYamlResponse with validation results
        """
        # Validate and resolve path to prevent traversal attacks
        try:
            safe_path = self._path_validator.validate_existing_path(
                Path(screenplay_json_path)
            )
        except ValueError as e:
            raise ValueError(f"Invalid screenplay path: {e}")

        # Load JSON from file
        with open(safe_path, "r", encoding="utf-8") as f:
            screenplay_json = json.load(f)

        # Extract speakers from screenplay
        speaker_stats = get_speaker_statistics(screenplay_json)
        speakers_in_script = set(speaker_stats.keys())

        # Parse YAML and check for duplicates
        yaml = YAML(typ="safe")
        yaml.allow_duplicate_keys = False
        duplicate_speakers: List[str] = []
        yaml_data = None

        try:
            yaml_data = yaml.load(StringIO(yaml_content))
        except DuplicateKeyError as e:
            # Extract duplicate key from error
            error_msg = str(e)
            import re

            duplicate_key_match = re.search(r'found duplicate key "([^"]+)"', error_msg)
            if duplicate_key_match:
                duplicate_speakers.append(duplicate_key_match.group(1))

            # Try to load with duplicates allowed to continue validation
            yaml.allow_duplicate_keys = True
            yaml_data = yaml.load(StringIO(yaml_content))

        if not isinstance(yaml_data, dict):
            return ValidateYamlResponse(
                is_valid=False,
                message="YAML must be a mapping of speakers to voice configurations",
            )

        speakers_in_yaml = set(yaml_data.keys())

        # Find missing and extra speakers
        missing_speakers = sorted(speakers_in_script - speakers_in_yaml)
        extra_speakers = sorted(speakers_in_yaml - speakers_in_script)

        # Validate provider configurations
        invalid_configs = {}
        for speaker, config in yaml_data.items():
            if not isinstance(config, dict):
                invalid_configs[speaker] = "Configuration must be a mapping/dictionary"
                continue

            provider_name = config.get("provider")
            if not provider_name:
                invalid_configs[speaker] = "Missing required 'provider' field"
                continue

            try:
                provider_class = TTSProviderManager._get_provider_class(provider_name)

                # Create a copy of the config for validation
                validation_config = config.copy()

                # Check for sts_id and expand config if present (like TTSProviderManager does)
                if "sts_id" in validation_config:
                    sts_id = validation_config.pop(
                        "sts_id"
                    )  # Remove sts_id from config

                    try:
                        # Get expansion from voice library
                        expanded_config = self._voice_library.expand_config(
                            provider_name, sts_id
                        )

                        # Merge: expanded config first, then user overrides
                        final_config = {**expanded_config, **validation_config}
                        validation_config = final_config

                    except VoiceNotFoundError as ve:
                        invalid_configs[speaker] = (
                            f"Invalid sts_id '{sts_id}': {str(ve)}"
                        )
                        continue
                    except Exception as ve:
                        invalid_configs[speaker] = (
                            f"Failed to expand sts_id '{sts_id}': {str(ve)}"
                        )
                        continue

                # Validate the (possibly expanded) config
                provider_class.validate_speaker_config(validation_config)

            except Exception as e:
                invalid_configs[speaker] = str(e)

        # Determine if valid
        is_valid = not any(
            [missing_speakers, extra_speakers, duplicate_speakers, invalid_configs]
        )

        # Create message
        if is_valid:
            message = "YAML configuration is valid"
        else:
            issues = []
            if missing_speakers:
                issues.append(f"Missing speakers: {', '.join(missing_speakers)}")
            if extra_speakers:
                issues.append(f"Extra speakers: {', '.join(extra_speakers)}")
            if duplicate_speakers:
                issues.append(f"Duplicate speakers: {', '.join(duplicate_speakers)}")
            if invalid_configs:
                issues.append(f"Invalid configurations: {len(invalid_configs)}")
            message = "Validation failed: " + "; ".join(issues)

        return ValidateYamlResponse(
            is_valid=is_valid,
            missing_speakers=missing_speakers,
            extra_speakers=extra_speakers,
            duplicate_speakers=duplicate_speakers,
            invalid_configs=invalid_configs,
            message=message,
        )

    async def generate_yaml(
        self,
        assignments: List[VoiceAssignment],
        character_info: List[CharacterInfo],
        include_comments: bool = True,
    ) -> GenerateYamlResponse:
        """
        Generate YAML configuration from voice assignments.

        Args:
            assignments: List of voice assignments
            character_info: List of character information for comments
            include_comments: Whether to include character stats and notes

        Returns:
            GenerateYamlResponse with generated YAML content
        """
        yaml = YAML(typ="safe")
        yaml.preserve_quotes = True
        yaml.default_flow_style = False
        yaml.width = 4096  # Prevent line wrapping
        yaml.map_indent = 2
        yaml.sequence_indent = 4

        # Create character info lookup
        char_info_map = {info.name: info for info in character_info}

        # Build YAML structure using CommentedMap
        root = CommentedMap()

        # Sort assignments: default first, then by line count descending
        sorted_assignments = self._sort_assignments(assignments, character_info)

        for idx, assignment in enumerate(sorted_assignments):
            char_name = assignment.character

            # Build character configuration
            char_config = CommentedMap()

            # Ensure field order: provider first, sts_id second, then others
            char_config["provider"] = assignment.provider
            if assignment.sts_id:  # Only include if not empty
                char_config["sts_id"] = assignment.sts_id

            # Add additional provider fields from provider_config
            if assignment.provider_config:
                for key, value in sorted(assignment.provider_config.items()):
                    if key not in ["provider", "sts_id"]:
                        char_config[key] = value

            # Add character to root with comments if requested
            if include_comments:
                comment_lines = self._build_character_comments(
                    assignment, char_info_map
                )
                if comment_lines:
                    # For first character, add header comments too
                    if idx == 0:
                        header_lines = [
                            "Voice configuration for speakers",
                            "Each speaker requires:",
                            "  provider: The TTS provider to use",
                            "  Additional provider-specific configuration fields",
                            "  Optional fields can be included at the root level",
                            "",
                        ]
                        all_comments = header_lines + comment_lines
                    else:
                        all_comments = [
                            ""
                        ] + comment_lines  # Add empty line before comments

                    # Add comments before the character key
                    root.yaml_set_comment_before_after_key(
                        char_name, before="\n".join(all_comments)
                    )

            root[char_name] = char_config

        # Generate YAML string
        stream = StringIO()
        yaml.dump(root, stream)
        yaml_content = stream.getvalue()

        return GenerateYamlResponse(yaml_content=yaml_content.rstrip())

    def _sort_assignments(
        self, assignments: List[VoiceAssignment], character_info: List[CharacterInfo]
    ) -> List[VoiceAssignment]:
        """Sort assignments by line count (default first, then descending)."""
        char_info_map = {info.name: info for info in character_info}

        return sorted(
            assignments,
            key=lambda a: (
                a.character != "default",
                -(
                    a.line_count
                    or char_info_map.get(
                        a.character,
                        CharacterInfo(
                            name=a.character,
                            line_count=0,
                            total_characters=0,
                            longest_dialogue=0,
                        ),
                    ).line_count
                ),
                a.character,
            ),
        )

    def _build_character_comments(
        self, assignment: VoiceAssignment, char_info_map: Dict[str, CharacterInfo]
    ) -> List[str]:
        """Build comment lines for a character."""
        comments = []
        char_info = char_info_map.get(assignment.character)

        # Character stats (use from assignment if available, otherwise from char_info)
        line_count = assignment.line_count or (char_info.line_count if char_info else 0)
        total_chars = assignment.total_characters or (
            char_info.total_characters if char_info else 0
        )
        longest_dialogue = assignment.longest_dialogue or (
            char_info.longest_dialogue if char_info else 0
        )

        if line_count > 0:
            comments.append(f"{assignment.character}: {line_count} lines")
            comments.append(
                f"Total characters: {total_chars}, Longest dialogue: {longest_dialogue} characters"
            )

        # Structured comments
        if assignment.casting_notes:
            comments.append(f"Casting notes: {assignment.casting_notes}")
        if assignment.role:
            comments.append(f"Role: {assignment.role}")

        # Additional unstructured notes (already include # prefix)
        if assignment.additional_notes:
            for note in assignment.additional_notes:
                # Strip # and re-add to ensure consistent formatting
                clean_note = note.lstrip("#").strip()
                if clean_note:
                    comments.append(clean_note)

        return comments

    async def parse_yaml(self, yaml_content: str) -> ParseYamlResponse:
        """
        Parse YAML configuration and extract voice assignments.

        Args:
            yaml_content: YAML configuration content

        Returns:
            ParseYamlResponse with parsed assignments
        """
        yaml = YAML(typ="safe")
        assignments = []
        errors = []

        # Handle empty or whitespace-only content
        if not yaml_content or not yaml_content.strip():
            errors.append("YAML content is empty")
            return ParseYamlResponse(assignments=[], has_errors=True, errors=errors)

        try:
            # First, extract comments for each character
            character_comments = self._extract_yaml_comments(yaml_content)

            # Then parse the YAML data
            yaml_data = yaml.load(StringIO(yaml_content))

            # Handle null/None result from YAML parser
            if yaml_data is None:
                errors.append("YAML file contains no valid data")
                return ParseYamlResponse(assignments=[], has_errors=True, errors=errors)

            if not isinstance(yaml_data, dict):
                errors.append(
                    "YAML must be a mapping of speakers to voice configurations"
                )
                return ParseYamlResponse(assignments=[], has_errors=True, errors=errors)

            # Handle empty dictionary
            if not yaml_data:
                errors.append("No speaker configurations found in YAML")
                return ParseYamlResponse(assignments=[], has_errors=True, errors=errors)

            # Extract assignments from YAML
            for speaker, config in yaml_data.items():
                # Skip null/None values
                if config is None:
                    errors.append(f"{speaker}: Configuration is empty (null)")
                    continue

                if not isinstance(config, dict):
                    errors.append(
                        f"{speaker}: Configuration must be a dictionary, got {type(config).__name__}"
                    )
                    continue

                # Normalize speaker name (handle special characters)
                speaker_str = str(speaker).strip()

                provider = config.get("provider")
                sts_id = config.get("sts_id") or config.get(
                    "voice_id", ""
                )  # Default to empty string

                if not provider:
                    errors.append(f"{speaker_str}: Missing required 'provider' field")
                    continue

                # Get comments for this character
                comment_info = character_comments.get(speaker_str, {})

                # Build provider_config with all fields except provider and sts_id
                temp_provider_config: Dict[str, Any] = {}
                for key, value in config.items():
                    if key not in ["provider", "sts_id", "voice_id"]:
                        temp_provider_config[key] = value

                # Only include provider_config if it has content
                provider_config: Optional[Dict[str, Any]] = (
                    temp_provider_config if temp_provider_config else None
                )

                assignment = VoiceAssignment(
                    character=speaker_str,
                    provider=str(provider).strip(),
                    sts_id=str(sts_id).strip() if sts_id else "",
                    casting_notes=comment_info.get("casting_notes"),
                    role=comment_info.get("role"),
                    provider_config=provider_config,
                    additional_notes=comment_info.get("additional_notes"),
                    line_count=comment_info.get("line_count"),
                    total_characters=comment_info.get("total_characters"),
                    longest_dialogue=comment_info.get("longest_dialogue"),
                )
                assignments.append(assignment)

        except DuplicateKeyError as e:
            # Extract duplicate key from error
            error_msg = str(e)
            import re

            duplicate_key_match = re.search(r'found duplicate key "([^"]+)"', error_msg)
            if duplicate_key_match:
                errors.append(
                    f"Duplicate speaker found: {duplicate_key_match.group(1)}"
                )
            else:
                errors.append(f"Duplicate speaker found in YAML")
        except Exception as e:
            # Provide more detailed error messages
            error_type = type(e).__name__
            if "found undefined alias" in str(e):
                errors.append("YAML contains undefined aliases or references")
            elif "could not determine a constructor" in str(e):
                errors.append("YAML contains invalid syntax or unsupported constructs")
            elif "expected a single document" in str(e):
                errors.append(
                    "YAML contains multiple documents (use single document only)"
                )
            else:
                errors.append(f"Failed to parse YAML ({error_type}): {str(e)}")

        # Check if we have at least one valid assignment
        if not assignments and not errors:
            errors.append("No valid speaker configurations found in YAML")

        return ParseYamlResponse(
            assignments=assignments, has_errors=len(errors) > 0, errors=errors
        )

    def _extract_yaml_comments(self, yaml_content: str) -> Dict[str, Dict[str, Any]]:
        """
        Extract casting notes, role, character stats, and additional notes from YAML comments.

        Args:
            yaml_content: YAML configuration content

        Returns:
            Dictionary mapping character names to their comment info
        """
        import re

        character_comments: Dict[str, Dict[str, Any]] = {}
        lines = yaml_content.split("\n")

        current_character = None
        comment_buffer: List[str] = []

        # Compile patterns from constants
        line_count_pattern = re.compile(
            YAML_COMMENT_PATTERNS["LINE_COUNT"], re.IGNORECASE
        )
        char_stats_pattern = re.compile(
            YAML_COMMENT_PATTERNS["CHAR_STATS"], re.IGNORECASE
        )
        casting_notes_pattern = re.compile(
            YAML_COMMENT_PATTERNS["CASTING_NOTES"], re.IGNORECASE
        )
        role_pattern = re.compile(YAML_COMMENT_PATTERNS["ROLE"], re.IGNORECASE)

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Check if this is a character definition line (ends with ':')
            if stripped and not stripped.startswith("#") and stripped.endswith(":"):
                # Look for the character name before the colon
                # Skip if it's inside the YAML structure (has spaces before it indicating nesting)
                if not line.startswith(" "):
                    # Extract character name (handle quoted names)
                    char_name = stripped.rstrip(":").strip()
                    # Handle various quote types
                    if (char_name.startswith('"') and char_name.endswith('"')) or (
                        char_name.startswith("'") and char_name.endswith("'")
                    ):
                        char_name = char_name[1:-1]

                    # Process comments that appeared right before this character
                    if comment_buffer:
                        casting_notes = []
                        roles = []
                        additional_notes = []
                        line_count = None
                        total_characters = None
                        longest_dialogue = None

                        for comment in comment_buffer:
                            # Check for line count
                            line_count_match = line_count_pattern.match(comment)
                            if line_count_match:
                                line_count = int(line_count_match.group(2))
                                continue

                            # Check for character stats
                            char_stats_match = char_stats_pattern.match(comment)
                            if char_stats_match:
                                total_characters = int(char_stats_match.group(1))
                                longest_dialogue = int(char_stats_match.group(2))
                                continue

                            # Check for casting notes
                            casting_match = casting_notes_pattern.match(comment)
                            if casting_match:
                                casting_notes.append(casting_match.group(1).strip())
                                continue

                            # Check for role
                            role_match = role_pattern.match(comment)
                            if role_match:
                                roles.append(role_match.group(1).strip())
                                continue

                            # If it doesn't match any pattern, it's an additional note
                            additional_notes.append(comment)

                        # Store all extracted information
                        if (
                            casting_notes
                            or roles
                            or additional_notes
                            or line_count is not None
                        ):
                            character_comments[char_name] = {}
                            if casting_notes:
                                # Join multi-line casting notes with spaces
                                character_comments[char_name]["casting_notes"] = (
                                    " ".join(casting_notes)
                                )
                            if roles:
                                # Join multi-line roles with spaces
                                character_comments[char_name]["role"] = " ".join(roles)
                            if additional_notes:
                                character_comments[char_name][
                                    "additional_notes"
                                ] = additional_notes
                            if line_count is not None:
                                character_comments[char_name]["line_count"] = line_count
                            if total_characters is not None:
                                character_comments[char_name][
                                    "total_characters"
                                ] = total_characters
                            if longest_dialogue is not None:
                                character_comments[char_name][
                                    "longest_dialogue"
                                ] = longest_dialogue

                    # Reset for next character
                    current_character = char_name
                    comment_buffer = []

            # Accumulate comment lines
            elif stripped.startswith("#"):
                comment_buffer.append(stripped)

            # Clear comment buffer if we hit a non-comment, non-character line
            elif stripped and not line.startswith(" "):
                comment_buffer = []

        return character_comments

    async def generate_character_notes_prompt(
        self,
        session_id: str,
        yaml_content: str,
        custom_prompt_path: Optional[str] = None,
    ) -> GenerateCharacterNotesPromptResponse:
        """
        Generate character notes prompt for LLM assistance.

        Args:
            session_id: Voice casting session UUID
            yaml_content: Current YAML configuration content
            custom_prompt_path: Optional custom prompt file path

        Returns:
            GenerateCharacterNotesPromptResponse with prompt content and privacy notice

        Raises:
            ValueError: If session not found or doesn't have a screenplay source path
        """
        # Get session and validate screenplay source path
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        if not session.screenplay_source_path:
            raise ValueError(
                f"Session {session_id} does not have a screenplay source path. Please upload the original PDF/TXT file."
            )

        # Write YAML content to temporary file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as tmp_yaml:
            tmp_yaml.write(yaml_content)
            tmp_yaml_path = Path(tmp_yaml.name)

        try:
            # Convert paths
            source_path = Path(session.screenplay_source_path)
            prompt_path = Path(custom_prompt_path) if custom_prompt_path else None

            # Generate prompt file
            output_path = await asyncio.get_event_loop().run_in_executor(
                None,
                generate_voice_casting_prompt_file,
                source_path,
                tmp_yaml_path,
                prompt_path,
            )

            # Read generated prompt
            with open(output_path, "r", encoding="utf-8") as f:
                prompt_content = f.read()

            # Clean up output file
            output_path.unlink(missing_ok=True)

            # Generate privacy notice
            privacy_notice = (
                f"⚠️ PRIVACY NOTICE:\n"
                f"This optional feature includes the COMPLETE TEXT of '{source_path.name}'\n"
                f"Before uploading to any LLM service:\n"
                f"• Review the service's privacy policy and data usage practices\n"
                f"• Ensure you're comfortable sharing your screenplay content\n"
                f"• Consider whether the service uses your content for AI training\n"
                f"• Alternative: Skip LLM assistance and configure voices manually\n"
                f"• For sensitive content, consider local LLM solutions\n"
                f"See PRIVACY.md for detailed guidance on privacy-conscious usage."
            )

            return GenerateCharacterNotesPromptResponse(
                prompt_content=prompt_content, privacy_notice=privacy_notice
            )

        finally:
            # Clean up temporary YAML file
            tmp_yaml_path.unlink(missing_ok=True)

    async def generate_voice_library_prompt(
        self,
        yaml_content: str,
        providers: List[str],
        custom_prompt_path: Optional[str] = None,
    ) -> GenerateVoiceLibraryPromptResponse:
        """
        Generate voice library casting prompt for LLM assistance.

        Args:
            yaml_content: Voice configuration YAML with character notes
            providers: List of providers to include in prompt
            custom_prompt_path: Optional custom prompt file path

        Returns:
            GenerateVoiceLibraryPromptResponse with prompt content and privacy notice
        """
        # Write YAML content to temporary file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as tmp_yaml:
            tmp_yaml.write(yaml_content)
            tmp_yaml_path = Path(tmp_yaml.name)

        try:
            # Convert prompt path
            prompt_path = Path(custom_prompt_path) if custom_prompt_path else None

            # Generate prompt file
            output_path = await asyncio.get_event_loop().run_in_executor(
                None,
                generate_voice_library_casting_prompt_file,
                tmp_yaml_path,
                providers,
                prompt_path,
                None,  # output_file_path
            )

            # Read generated prompt
            with open(output_path, "r", encoding="utf-8") as f:
                prompt_content = f.read()

            # Clean up output file
            output_path.unlink(missing_ok=True)

            # Generate privacy notice
            providers_str = ", ".join(providers)
            privacy_notice = (
                f"⚠️ PRIVACY NOTICE:\n"
                f"This optional feature includes voice configuration data and character names,\n"
                f"potentially with character casting notes, and voice library data for: {providers_str}.\n"
                f"Before uploading to any LLM service:\n"
                f"• Review the service's privacy policy and data usage practices\n"
                f"• Ensure you're comfortable sharing your voice configuration details\n"
                f"• Consider whether the service uses your content for AI training\n"
                f"• Alternative: Skip LLM assistance and configure voices manually\n"
                f"• For sensitive content, consider local LLM solutions\n"
                f"See PRIVACY.md for detailed guidance on privacy-conscious usage."
            )

            return GenerateVoiceLibraryPromptResponse(
                prompt_content=prompt_content, privacy_notice=privacy_notice
            )

        finally:
            # Clean up temporary YAML file
            tmp_yaml_path.unlink(missing_ok=True)

    async def create_session(
        self, screenplay_json_path: str, screenplay_source_path: Optional[str] = None
    ) -> VoiceCastingSession:
        """
        Create a new voice casting session.

        Args:
            screenplay_json_path: Path to screenplay JSON file
            screenplay_source_path: Optional path to original screenplay file (PDF/TXT)

        Returns:
            VoiceCastingSession object
        """
        session_id = str(uuid.uuid4())
        screenplay_name = Path(screenplay_json_path).stem

        session = VoiceCastingSession(
            session_id=session_id,
            screenplay_json_path=screenplay_json_path,
            screenplay_name=screenplay_name,
            screenplay_source_path=screenplay_source_path,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            status="active",
        )

        self._sessions[session_id] = session
        logger.info(f"Created voice casting session {session_id} for {screenplay_name}")

        return session

    async def create_session_from_task(
        self, parsing_result: Dict[str, Any]
    ) -> VoiceCastingSession:
        """
        Create a voice casting session from a screenplay parsing task result.

        Args:
            parsing_result: Result from screenplay parsing containing file paths

        Returns:
            VoiceCastingSession object

        Raises:
            ValueError: If parsing result doesn't contain required file paths
        """
        # Extract paths from parsing result
        if "files" not in parsing_result or "json" not in parsing_result["files"]:
            raise ValueError("Parsing result does not contain JSON file path")

        json_file_path = parsing_result["files"]["json"]
        original_file_path = parsing_result["files"].get("original")

        # Create session with both JSON and original paths
        session = await self.create_session(
            screenplay_json_path=json_file_path,
            screenplay_source_path=original_file_path,
        )

        logger.info(
            f"Created voice casting session {session.session_id} from parsing task"
        )
        return session

    async def get_session(self, session_id: str) -> Optional[VoiceCastingSession]:
        """
        Retrieve a voice casting session.

        Args:
            session_id: Session UUID

        Returns:
            VoiceCastingSession if found, None otherwise
        """
        return self._sessions.get(session_id)

    async def update_session(
        self, session_id: str, status: str
    ) -> Optional[VoiceCastingSession]:
        """
        Update session status.

        Args:
            session_id: Session UUID
            status: New status (active, completed, expired)

        Returns:
            Updated VoiceCastingSession if found, None otherwise
        """
        session = self._sessions.get(session_id)
        if session:
            session.status = status
            session.updated_at = datetime.utcnow()
        return session

    async def update_session_screenplay_source(
        self, session_id: str, screenplay_source_path: str
    ) -> Optional[VoiceCastingSession]:
        """
        Update the screenplay source path for a session.

        Args:
            session_id: Session UUID
            screenplay_source_path: Path to the original screenplay file (PDF/TXT)

        Returns:
            Updated VoiceCastingSession if found, None otherwise
        """
        session = self._sessions.get(session_id)
        if session:
            session.screenplay_source_path = screenplay_source_path
            session.updated_at = datetime.utcnow()
            logger.info(f"Updated screenplay source path for session {session_id}")
        return session

    async def cleanup_expired_sessions(self, expiry_hours: int = 24) -> int:
        """
        Clean up sessions older than expiry_hours.

        Args:
            expiry_hours: Hours after which sessions expire

        Returns:
            Number of sessions cleaned up
        """
        current_time = datetime.utcnow()
        expired_sessions = []

        for session_id, session in self._sessions.items():
            age_hours = (current_time - session.created_at).total_seconds() / 3600
            if age_hours > expiry_hours:
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            del self._sessions[session_id]
            logger.info(f"Cleaned up expired session {session_id}")

        return len(expired_sessions)


# Create singleton instance
voice_casting_service = VoiceCastingService()
