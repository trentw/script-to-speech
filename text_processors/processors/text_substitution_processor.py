import re
from typing import Dict, List, Tuple

from ..text_processor_base import TextProcessor


class TextSubstitutionProcessor(TextProcessor):
    """Processor that performs text substitutions (e.g., expanding abbreviations)."""

    def process(self, json_chunk: Dict) -> Tuple[Dict, bool]:
        modified_chunk = json_chunk.copy()
        changes_made = False

        # Get substitutions from config directly
        for sub in self.config.get("substitutions", []):
            pattern = re.escape(sub.get("from", ""))
            replacement = sub.get("to", "")
            fields = sub.get("fields", [])

            for field in fields:
                if field in json_chunk:
                    original_text = json_chunk[field]
                    modified_text = re.sub(
                        pattern, replacement, original_text, flags=re.UNICODE
                    )

                    if modified_text != original_text:
                        modified_chunk[field] = modified_text
                        changes_made = True

        return modified_chunk, changes_made

    def get_transformed_fields(self) -> List[str]:
        """Return list of fields that this processor transforms."""
        fields = set()
        for sub in self.config.get("substitutions", []):
            for field in sub.get("fields", []):
                fields.add(field)
        return list(fields)

    def validate_config(self) -> bool:
        """Validate the processor configuration."""
        if not isinstance(self.config.get("substitutions"), list):
            return False

        for sub in self.config.get("substitutions", []):
            if not all(key in sub for key in ["from", "to", "fields"]):
                return False

            if not isinstance(sub.get("fields"), list):
                return False

        return True
