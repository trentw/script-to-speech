# text_processors/text_preprocessor_base.py
from abc import ABC, abstractmethod, abstractproperty
from typing import Dict, List, Tuple, Literal


class TextPreProcessor(ABC):
    """Base class for text pre-processors that can modify the entire chunk list."""

    def __init__(self, config: Dict):
        self.config = config

    @property
    def multi_config_mode(self) -> Literal["chain", "override"]:
        """
        Determines how this preprocessor behaves when multiple configs are loaded.
        
        Returns:
            "chain": Multiple instances of this preprocessor can exist and will be chained
            "override": Only one instance can exist, last config's instance is used
        """
        return "chain"

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
