from typing import Dict, List, Tuple, Set
from ..text_preprocessor_base import TextPreProcessor


class SkipAndMergePreProcessor(TextPreProcessor):
    """
    Pre-processor that removes chunks of specified types and merges 
    adjacent chunks around removed chunks where appropriate.
    """
    # Types that can be merged if they're the same type
    MERGEABLE_TYPES = {'scene_heading', 'action', 'dialog', 'dialog_modifier'}

    def validate_config(self) -> bool:
        """Validate that skip_types is a list."""
        return isinstance(self.config.get('skip_types'), list)

    def _can_merge_chunks(self, chunk1: Dict, chunk2: Dict) -> bool:
        """
        Determine if two chunks can be merged.

        Chunks can be merged if:
        - They are the same type
        - Type is in MERGEABLE_TYPES
        - For dialog: they have the same speaker
        """
        if chunk1['type'] != chunk2['type']:
            return False

        if chunk1['type'] not in self.MERGEABLE_TYPES:
            return False

        # For dialog, speakers must match
        if chunk1['type'] == 'dialog':
            return chunk1.get('speaker') == chunk2.get('speaker')

        return True

    def _merge_chunks(self, chunk1: Dict, chunk2: Dict) -> Dict:
        """
        Merge two compatible chunks into one.
        Preserves all fields, concatenating text with a space.
        """
        merged = chunk1.copy()
        merged['text'] = f"{chunk1['text']} {chunk2['text']}"
        merged['raw_text'] = f"{chunk1['raw_text']}\n{chunk2['raw_text']}"
        return merged

    def process(self, chunks: List[Dict]) -> Tuple[List[Dict], bool]:
        """
        Process chunks by removing specified types and merging adjacent chunks
        around removed chunks where appropriate.

        Args:
            chunks: List of all text chunks from the screenplay

        Returns:
            Tuple[List[Dict], bool]:
                - Modified list of chunks
                - Boolean indicating whether any changes were made
        """
        if not chunks:
            return chunks, False

        skip_types = set(self.config.get('skip_types', []))
        result_chunks = []
        made_changes = False
        i = 0

        while i < len(chunks):
            current_chunk = chunks[i]

            # Skip chunks of specified types
            if current_chunk['type'] in skip_types:
                made_changes = True

                # Try to merge chunks on either side of the skipped chunk
                if result_chunks and i + 1 < len(chunks):
                    prev_chunk = result_chunks[-1]
                    next_chunk = chunks[i + 1]

                    if self._can_merge_chunks(prev_chunk, next_chunk):
                        # Remove the previous chunk (we'll add the merged one later)
                        result_chunks.pop()
                        # Merge chunks and add to result
                        merged_chunk = self._merge_chunks(
                            prev_chunk, next_chunk)
                        result_chunks.append(merged_chunk)
                        i += 2  # Skip both current and next chunk
                        print(
                            f"Merged chunks around removed {current_chunk['type']}. Text: {current_chunk['text']}")
                        continue

                i += 1  # Skip current chunk
                continue

            # Add current chunk without trying to merge
            result_chunks.append(current_chunk)
            i += 1

        return result_chunks, made_changes
