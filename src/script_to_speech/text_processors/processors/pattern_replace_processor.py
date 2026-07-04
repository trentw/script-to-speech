import re
from typing import Dict, List, Optional, Tuple

from ..text_processor_base import TextProcessor


class PatternReplaceProcessor(TextProcessor):
    """
    Processor that replaces text in fields based on pattern matches in other fields.
    """

    def process(self, json_chunk: Dict) -> Tuple[Dict, bool]:
        modified_chunk = json_chunk.copy()
        changes_made = False

        for replacement in self.config.get("replacements", []):
            # Skip if any required fields are missing
            if not all(
                key in replacement
                for key in [
                    "match_field",
                    "match_pattern",
                    "replace_field",
                    "replace_pattern",
                    "replace_string",
                ]
            ):
                continue

            # Get configuration values
            match_field = replacement["match_field"]
            replace_field = replacement["replace_field"]
            replace_string = replacement["replace_string"]

            # Skip if match field isn't in the chunk
            if match_field not in json_chunk:
                continue

            # Try to compile patterns
            try:
                match_pattern = re.compile(replacement["match_pattern"])
                replace_pattern = re.compile(replacement["replace_pattern"])
            except re.error:
                continue

            # Check if the match field matches the pattern
            if match_pattern.match(str(json_chunk[match_field])):
                # If match is found and replace field exists, perform replacement
                if replace_field in json_chunk:
                    original_text = str(json_chunk[replace_field])
                    modified_text = re.sub(
                        replace_pattern,
                        replace_string if replace_string else "",
                        original_text,
                    )

                    if modified_text != original_text:
                        modified_chunk[replace_field] = modified_text
                        changes_made = True

        return modified_chunk, changes_made

    def get_transformed_fields(self) -> List[str]:
        """Return list of all fields that could be transformed."""
        return list(
            set(
                r.get("replace_field", "")
                for r in self.config.get("replacements", [])
                if "replace_field" in r
            )
        )

    def validate_config(self) -> bool:
        if not isinstance(self.config.get("replacements"), list):
            return False

        required_keys = {
            "match_field",
            "match_pattern",
            "replace_field",
            "replace_pattern",
            "replace_string",
        }

        for replacement in self.config.get("replacements", []):
            # Verify all required keys are present
            if not all(key in replacement for key in required_keys):
                return False

            # Verify all values are strings
            if not all(
                isinstance(replacement.get(key, ""), str) for key in required_keys
            ):
                return False

            # Verify patterns are valid regex
            try:
                re.compile(replacement.get("match_pattern", ""))
                re.compile(replacement.get("replace_pattern", ""))
            except re.error:
                return False

        return True

    @classmethod
    def get_config_schema(cls) -> Optional[Dict]:
        return {
            "label": "Pattern Replace",
            "description": (
                "Regex-based replacement, applied to chunks whose match field "
                "matches a pattern."
            ),
            "help": (
                "Each replacement is a two-step rule:\n\n"
                "1. Match: a line is eligible when the Match pattern (a "
                'regex) matches its Match field — usually "type", so a rule '
                "only applies to, say, dialogue_modifier lines.\n\n"
                "2. Replace: within the eligible line's Replace field "
                '(usually "text"), every occurrence of the Replace pattern '
                "is swapped for the Replacement string. The replacement "
                "supports backreferences like \\1 for groups captured by the "
                'Replace pattern. An empty "replace" will remove the matched string. \n\n'
                "Patterns use Python regex syntax and are validated as you "
                "type. Example: match pattern ^dialogue_modifier$ on field "
                "type, replace pattern ^\\(|\\)$ with an empty replacement "
                'strips the parentheses from "(gasps)".'
            ),
            "fields": [
                {
                    "name": "replacements",
                    "type": "list",
                    "required": True,
                    "label": "Replacements",
                    "item_schema": {
                        "type": "object",
                        "fields": [
                            {
                                "name": "match_field",
                                "type": "string",
                                "required": True,
                                "default": "type",
                                "label": "Match field",
                                "description": (
                                    "Chunk field checked against the match pattern."
                                ),
                                "advanced": True,
                                "suggestions_ref": "chunk_fields",
                            },
                            {
                                "name": "match_pattern",
                                "type": "string",
                                "format": "regex",
                                "required": True,
                                "label": "Match pattern",
                                "description": (
                                    "Chunk is eligible when this regex matches the "
                                    "match field (anchored at the start)."
                                ),
                            },
                            {
                                "name": "replace_field",
                                "type": "string",
                                "required": True,
                                "default": "text",
                                "label": "Replace field",
                                "description": (
                                    "Chunk field the replacement is applied to."
                                ),
                                "advanced": True,
                                "suggestions_ref": "chunk_fields",
                            },
                            {
                                "name": "replace_pattern",
                                "type": "string",
                                "format": "regex",
                                "required": True,
                                "label": "Replace pattern",
                                "description": "Regex replaced within the replace field.",
                            },
                            {
                                "name": "replace_string",
                                "type": "string",
                                "required": True,
                                "label": "Replacement",
                                "description": (
                                    "Replacement text; supports backreferences "
                                    "like \\1. Leave empty to remove matched string"
                                ),
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
