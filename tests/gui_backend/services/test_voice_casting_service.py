"""Tests for voice casting service YAML comment preservation."""

import asyncio
from datetime import datetime
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
from ruamel.yaml import YAML

from script_to_speech.gui_backend.services.voice_casting_service import (
    VoiceCastingService,
    VoiceCastingSession,
)


@pytest.fixture
def voice_casting_service():
    """Create a VoiceCastingService instance for testing."""
    return VoiceCastingService()


@pytest.fixture
def sample_yaml_content():
    """Create sample YAML content with comments for testing."""
    return """# Voice configuration for speakers
# Each speaker requires provider and voice configuration

# BARBRA: 39 lines
# Total characters: 2182, Longest dialogue: 214 characters
# Casting notes: Young woman, traumatized and vulnerable
# Role: Major character - main female survivor
BARBRA:
  provider: openai
  sts_id: nova

# HARRY: 56 lines
# Total characters: 5438, Longest dialogue: 301 characters
# Casting notes: Older man, argumentative and fearful
# Role: Secondary character - family man
HARRY:
  provider: elevenlabs
  sts_id: carl

# TOM: 25 lines
# Total characters: 1234, Longest dialogue: 156 characters
# Casting notes: Young man, helpful and brave
# Role: Minor character - assists the group
TOM:
  provider: openai
  sts_id: echo
"""


@pytest.fixture
def yaml_with_quoted_names():
    """Create YAML content with characters requiring quotes."""
    return """# Voice configuration for speakers

# WOMAN #1: 1 lines
# Total characters: 72, Longest dialogue: 72 characters
# Casting notes: Gossipy suburban woman at mall
# Role: Background character
"WOMAN #1":
  provider: elevenlabs

# WOMAN #2: 1 lines
# Total characters: 30, Longest dialogue: 30 characters
# Casting notes: Another gossipy suburban woman
# Role: Background character in mall scene
"WOMAN #2":
  provider: elevenlabs

# TOM:: 8 lines
# Total characters: 456, Longest dialogue: 89 characters
# Casting notes: Character with colon in name
# Role: Special character test
"TOM:":
  provider: openai
  sts_id: ash
"""


@pytest.fixture
def yaml_with_custom_voices():
    """Create YAML with custom voice configurations."""
    return """# Voice configuration

# NARRATOR: 100 lines
# Total characters: 10000, Longest dialogue: 500 characters
# Casting notes: Professional narrator voice
# Role: Main narrator
NARRATOR:
  provider: elevenlabs
  voice_id: custom_voice_123
  stability: 0.75
  similarity_boost: 0.8

# HERO: 50 lines
# Total characters: 5000, Longest dialogue: 250 characters
# Casting notes: Heroic protagonist
# Role: Main character
HERO:
  provider: cartesia
  provider_config:
    voice_id: custom_cartesia_456
    speed: 1.0
    emotion: "neutral"
"""


@pytest.fixture
def mock_session(sample_yaml_content):
    """Create a mock session with YAML content."""
    return VoiceCastingSession(
        session_id="test-session",
        screenplay_json_path="mock.json",
        screenplay_name="test",
        yaml_content=sample_yaml_content,
        yaml_version_id=1,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


class TestYamlCommentPreservation:
    """Test suite for YAML comment preservation when clearing voices."""

    @pytest.mark.asyncio
    async def test_clear_voice_preserves_next_character_comments_beginning(
        self, voice_casting_service, mock_session
    ):
        """Test that clearing first character's voice preserves second character's comments."""
        # Arrange
        service = voice_casting_service
        service._sessions = {"test-session": mock_session}

        # Act
        result = await service.clear_character_voice(
            session_id="test-session", character="BARBRA", version_id=1
        )

        # Assert
        yaml = YAML()
        yaml_data = yaml.load(StringIO(result.yaml_content))

        # Verify BARBRA has null provider and no sts_id
        assert yaml_data["BARBRA"]["provider"] is None
        assert "sts_id" not in yaml_data["BARBRA"]

        # Verify HARRY's comments are preserved in the output
        lines = result.yaml_content.split("\n")
        harry_index = next(
            i
            for i, line in enumerate(lines)
            if "HARRY:" in line and not line.strip().startswith("#")
        )

        # Check previous lines for HARRY's comments
        previous_lines = lines[max(0, harry_index - 5) : harry_index]
        assert any("# HARRY: 56 lines" in line for line in previous_lines)
        assert any("# Total characters: 5438" in line for line in previous_lines)
        assert any("argumentative and fearful" in line for line in previous_lines)
        assert any("Secondary character" in line for line in previous_lines)

    @pytest.mark.asyncio
    async def test_clear_voice_preserves_next_character_comments_middle(
        self, voice_casting_service, mock_session
    ):
        """Test that clearing middle character's voice preserves next character's comments."""
        # Arrange
        service = voice_casting_service
        service._sessions = {"test-session": mock_session}

        # Act
        result = await service.clear_character_voice(
            session_id="test-session", character="HARRY", version_id=1
        )

        # Assert
        yaml = YAML()
        yaml_data = yaml.load(StringIO(result.yaml_content))

        # Verify HARRY has null provider and no sts_id
        assert yaml_data["HARRY"]["provider"] is None
        assert "sts_id" not in yaml_data["HARRY"]

        # Verify TOM's comments are preserved
        lines = result.yaml_content.split("\n")
        tom_index = next(
            i
            for i, line in enumerate(lines)
            if "TOM:" in line and not line.strip().startswith("#")
        )

        previous_lines = lines[max(0, tom_index - 5) : tom_index]
        assert any("# TOM: 25 lines" in line for line in previous_lines)
        assert any("# Total characters: 1234" in line for line in previous_lines)
        assert any("helpful and brave" in line for line in previous_lines)
        assert any("Minor character" in line for line in previous_lines)

    @pytest.mark.asyncio
    async def test_clear_voice_preserves_comments_last_character(
        self, voice_casting_service, mock_session
    ):
        """Test that clearing last character's voice doesn't cause issues."""
        # Arrange
        service = voice_casting_service
        service._sessions = {"test-session": mock_session}

        # Act
        result = await service.clear_character_voice(
            session_id="test-session", character="TOM", version_id=1
        )

        # Assert
        yaml = YAML()
        yaml_data = yaml.load(StringIO(result.yaml_content))

        # Verify TOM has null provider and no sts_id
        assert yaml_data["TOM"]["provider"] is None
        assert "sts_id" not in yaml_data["TOM"]

        # Verify TOM's own comments are still present
        lines = result.yaml_content.split("\n")
        tom_index = next(
            i
            for i, line in enumerate(lines)
            if "TOM:" in line and not line.strip().startswith("#")
        )

        previous_lines = lines[max(0, tom_index - 5) : tom_index]
        assert any("# TOM: 25 lines" in line for line in previous_lines)

    @pytest.mark.asyncio
    async def test_clear_voice_with_quoted_character_names(
        self, voice_casting_service, yaml_with_quoted_names
    ):
        """Test clearing voices for characters with special names requiring quotes."""
        # Arrange
        service = voice_casting_service
        session = VoiceCastingSession(
            session_id="quoted-test",
            screenplay_json_path="mock.json",
            screenplay_name="test",
            yaml_content=yaml_with_quoted_names,
            yaml_version_id=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        service._sessions = {"quoted-test": session}

        # Act
        result = await service.clear_character_voice(
            session_id="quoted-test", character="WOMAN #1", version_id=1
        )

        # Assert
        yaml = YAML()
        yaml.preserve_quotes = True
        yaml_data = yaml.load(StringIO(result.yaml_content))

        # Verify WOMAN #1 has null provider
        assert yaml_data["WOMAN #1"]["provider"] is None

        # Verify WOMAN #2's comments are preserved
        lines = result.yaml_content.split("\n")
        woman2_index = next(
            i
            for i, line in enumerate(lines)
            if '"WOMAN #2":' in line and not line.strip().startswith("#")
        )

        previous_lines = lines[max(0, woman2_index - 6) : woman2_index]
        assert any("# WOMAN #2: 1 lines" in line for line in previous_lines)
        assert any("# Total characters: 30" in line for line in previous_lines)
        assert any("Another gossipy suburban woman" in line for line in previous_lines)
        assert any("mall scene" in line for line in previous_lines)

    @pytest.mark.asyncio
    async def test_clear_voice_when_only_provider_field_exists(
        self, voice_casting_service, yaml_with_quoted_names
    ):
        """Test clearing voice when character only has provider field (no sts_id to delete)."""
        # Arrange
        service = voice_casting_service
        session = VoiceCastingSession(
            session_id="provider-only-test",
            screenplay_json_path="mock.json",
            screenplay_name="test",
            yaml_content=yaml_with_quoted_names,
            yaml_version_id=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        service._sessions = {"provider-only-test": session}

        # Act - WOMAN #1 only has provider field
        result = await service.clear_character_voice(
            session_id="provider-only-test", character="WOMAN #1", version_id=1
        )

        # Assert
        yaml = YAML()
        yaml.preserve_quotes = True
        yaml_data = yaml.load(StringIO(result.yaml_content))

        # Verify WOMAN #1 has null provider and nothing else
        assert yaml_data["WOMAN #1"]["provider"] is None
        assert len(yaml_data["WOMAN #1"]) == 1  # Only provider field

        # Verify next character's comments are still preserved
        lines = result.yaml_content.split("\n")
        woman2_index = next(
            i
            for i, line in enumerate(lines)
            if '"WOMAN #2":' in line and not line.strip().startswith("#")
        )

        previous_lines = lines[max(0, woman2_index - 6) : woman2_index]
        assert any("# WOMAN #2: 1 lines" in line for line in previous_lines)

    @pytest.mark.asyncio
    async def test_clear_custom_voice_preserves_comments(
        self, voice_casting_service, yaml_with_custom_voices
    ):
        """Test clearing custom voice with provider_config preserves comments."""
        # Arrange
        service = voice_casting_service
        session = VoiceCastingSession(
            session_id="custom-test",
            screenplay_json_path="mock.json",
            screenplay_name="test",
            yaml_content=yaml_with_custom_voices,
            yaml_version_id=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        service._sessions = {"custom-test": session}

        # Act
        result = await service.clear_character_voice(
            session_id="custom-test", character="HERO", version_id=1
        )

        # Assert
        yaml = YAML()
        yaml_data = yaml.load(StringIO(result.yaml_content))

        # Verify HERO has null provider and no provider_config
        assert yaml_data["HERO"]["provider"] is None
        assert "provider_config" not in yaml_data["HERO"]

        # Verify HERO's own comments are preserved
        lines = result.yaml_content.split("\n")
        hero_index = next(
            i
            for i, line in enumerate(lines)
            if "HERO:" in line and not line.strip().startswith("#")
        )

        previous_lines = lines[max(0, hero_index - 5) : hero_index]
        assert any("# HERO: 50 lines" in line for line in previous_lines)
        assert any("Heroic protagonist" in line for line in previous_lines)

    @pytest.mark.asyncio
    async def test_clear_voice_with_colon_in_name(
        self, voice_casting_service, yaml_with_quoted_names
    ):
        """Test clearing voice for character with colon in name (e.g., 'TOM:')."""
        # Arrange
        service = voice_casting_service
        session = VoiceCastingSession(
            session_id="colon-test",
            screenplay_json_path="mock.json",
            screenplay_name="test",
            yaml_content=yaml_with_quoted_names,
            yaml_version_id=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        service._sessions = {"colon-test": session}

        # Act
        result = await service.clear_character_voice(
            session_id="colon-test", character="TOM:", version_id=1
        )

        # Assert
        yaml = YAML()
        yaml.preserve_quotes = True
        yaml_data = yaml.load(StringIO(result.yaml_content))

        # Verify TOM: has null provider and no sts_id
        assert yaml_data["TOM:"]["provider"] is None
        assert "sts_id" not in yaml_data["TOM:"]

        # Verify TOM:'s comments are preserved
        lines = result.yaml_content.split("\n")
        tom_colon_index = next(
            i
            for i, line in enumerate(lines)
            if '"TOM:":' in line and not line.strip().startswith("#")
        )

        previous_lines = lines[max(0, tom_colon_index - 5) : tom_colon_index]
        assert any("# TOM:: 8 lines" in line for line in previous_lines)
        assert any("Character with colon" in line for line in previous_lines)

    @pytest.mark.asyncio
    async def test_clear_voice_version_conflict(
        self, voice_casting_service, mock_session
    ):
        """Test that version conflicts are detected."""
        # Arrange
        service = voice_casting_service
        service._sessions = {"test-session": mock_session}

        # Act & Assert
        with pytest.raises(ValueError, match="modified by another source"):
            await service.clear_character_voice(
                session_id="test-session",
                character="BARBRA",
                version_id=999,  # Wrong version
            )

    @pytest.mark.asyncio
    async def test_clear_voice_nonexistent_character(
        self, voice_casting_service, mock_session
    ):
        """Test clearing voice for character that doesn't exist in YAML."""
        # Arrange
        service = voice_casting_service
        service._sessions = {"test-session": mock_session}

        # Act - Character will be created if it doesn't exist
        result = await service.clear_character_voice(
            session_id="test-session", character="NONEXISTENT", version_id=1
        )

        # Assert
        yaml = YAML()
        yaml_data = yaml.load(StringIO(result.yaml_content))

        # Verify character was created with null provider
        assert "NONEXISTENT" in yaml_data
        assert yaml_data["NONEXISTENT"]["provider"] is None

    @pytest.mark.asyncio
    async def test_clear_voice_increments_version(
        self, voice_casting_service, mock_session
    ):
        """Test that clearing voice increments the session version."""
        # Arrange
        service = voice_casting_service
        service._sessions = {"test-session": mock_session}
        original_version = mock_session.yaml_version_id

        # Act
        result = await service.clear_character_voice(
            session_id="test-session", character="BARBRA", version_id=original_version
        )

        # Assert
        assert result.yaml_version_id == original_version + 1

    @pytest.mark.asyncio
    async def test_clear_voice_updates_timestamp(
        self, voice_casting_service, mock_session
    ):
        """Test that clearing voice updates the session timestamp."""
        # Arrange
        service = voice_casting_service
        service._sessions = {"test-session": mock_session}
        original_updated = mock_session.updated_at

        # Act
        result = await service.clear_character_voice(
            session_id="test-session", character="BARBRA", version_id=1
        )

        # Assert
        assert result.updated_at > original_updated
