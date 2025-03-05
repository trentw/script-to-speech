from typing import Dict, List, Tuple
from ..text_preprocessor_base import TextPreProcessor
from utils.logging import get_screenplay_logger

logger = get_screenplay_logger("text_processors.preprocessors.speaker_merge")


class SpeakerMergePreProcessor(TextPreProcessor):
    """
    Pre-processor that replaces specified speaker variations with their canonical form.
    Handles both speaker_attribution chunks (changing the text of of the speaker) and
    dialog chunks (changing the speaker)

    Configuration example:
    speakers_to_merge:
      BELLINI:
        - BEL LINI
        - BE LLINI
      LAWRENCE:
        - LAWR ENCE
        - L AWRENCE
    """

    def validate_config(self) -> bool:
        """
        Validate the speakers_to_merge configuration structure.
        The config should be a dictionary where each key is a parent speaker
        and its value is a list of child variations.
        """
        speakers_config = self.config.get("speakers_to_merge")

        if not isinstance(speakers_config, dict):
            logger.error("speakers_to_merge must be a dictionary")
            return False

        for parent, children in speakers_config.items():
            if not isinstance(children, list):
                logger.error(f"Children for {parent} must be a list")
                return False

            if not all(isinstance(child, str) for child in children):
                logger.error(f"All children for {parent} must be strings")
                return False

        return True

    def _build_speaker_mapping(self) -> Dict[str, str]:
        """
        Build a mapping of child speakers to their parent speakers.
        For dialog chunks, we'll use trimmed versions for matching.
        For speaker_attribution, we'll use the exact strings for replacement.
        """
        mapping = {}
        for parent, children in self.config["speakers_to_merge"].items():
            for child in children:
                if child != parent:  # Don't map parent to itself
                    mapping[child] = parent

        return mapping

    def process(self, chunks: List[Dict]) -> Tuple[List[Dict], bool]:
        """
        Process chunks by replacing speaker variations with their canonical form.

        Args:
            chunks: List of all text chunks from the screenplay

        Returns:
            Tuple[List[Dict], bool]:
                - Modified list of chunks
                - Boolean indicating whether any changes were made
        """
        if not chunks:
            return chunks, False

        if not self.validate_config():
            logger.error("Invalid configuration, skipping speaker merge")
            return chunks, False

        speaker_mapping = self._build_speaker_mapping()
        made_changes = False
        result_chunks = []

        for chunk in chunks:
            modified_chunk = chunk.copy()

            if chunk["type"] == "speaker_attribution":
                # For speaker_attribution, do direct string replacement
                text = chunk["text"]
                for child, parent in speaker_mapping.items():
                    if child in text:
                        text = text.replace(child, parent)
                        made_changes = True
                        logger.info(
                            f"Merged speaker in attribution: {child} -> {parent}"
                        )
                modified_chunk["text"] = text

            elif chunk["type"] == "dialog":
                # For dialog, match on trimmed speaker field
                speaker = chunk.get("speaker", "").strip()
                if speaker in speaker_mapping:
                    parent_speaker = speaker_mapping[speaker]
                    modified_chunk["speaker"] = parent_speaker
                    made_changes = True
                    logger.info(f"Merged dialog speaker: {speaker} -> {parent_speaker}")

            result_chunks.append(modified_chunk)

        return result_chunks, made_changes
