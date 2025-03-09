import copy
from abc import ABC, abstractmethod, abstractproperty
from typing import Dict, List, Literal, Tuple


class TextProcessor(ABC):
    """
    Base class for text processors that modify screenplay text chunks.

    IMPORTANT: Processors must be STATELESS with respect to chunk processing.
    The configuration is set at initialization time and should not change.
    Processors MUST NOT maintain state between process() calls.
    """

    def __init__(self, config: Dict):
        """
        Initialize with configuration.
        After initialization, the config should be treated as immutable.
        """
        # Create a deep copy to ensure the config can't be modified externally
        self.config = copy.deepcopy(config)

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
