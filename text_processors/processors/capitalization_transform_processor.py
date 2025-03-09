import re
from typing import Dict, List, Tuple

from ..text_processor_base import TextProcessor


class CapitalizationTransformProcessor(TextProcessor):
    """Processor that transforms text case based on configuration rules."""

    def _transform_case(self, text: str, case_type: str) -> str:
        """Transform text to specified case type."""
        if case_type == "upper_case":
            return text.upper()
        elif case_type == "lower_case":
            return text.lower()
        elif case_type == "sentence_case":
            return text.capitalize()
        else:
            # Default to no transformation for invalid case types
            return text

    def process(self, json_chunk: Dict) -> Tuple[Dict, bool]:
        """Process the chunk according to transformation rules."""
        modified_chunk = json_chunk.copy()
        changes_made = False

        chunk_type = json_chunk.get("type")
        text = json_chunk.get("text", "")

        for transform in self.config.get("transformations", []):
            # Skip if required fields are missing
            if "chunk_type" not in transform or "case" not in transform:
                continue

            # Check if chunk type matches
            if chunk_type != transform.get("chunk_type"):
                continue

            # Check text_must_contain_string if specified
            if (
                transform.get("text_must_contain_string")
                and transform.get("text_must_contain_string") not in text
            ):
                continue

            # Check text_must_contain_pattern if specified
            if transform.get("text_must_contain_pattern"):
                try:
                    pattern = re.compile(transform.get("text_must_contain_pattern"))
                    if not pattern.search(text):
                        continue
                except re.error:
                    continue

            # Apply case transformation
            modified_text = self._transform_case(text, transform.get("case"))
            if modified_text != text:
                modified_chunk["text"] = modified_text
                text = modified_text  # Update text for potential subsequent transforms
                changes_made = True

        return modified_chunk, changes_made

    def get_transformed_fields(self) -> List[str]:
        """Return list of fields that this processor transforms."""
        return ["text"]

    def validate_config(self) -> bool:
        """Validate the processor configuration."""
        if not isinstance(self.config.get("transformations"), list):
            return False

        valid_cases = {"upper_case", "lower_case", "sentence_case"}

        for transform in self.config.get("transformations", []):
            # Check required fields
            if "chunk_type" not in transform or "case" not in transform:
                return False

            # Validate case type
            if transform.get("case") not in valid_cases:
                return False

            # Validate optional pattern if present
            if "text_must_contain_pattern" in transform:
                try:
                    re.compile(transform.get("text_must_contain_pattern"))
                except re.error:
                    return False

        return True
