"""CLI for alphabetically sorting the voices in a voice library ``voices.yaml``.

This sorts the voice keys under the top-level ``voices:`` mapping into alphabetical
order while preserving the source file **byte-for-byte** otherwise. It works on raw
text rather than round-tripping through a YAML parser, so every block keeps its exact
spacing, quoting, comments, and value formatting -- only the order of the voice blocks
changes.

Only the ``voices:`` mapping is reordered. Other top-level sections (e.g.
``provider_metadata:``, which the elevenlabs files carry) are left exactly where they
are, even though they also contain indent-2 keys. A voice block is detected as a line
indented exactly two spaces that ends a key (``^  <key>:``) *within* the voices
section; it runs from its key line up to (but not including) the next voice key (or the
end of the section), so all nested content travels with it untouched.

Note: a blank line or comment immediately above a voice key is treated as that voice's
leading lines and moves with it when sorted, so a ``# Name - ...`` comment stays
attached to the voice it documents (the openai files use this convention). As a safety
net, the tool parses both the input and the sorted output and refuses to write unless
they are identical data -- so any structural surprise fails loudly instead of
corrupting a file.

By design this never overwrites the input -- it writes to a separate file (default
``<input stem>.sorted.yaml`` beside the input) so the result can be reviewed/diffed
before replacing the original.
"""

import argparse
import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import yaml

# A voice key inside the voices mapping: exactly two leading spaces, then a key.
_VOICE_KEY_RE = re.compile(r"^  (\S[^:]*):")
# The top-level voices mapping introducer (column 0, optional trailing comment).
_VOICES_RE = re.compile(r"^voices:\s*(#.*)?$")
# A new top-level key/section: a non-space, non-comment character at column 0.
# Blank lines and ``#`` comments do NOT end the voices section.
_TOP_LEVEL_KEY_RE = re.compile(r"^[^\s#]")


def _is_blank_or_comment(line: str) -> bool:
    """True for an empty/whitespace-only line or a ``#`` comment line."""
    stripped = line.strip()
    return stripped == "" or stripped.startswith("#")


def split_voice_section(text: str) -> Tuple[str, List[Tuple[str, str]], str]:
    """Split a voices file into ``(prefix, blocks, suffix)`` around the voice entries.

    Only the voice blocks inside the top-level ``voices:`` mapping are isolated; any
    other top-level section (before or after ``voices:``) stays in ``prefix`` /
    ``suffix`` untouched.

    A run of blank/comment lines immediately above a voice key is treated as that
    voice's **leading** lines and travels with it (the openai files document each voice
    with a ``# Name - ...`` comment right above its key). Blank lines *inside* a voice's
    body stay with that voice, because they are followed by more of its indented content
    rather than by the next key.

    Args:
        text: Full contents of a ``voices.yaml`` file.

    Returns:
        ``(prefix, blocks, suffix)`` where ``prefix`` is everything up to and including
        the ``voices:`` line, ``blocks`` is a list of ``(key, block_text)`` voice tuples
        in source order (each including its leading comment/blank run), and ``suffix`` is
        any trailing blank/comment lines after the last voice plus everything from the
        next top-level section onward. ``prefix + "".join(block_text...) + suffix``
        reproduces ``text`` exactly. If there is no ``voices:`` mapping with entries,
        ``blocks`` is empty, ``prefix == text``, and ``suffix == ""``.
    """
    lines = text.splitlines(keepends=True)

    voices_index = next(
        (i for i, line in enumerate(lines) if _VOICES_RE.match(line)), None
    )
    if voices_index is None:
        return text, [], ""

    # The voices section ends at the next top-level key (or end of file).
    section_end = len(lines)
    for j in range(voices_index + 1, len(lines)):
        if _TOP_LEVEL_KEY_RE.match(lines[j]):
            section_end = j
            break

    blocks: List[Tuple[str, List[str]]] = []
    current: Optional[Tuple[str, List[str]]] = None
    # Blank/comment lines whose owner is not yet known: they belong to the next voice
    # if a key comes before any body content, otherwise to the current voice's body.
    pending: List[str] = []

    for line in lines[voices_index + 1 : section_end]:
        key_match = _VOICE_KEY_RE.match(line)
        if key_match:
            current = (key_match.group(1), [*pending, line])
            pending = []
            blocks.append(current)
        elif _is_blank_or_comment(line) or current is None:
            pending.append(line)
        else:
            current[1].extend(pending)
            pending = []
            current[1].append(line)

    if not blocks:
        return text, [], ""

    prefix = "".join(lines[: voices_index + 1])
    # Any still-pending lines are trailing blank/comment lines after the last voice's
    # body; keep them at the end of the section rather than moving them with a voice.
    suffix = "".join(pending) + "".join(lines[section_end:])
    return prefix, [(key, "".join(block)) for key, block in blocks], suffix


def sort_voices_text(text: str) -> str:
    """Return ``text`` with the ``voices:`` blocks sorted alphabetically by key.

    Sorting is a pure text reordering of whole blocks, so all formatting -- and every
    other top-level section -- is preserved. If the file contains no voice blocks the
    text is returned unchanged.
    """
    prefix, blocks, suffix = split_voice_section(text)
    if not blocks:
        return text
    sorted_blocks = sorted(blocks, key=lambda block: block[0])
    return prefix + "".join(block_text for _, block_text in sorted_blocks) + suffix


def _assert_data_preserved(original_text: str, sorted_text: str) -> None:
    """Raise ValueError unless both texts parse to identical YAML data.

    This guards against the text reordering ever altering content (not just order).
    """
    if yaml.safe_load(original_text) != yaml.safe_load(sorted_text):
        raise ValueError(
            "Sorted output does not parse to the same data as the input. "
            "Refusing to write -- this indicates the file does not match the "
            "expected 'voices:' + two-space-indented-key structure."
        )


def sort_voices_file(
    input_path: Path,
    output_path: Optional[Path] = None,
    check: bool = False,
) -> int:
    """Sort the voices in ``input_path`` and write the result to a new file.

    Args:
        input_path: Path to the ``voices.yaml`` to sort.
        output_path: Where to write the sorted file. Defaults to
            ``<input stem>.sorted.yaml`` beside the input. Must differ from the input.
        check: If True, do not write anything; print whether the file is already
            sorted and return 0 if sorted, 1 if not.

    Returns:
        Process exit code (0 on success, 1 on error / not-sorted in check mode).
    """
    if not input_path.is_file():
        print(f"Error: input file not found: {input_path}")
        return 1

    text = input_path.read_text()
    _, blocks, _ = split_voice_section(text)

    if not blocks:
        print(
            f"Error: no voices found under 'voices:' in {input_path}. "
            "Is this a voice library voices.yaml?"
        )
        return 1

    keys = [key for key, _ in blocks]
    already_sorted = keys == sorted(keys)

    sorted_text = sort_voices_text(text)
    _assert_data_preserved(text, sorted_text)

    if check:
        if already_sorted:
            print(f"✓ {input_path} is already sorted ({len(keys)} voices).")
            return 0
        print(f"✗ {input_path} is NOT sorted ({len(keys)} voices).")
        return 1

    if output_path is None:
        output_path = input_path.with_name(
            f"{input_path.stem}.sorted{input_path.suffix}"
        )

    if output_path.resolve() == input_path.resolve():
        print(
            "Error: --output must differ from the input file (this tool never overwrites the input)."
        )
        return 1

    output_path.write_text(sorted_text)
    state = "already-sorted" if already_sorted else "sorted"
    print(f"✓ Wrote {state} voices ({len(keys)}) to {output_path}")
    return 0


def main() -> None:
    """Main entry point for the sts-sort-voice-library-data command."""
    parser = argparse.ArgumentParser(
        description=(
            "Alphabetically sort the top-level voice keys in a voice library "
            "voices.yaml, preserving exact formatting. Writes to a new file; never "
            "overwrites the input."
        )
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Path to the voices.yaml to sort.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help=(
            "Output path. Defaults to '<input stem>.sorted.yaml' beside the input. "
            "Must differ from the input."
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Read-only: exit 0 if already sorted, 1 if not. Writes nothing.",
    )

    args = parser.parse_args()
    sys.exit(sort_voices_file(args.input, args.output, args.check))


if __name__ == "__main__":
    main()
