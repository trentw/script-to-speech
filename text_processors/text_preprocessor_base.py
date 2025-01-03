# text_processors/text_preprocessor_base.py
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple


class TextPreProcessor(ABC):
    """Base class for text pre-processors that can modify the entire chunk list."""

    def __init__(self, config: Dict):
        self.config = config

    @abstractmethod
    def process(self, chunks: List[Dict]) -> Tuple[List[Dict], bool]:
        """
        Process the entire list of text chunks.

        Args:
            chunks: List of all text chunks from the screenplay

        Returns:
            Tuple[List[Dict], bool]: 
                - Modified list of chunks
                - Boolean indicating whether any changes were made

        Raises:
            ValueError: If processing fails
        """
        pass

    def validate_config(self) -> bool:
        """
        Validate the configuration for this pre-processor.
        Default implementation for pre-processors with no config.

        Returns:
            bool: True if configuration is valid
        """
        return True
