import re
from typing import Dict, List, Optional, Tuple

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

    @classmethod
    def get_config_schema(cls) -> Optional[Dict]:
        return {
            "label": "Text Substitution",
            "description": (
                'Replace exact text with a substitution (e.g. "V.O." -> '
                '"VOICE OVER").'
            ),
            "help": (
                "Finds exact text and replaces it — no regex, no case "
                "folding. Use it to expand screenplay abbreviations the TTS "
                'voice would otherwise read literally ("V.O.", "INT.", '
                '"CONT\'D").\n\n'
                "Substitutions run top to bottom on each line; a later rule "
                "sees the output of earlier ones. By default only the spoken "
                '"text" field is touched — the advanced Fields setting can '
                "also target the speaker or other chunk fields.\n\n"
                "For pattern-based matching (anything beyond an exact "
                "string), use Pattern Replace instead."
            ),
            "fields": [
                {
                    "name": "substitutions",
                    "type": "list",
                    "required": True,
                    "label": "Substitutions",
                    "item_schema": {
                        "type": "object",
                        "fields": [
                            {
                                "name": "from",
                                "type": "string",
                                "required": True,
                                "label": "Replace",
                                "description": "Exact text to find (not a regex).",
                            },
                            {
                                "name": "to",
                                "type": "string",
                                "required": True,
                                "label": "With",
                            },
                            {
                                "name": "fields",
                                "type": "list",
                                "required": True,
                                "default": ["text"],
                                "label": "Fields",
                                "description": (
                                    "Chunk fields the substitution is applied to."
                                ),
                                "advanced": True,
                                "item_schema": {
                                    "type": "string",
                                    "suggestions_ref": "chunk_fields",
                                },
                            },
                            {
                                "name": "notes",
                                "type": "string",
                                "label": "Notes",
                                "description": (
                                    "Optional note kept in the config file "
                                    "(why this rule exists). Shown above the "
                                    "rule in the editor."
                                ),
                                "advanced": True,
                            },
                        ],
                    },
                },
            ],
        }
