from abc import ABC, abstractmethod
from typing import Dict, List, Tuple


class ProcessingSubModule(ABC):
    def __init__(self, config: Dict):
        self.config = config

    @abstractmethod
    def process(self, json_chunk: Dict) -> Tuple[Dict, bool]:
        """
        Process the input JSON chunk and return a tuple containing:
        - The processed JSON chunk (modified or original)
        - A boolean indicating whether the chunk was modified
        """
        pass

    @abstractmethod
    def get_transformed_fields(self) -> List[str]:
        """
        Return a list of fields that this submodule transforms.
        """
        pass

    @abstractmethod
    def validate_config(self) -> bool:
        """
        Validate the configuration for this submodule.
        Return True if the configuration is valid, False otherwise.
        """
        pass
