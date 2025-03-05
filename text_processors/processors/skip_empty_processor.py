from typing import Dict, Tuple, List
from ..text_processor_base import TextProcessor


class SkipEmptyProcessor(TextProcessor):
    """Processor that removes text from specified chunk types (e.g., page numbers)."""

    def process(self, json_chunk: Dict) -> Tuple[Dict, bool]:
        if json_chunk.get("type") in self.config.get("skip_types", []):
            modified_chunk = json_chunk.copy()
            modified_chunk["text"] = ""
            return modified_chunk, True
        return json_chunk, False

    def get_transformed_fields(self) -> List[str]:
        return ["text"]

    def validate_config(self) -> bool:
        return isinstance(self.config.get("skip_types"), list)
