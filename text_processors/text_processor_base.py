from abc import ABC, abstractmethod, abstractproperty
from typing import Dict, List, Tuple, Literal


class TextProcessor(ABC):
    """Base class for text processors that modify screenplay text chunks."""

    def __init__(self, config: Dict):
        self.config = config

    @property
    def multi_config_mode(self) -> Literal["chain", "override"]:
        """
        Determines how this processor behaves when multiple configs are loaded.
        
        Returns:
            "chain": Multiple instances of this processor can exist and will be chained
            "override": Only one instance can exist, last config's instance is used
        """
        return "chain"

    @abstractmethod
    def process(self, json_chunk: Dict) -> Tuple[Dict, bool]:
        """
        Process the input text chunk and return a tuple containing:
        - The processed text chunk (modified or original)
        - A boolean indicating whether the chunk was modified
        """
        pass

    @abstractmethod
    def get_transformed_fields(self) -> List[str]:
        """Return a list of fields that this processor transforms."""
        pass

    @abstractmethod
    def validate_config(self) -> bool:
        """
        Validate the configuration for this processor.
        Return True if the configuration is valid, False otherwise.
        """
        pass
