from typing import Dict, List, Tuple
from ..text_preprocessor_base import TextPreProcessor
import re


class DualDialogPreProcessor(TextPreProcessor):
    """
    Pre-processor that splits dual dialog blocks into sequential dialog blocks,
    creating proper speaker attributions for each.
    """
    MIN_SPEAKER_SPACING = 5  # Minimum spaces between speakers
    MIN_DIALOG_SPACING = 3   # Minimum spaces to identify right speaker's text

    def validate_config(self) -> bool:
        """No user configuration, always return true"""
        return True

    def process(self, chunks: List[Dict]) -> Tuple[List[Dict], bool]:
        """Process chunks by converting dual dialog into sequential dialog."""
        if not chunks:
            return chunks, False

        result_chunks = []
        i = 0
        made_changes = False

        while i < len(chunks):
            current_chunk = chunks[i]

            # Look for dual speaker attribution
            if current_chunk['type'] == 'dual_speaker_attribution' and i + 1 < len(chunks):
                next_chunk = chunks[i + 1]

                # Check if followed by dual dialog
                if next_chunk['type'] == 'dual_dialog':
                    made_changes = True
                    # Process the dual dialog pair and create individual dialog chunks
                    new_chunks = self._process_dual_dialog_pair(
                        current_chunk, next_chunk)
                    result_chunks.extend(new_chunks)
                    i += 2  # Skip both chunks
                    continue

            # Keep non-dual-dialog chunks as is
            result_chunks.append(current_chunk)
            i += 1

        return result_chunks, made_changes

    def _process_dual_dialog_pair(self, speaker_chunk: Dict, dialog_chunk: Dict) -> List[Dict]:
        """Process a pair of dual speaker attribution and dual dialog chunks."""
        # Get left and right speakers (both full text and stripped versions)
        left_speaker_full, right_speaker_full = self._split_speakers_full(
            speaker_chunk['text'])
        left_speaker_stripped = re.sub(
            r'\([^)]*\)', '', left_speaker_full).strip()
        right_speaker_stripped = re.sub(
            r'\([^)]*\)', '', right_speaker_full).strip()

        # Get left and right dialog
        left_dialog, right_dialog = self._split_dialog(
            dialog_chunk['raw_text'])

        # Create chunks for both speakers
        chunks = []

        # Left speaker chunks
        if left_dialog.strip():
            # Speaker attribution for left speaker
            chunks.append({
                'type': 'speaker_attribution',
                'speaker': '',  # Speaker attributions have empty speaker field
                'text': left_speaker_full,
                'raw_text': speaker_chunk['raw_text']
            })

            # Dialog for left speaker
            chunks.append({
                'type': 'dialog',
                'speaker': left_speaker_stripped,
                'text': left_dialog.strip(),
                'raw_text': dialog_chunk['raw_text']
            })

        # Right speaker chunks
        if right_dialog.strip():
            # Speaker attribution for right speaker
            chunks.append({
                'type': 'speaker_attribution',
                'speaker': '',  # Speaker attributions have empty speaker field
                'text': right_speaker_full,
                'raw_text': speaker_chunk['raw_text']
            })

            # Dialog for right speaker
            chunks.append({
                'type': 'dialog',
                'speaker': right_speaker_stripped,
                'text': right_dialog.strip(),
                'raw_text': dialog_chunk['raw_text']
            })

        return chunks

    def _split_speakers_full(self, speaker_text: str) -> Tuple[str, str]:
        """
        Split dual speaker attribution into left and right speakers.
        Preserves parentheticals in speaker names.
        """
        # Split on multiple spaces
        parts = [p for p in re.split(
            r'\s{%d,}' % self.MIN_SPEAKER_SPACING, speaker_text) if p]

        if len(parts) != 2:
            raise ValueError(f"Could not split speakers from: {speaker_text}")

        return parts[0], parts[1]

    def _split_dialog(self, raw_dialog: str) -> Tuple[str, str]:
        """Split dual dialog into left and right parts."""
        lines = raw_dialog.split('\n')
        left_buffer = []
        right_buffer = []

        # Find left speaker's indentation from first line
        first_line = lines[0].rstrip()
        left_indent = len(first_line) - len(first_line.lstrip())

        for line in lines:
            line = line.rstrip()  # Remove trailing whitespace
            if not line:  # Skip empty lines
                continue

            # Get line's indentation
            indent = len(line) - len(line.lstrip())

            if indent == left_indent:
                # This line starts at left speaker position
                # Split it into left and right parts
                parts = [p for p in re.split(
                    r'\s{%d,}' % self.MIN_DIALOG_SPACING, line) if p]
                if parts:
                    left_buffer.append(parts[0])
                    if len(parts) > 1:
                        right_buffer.append(parts[-1])
            elif indent > left_indent + 10:  # Significantly indented, must be right speaker
                right_buffer.append(line.strip())

        return (
            ' '.join(left_buffer),
            ' '.join(right_buffer)
        )
