from typing import Dict, List, Optional, Tuple

from ..text_processor_base import TextProcessor


class SkipEmptyProcessor(TextProcessor):
    """Processor that removes text from specified chunk types (e.g., page numbers)."""

    def process(self, json_chunk: Dict) -> Tuple[Dict, bool]:
        if json_chunk.get("type") in self.config.get(
            "skip_types", []
        ) and json_chunk.get("text"):
            modified_chunk = json_chunk.copy()
            modified_chunk["text"] = ""
            return modified_chunk, True
        return json_chunk, False

    def get_transformed_fields(self) -> List[str]:
        return ["text"]

    def validate_config(self) -> bool:
        return isinstance(self.config.get("skip_types"), list)

    @classmethod
    def get_config_schema(cls) -> Optional[Dict]:
        return {
            "label": "Skip Empty",
            "description": (
                "Blank out the text of specific chunk types so they are not "
                "spoken (e.g. page numbers)."
            ),
            "help": (
                "Empties the spoken text of every chunk of the listed types "
                "so nothing is generated for them. The chunk itself remains "
                "in the screenplay structure.\n\n"
                "Compare with the Skip and Merge structure step, which "
                "removes the chunks entirely and rejoins what they "
                "interrupted — use that when a page number splits a speech "
                "in two; use Skip Empty when you just want a chunk type "
                "silenced."
            ),
            "fields": [
                {
                    "name": "skip_types",
                    "type": "list",
                    "required": True,
                    "label": "Chunk types to skip",
                    "description": "Chunks of these types have their text removed.",
                    "item_schema": {"type": "string", "suggestions_ref": "chunk_types"},
                },
            ],
        }
