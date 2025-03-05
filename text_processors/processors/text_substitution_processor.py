import re
from typing import Dict, List, Tuple

from ..text_processor_base import TextProcessor


class TextSubstitutionProcessor(TextProcessor):
    """Processor that performs text substitutions (e.g., expanding abbreviations)."""

    def __init__(self, config: Dict):
        super().__init__(config)
        self.substitutions = self.prepare_substitutions()

    def prepare_substitutions(self):
        substitutions = []
        for sub in self.config.get("substitutions", []):
            pattern = re.escape(sub["from"])
            replacement = sub["to"]
            fields = sub["fields"]
            substitutions.append((pattern, replacement, fields))
        return substitutions

    def process(self, json_chunk: Dict) -> Tuple[Dict, bool]:
        modified_chunk = json_chunk.copy()
        changes_made = False

        for field in set(
            field for _, _, fields in self.substitutions for field in fields
        ):
            if field in json_chunk:
                original_text = json_chunk[field]
                modified_text = original_text

                for pattern, replacement, sub_fields in self.substitutions:
                    if field in sub_fields:
                        modified_text = re.sub(
                            pattern, replacement, modified_text, flags=re.UNICODE
                        )

                if modified_text != original_text:
                    modified_chunk[field] = modified_text
                    changes_made = True

        return modified_chunk, changes_made

    def get_transformed_fields(self) -> List[str]:
        return list(
            set(field for _, _, fields in self.substitutions for field in fields)
        )

    def validate_config(self) -> bool:
        if not isinstance(self.config.get("substitutions"), list):
            return False
        for sub in self.config.get("substitutions", []):
            if not all(key in sub for key in ["from", "to", "fields"]):
                return False
            if not isinstance(sub["fields"], list):
                return False
        return True
