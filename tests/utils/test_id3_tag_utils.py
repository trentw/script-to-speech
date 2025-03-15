import os
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest
import yaml

from utils.id3_tag_utils import set_id3_tags, set_id3_tags_from_config


class TestSetId3Tags:
    """Tests for the set_id3_tags function."""

    @patch("utils.id3_tag_utils.eyed3.load")
    def test_set_id3_tags_success(self, mock_load):
        """Test set_id3_tags with valid inputs."""
        # Mock eyed3 audio file and tag
        mock_audiofile = MagicMock()
        mock_tag = MagicMock()
        mock_audiofile.tag = mock_tag
        mock_load.return_value = mock_audiofile

        # Call function
        set_id3_tags(
            mp3_path="/test/path.mp3",
            title="Test Title",
            screenplay_author="Test Author",
            date="2023",
        )

        # Verify eyed3 was loaded correctly
        mock_load.assert_called_once_with("/test/path.mp3")

        # Verify tag setting
        assert mock_tag.title == "Test Title"
        assert mock_tag.album == "Test Title"
        assert mock_tag.artist == "Test Author"
        assert mock_tag.recording_date == "2023"

        # Verify tag was saved
        mock_tag.save.assert_called_once()

    @patch("utils.id3_tag_utils.eyed3.load")
    def test_set_id3_tags_with_no_tag(self, mock_load):
        """Test set_id3_tags when the audio file has no tag."""
        # Create a mock audio file
        mock_audiofile = MagicMock()
        mock_audiofile.tag = None

        # Create a mock tag that will be attached after initTag
        mock_tag = MagicMock()

        # Configure the mock load to return our audiofile
        mock_load.return_value = mock_audiofile

        # Setup initTag to set the tag attribute
        def mock_init_tag():
            mock_audiofile.tag = mock_tag

        mock_audiofile.initTag.side_effect = mock_init_tag

        # Call function
        set_id3_tags(
            mp3_path="/test/path.mp3",
            title="Test Title",
            screenplay_author="Test Author",
            date="2023",
        )

        # Verify initTag was called
        mock_audiofile.initTag.assert_called_once()

        # Verify tag was set correctly
        assert mock_tag.title == "Test Title"
        assert mock_tag.album == "Test Title"
        assert mock_tag.artist == "Test Author"
        assert mock_tag.recording_date == "2023"

        # Verify tag was saved
        mock_tag.save.assert_called_once()

    @patch("utils.id3_tag_utils.eyed3.load")
    def test_set_id3_tags_could_not_load_file(self, mock_load):
        """Test set_id3_tags when the audio file cannot be loaded."""
        # Both load attempts return None
        mock_load.return_value = None

        # Call function should raise ValueError
        with pytest.raises(ValueError, match="Could not load MP3 file:"):
            set_id3_tags(
                mp3_path="/test/path.mp3",
                title="Test Title",
                screenplay_author="Test Author",
                date="2023",
            )

        # Verify eyed3 was loaded twice (initial attempt and retry)
        assert mock_load.call_count == 2
        mock_load.assert_called_with("/test/path.mp3")

    @patch("utils.id3_tag_utils.eyed3.load")
    def test_set_id3_tags_with_empty_date(self, mock_load):
        """Test set_id3_tags with empty date value."""
        # Mock eyed3 audio file and tag
        mock_audiofile = MagicMock()
        mock_tag = MagicMock()
        mock_audiofile.tag = mock_tag
        mock_load.return_value = mock_audiofile

        # Call function with empty date
        set_id3_tags(
            mp3_path="/test/path.mp3",
            title="Test Title",
            screenplay_author="Test Author",
            date="",
        )

        # Verify title and artist were set
        assert mock_tag.title == "Test Title"
        assert mock_tag.album == "Test Title"
        assert mock_tag.artist == "Test Author"

        # Verify tag was saved
        mock_tag.save.assert_called_once()

    @patch("utils.id3_tag_utils.eyed3.load")
    def test_set_id3_tags_error_handling(self, mock_load):
        """Test set_id3_tags when an error occurs during tag setting."""
        # Mock eyed3 load to raise exception
        mock_load.side_effect = Exception("Test error")

        # Call function should propagate exception
        with pytest.raises(Exception, match="Test error"):
            set_id3_tags(
                mp3_path="/test/path.mp3",
                title="Test Title",
                screenplay_author="Test Author",
                date="2023",
            )


class TestSetId3TagsFromConfig:
    """Tests for the set_id3_tags_from_config function."""

    @patch("utils.id3_tag_utils.set_id3_tags")
    def test_set_id3_tags_from_config_success(self, mock_set_id3_tags):
        """Test set_id3_tags_from_config with valid configuration."""
        # Mock yaml.safe_load to return valid config
        config = {
            "id3_tag_config": {
                "title": "Config Title",
                "screenplay_author": "Config Author",
                "date": "2023",
            }
        }

        # Setup mock file open
        with patch("builtins.open", mock_open(read_data="dummy_data")) as mock_file:
            with patch("yaml.safe_load", return_value=config):
                # Call function
                result = set_id3_tags_from_config(
                    mp3_path="/test/path.mp3", config_path="/test/config.yaml"
                )

                # Verify file was opened correctly
                mock_file.assert_called_once_with(
                    "/test/config.yaml", "r", encoding="utf-8"
                )

                # Verify set_id3_tags was called with correct args
                mock_set_id3_tags.assert_called_once_with(
                    "/test/path.mp3", "Config Title", "Config Author", "2023"
                )

                # Verify result is True
                assert result is True

    @patch("utils.id3_tag_utils.set_id3_tags")
    def test_set_id3_tags_from_config_no_id3_section(self, mock_set_id3_tags):
        """Test set_id3_tags_from_config when config has no id3_tag_config section."""
        # Mock yaml.safe_load to return config without id3_tag_config
        config = {"other_section": {}}

        # Setup mock file open
        with patch("builtins.open", mock_open(read_data="dummy_data")) as mock_file:
            with patch("yaml.safe_load", return_value=config):
                # Call function
                result = set_id3_tags_from_config(
                    mp3_path="/test/path.mp3", config_path="/test/config.yaml"
                )

                # Verify file was opened correctly
                mock_file.assert_called_once_with(
                    "/test/config.yaml", "r", encoding="utf-8"
                )

                # Verify set_id3_tags was not called
                mock_set_id3_tags.assert_not_called()

                # Verify result is False
                assert result is False

    @patch("utils.id3_tag_utils.set_id3_tags")
    def test_set_id3_tags_from_config_no_title(self, mock_set_id3_tags):
        """Test set_id3_tags_from_config when config has no title."""
        # Mock yaml.safe_load to return config without title
        config = {
            "id3_tag_config": {"screenplay_author": "Config Author", "date": "2023"}
        }

        # Setup mock file open
        with patch("builtins.open", mock_open(read_data="dummy_data")) as mock_file:
            with patch("yaml.safe_load", return_value=config):
                # Call function
                result = set_id3_tags_from_config(
                    mp3_path="/test/path.mp3", config_path="/test/config.yaml"
                )

                # Verify file was opened correctly
                mock_file.assert_called_once_with(
                    "/test/config.yaml", "r", encoding="utf-8"
                )

                # Verify set_id3_tags was not called
                mock_set_id3_tags.assert_not_called()

                # Verify result is False
                assert result is False

    @patch("utils.id3_tag_utils.set_id3_tags")
    def test_set_id3_tags_from_config_empty_title(self, mock_set_id3_tags):
        """Test set_id3_tags_from_config when config has empty title."""
        # Mock yaml.safe_load to return config with empty title
        config = {
            "id3_tag_config": {
                "title": "",
                "screenplay_author": "Config Author",
                "date": "2023",
            }
        }

        # Setup mock file open
        with patch("builtins.open", mock_open(read_data="dummy_data")) as mock_file:
            with patch("yaml.safe_load", return_value=config):
                # Call function
                result = set_id3_tags_from_config(
                    mp3_path="/test/path.mp3", config_path="/test/config.yaml"
                )

                # Verify file was opened correctly
                mock_file.assert_called_once_with(
                    "/test/config.yaml", "r", encoding="utf-8"
                )

                # Verify set_id3_tags was not called
                mock_set_id3_tags.assert_not_called()

                # Verify result is False
                assert result is False

    @patch("utils.id3_tag_utils.set_id3_tags")
    def test_set_id3_tags_from_config_missing_fields(self, mock_set_id3_tags):
        """Test set_id3_tags_from_config with missing optional fields."""
        # Mock yaml.safe_load to return config with just title
        config = {"id3_tag_config": {"title": "Config Title"}}

        # Setup mock file open
        with patch("builtins.open", mock_open(read_data="dummy_data")) as mock_file:
            with patch("yaml.safe_load", return_value=config):
                # Call function
                result = set_id3_tags_from_config(
                    mp3_path="/test/path.mp3", config_path="/test/config.yaml"
                )

                # Verify file was opened correctly
                mock_file.assert_called_once_with(
                    "/test/config.yaml", "r", encoding="utf-8"
                )

                # Verify set_id3_tags was called with defaults for missing fields
                mock_set_id3_tags.assert_called_once_with(
                    "/test/path.mp3",
                    "Config Title",
                    "",  # Default empty screenplay_author
                    "",  # Default empty date
                )

                # Verify result is True
                assert result is True

    def test_set_id3_tags_from_config_file_error(self):
        """Test set_id3_tags_from_config when file cannot be opened."""
        # Setup mock file open to raise exception
        with patch("builtins.open", side_effect=Exception("File error")):
            # Call function
            result = set_id3_tags_from_config(
                mp3_path="/test/path.mp3", config_path="/test/config.yaml"
            )

            # Verify result is False
            assert result is False

    @patch("utils.id3_tag_utils.set_id3_tags")
    def test_set_id3_tags_from_config_id3_error(self, mock_set_id3_tags):
        """Test set_id3_tags_from_config when setting ID3 tags fails."""
        # Mock yaml.safe_load to return valid config
        config = {
            "id3_tag_config": {
                "title": "Config Title",
                "screenplay_author": "Config Author",
                "date": "2023",
            }
        }

        # Mock set_id3_tags to raise exception
        mock_set_id3_tags.side_effect = Exception("ID3 error")

        # Setup mock file open
        with patch("builtins.open", mock_open(read_data="dummy_data")) as mock_file:
            with patch("yaml.safe_load", return_value=config):
                # Call function
                result = set_id3_tags_from_config(
                    mp3_path="/test/path.mp3", config_path="/test/config.yaml"
                )

                # Verify file was opened correctly
                mock_file.assert_called_once_with(
                    "/test/config.yaml", "r", encoding="utf-8"
                )

                # Verify set_id3_tags was called
                mock_set_id3_tags.assert_called_once()

                # Verify result is False due to exception
                assert result is False
