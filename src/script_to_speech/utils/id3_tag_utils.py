import os
from pathlib import Path
from typing import Any, Dict, Optional

import eyed3
import yaml

from .logging import get_screenplay_logger

logger = get_screenplay_logger("id3_tag_utils")

# TXXX frame descriptions for generation provenance stamped on review-flow
# variants (see utils/generate_standalone_speech.py). The frames travel with
# the file when a variant is committed into a project's audio cache.
GENERATION_KIND_FRAME = "STS_GENERATION_KIND"
GENERATION_TEXT_FRAME = "STS_GENERATION_TEXT"


def set_id3_tags(mp3_path: str, title: str, screenplay_author: str, date: str) -> None:
    """
    Set ID3 tags for an MP3 file.

    Args:
        mp3_path: Path to the MP3 file
        title: Title to set (will be used for both title and album tags)
        screenplay_author: Author to set as artist
        date: Date to set
    """
    try:
        audiofile = eyed3.load(mp3_path)
        if audiofile is None or audiofile.tag is None:
            audiofile = eyed3.load(mp3_path)
            if audiofile is None:
                raise ValueError(f"Could not load MP3 file: {mp3_path}")
            audiofile.initTag()

        logger.info(f"Setting ID3 tags for {mp3_path}")
        logger.info(f"  Title: {title}")
        logger.info(f"  Album: {title}")
        logger.info(f"  Artist: {screenplay_author}")
        logger.info(f"  Date: {date}")

        audiofile.tag.title = title
        audiofile.tag.album = title
        audiofile.tag.artist = screenplay_author
        if date:
            audiofile.tag.recording_date = date

        audiofile.tag.save()
        logger.info("ID3 tags saved successfully")
    except Exception as e:
        logger.error(f"Error setting ID3 tags: {str(e)}")
        raise


def set_generation_metadata(
    mp3_path: str, generation_kind: str, generation_text: str
) -> bool:
    """
    Stamp generation provenance into ID3 user-text (TXXX) frames.

    Records the generation kind ("retake"/"edit") and the exact text that
    produced the audio, so the provenance travels with the file when a
    review-flow variant is copied into a project's audio cache.

    Non-fatal by design: a tagging failure must not fail an otherwise
    successful generation.

    Returns:
        True if the tags were written, False otherwise.
    """
    try:
        audiofile = eyed3.load(mp3_path)
        if audiofile is None:
            raise ValueError(f"Could not load MP3 file: {mp3_path}")
        tag = audiofile.tag
        if tag is None:
            audiofile.initTag()
            tag = audiofile.tag
        if tag is None:
            raise ValueError(f"Could not initialize ID3 tag: {mp3_path}")
        tag.user_text_frames.set(generation_kind, GENERATION_KIND_FRAME)
        tag.user_text_frames.set(generation_text, GENERATION_TEXT_FRAME)
        tag.save()
        return True
    except Exception as e:
        logger.warning(f"Could not set generation metadata on {mp3_path}: {e}")
        return False


def set_id3_tags_from_config(mp3_path: str, config_path: str) -> bool:
    """
    Set ID3 tags for an MP3 file based on a configuration file.

    Args:
        mp3_path: Path to the MP3 file
        config_path: Path to the configuration file

    Returns:
        True if tags were set successfully, False otherwise
    """
    try:
        # Load the configuration
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # Extract ID3 tag configuration
        id3_config = config.get("id3_tag_config", {})
        title = id3_config.get("title", "")
        screenplay_author = id3_config.get("screenplay_author", "")
        date = id3_config.get("date", "")

        # Only set tags if at least title is provided
        if title:
            # Use the set_id3_tags function to set the tags
            set_id3_tags(mp3_path, title, screenplay_author, date)
            return True
        else:
            logger.warning("No title provided in config, skipping ID3 tag setting")

        return False
    except Exception as e:
        logger.error(f"Error setting ID3 tags from config: {str(e)}")
        return False
