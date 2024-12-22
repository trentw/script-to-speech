from typing import Dict, Tuple, List
from ..text_processor_base import TextProcessor
import re


class PatternReplaceProcessor(TextProcessor):
    """
    Processor that replaces text in fields based on pattern matches in other fields.
    """

    def __init__(self, config: Dict):
        super().__init__(config)
        self.replacements = self._prepare_replacements()

    def _prepare_replacements(self):
        """Prepare and compile regex patterns for each replacement."""
        replacements = []
        for replacement in self.config.get('replacements', []):
            try:
                replacements.append({
                    'match_field': replacement['match_field'],
                    'match_pattern': re.compile(replacement['match_pattern']),
                    'replace_field': replacement['replace_field'],
                    'replace_pattern': replacement['replace_pattern']
                })
            except re.error as e:
                raise ValueError(f"Invalid regex pattern in replacement: {e}")
        return replacements

    def process(self, json_chunk: Dict) -> Tuple[Dict, bool]:
        modified_chunk = json_chunk.copy()
        changes_made = False

        for replacement in self.replacements:
            # Check if the match field exists and matches the pattern
            if (replacement['match_field'] in json_chunk and
                    replacement['match_pattern'].match(str(json_chunk[replacement['match_field']]))):

                # If match is found and replace field exists, perform replacement
                if replacement['replace_field'] in json_chunk:
                    original_text = str(
                        json_chunk[replacement['replace_field']])
                    modified_text = re.sub(
                        replacement['replace_pattern'],
                        '',  # Replace with empty string
                        original_text
                    )

                    if modified_text != original_text:
                        modified_chunk[replacement['replace_field']
                                       ] = modified_text
                        changes_made = True

        return modified_chunk, changes_made

    def get_transformed_fields(self) -> List[str]:
        """Return list of all fields that could be transformed."""
        return list(set(r['replace_field'] for r in self.replacements))

    def validate_config(self) -> bool:
        if not isinstance(self.config.get('replacements'), list):
            return False

        required_keys = {'match_field', 'match_pattern',
                         'replace_field', 'replace_pattern'}

        for replacement in self.config.get('replacements', []):
            # Verify all required keys are present
            if not all(key in replacement for key in required_keys):
                return False

            # Verify all values are strings
            if not all(isinstance(replacement[key], str) for key in required_keys):
                return False

            # Verify patterns are valid regex
            try:
                re.compile(replacement['match_pattern'])
                re.compile(replacement['replace_pattern'])
            except re.error:
                return False

        return True
