"""Registry of available text processors and preprocessors.

The processing pipeline loads processors dynamically by name (see
TextProcessorManager), so the set of available processors exists only
implicitly as modules on disk. This registry makes that set explicit for
consumers that need to enumerate processors -- primarily the GUI, which
lists them in its configuration editor and renders their config schemas.

The name lists are static (rather than scanned from the filesystem) because
directory scanning is unreliable inside frozen PyInstaller builds, while
importing by name works there. A test asserts the lists match the modules
on disk so a newly added processor can't be silently forgotten.
"""

import importlib
from typing import List, Literal, Type, Union

from .text_preprocessor_base import TextPreProcessor
from .text_processor_base import TextProcessor

ProcessorKind = Literal["preprocessor", "processor"]

AVAILABLE_PREPROCESSORS: List[str] = [
    "skip_and_merge",
    "dual_dialogue",
    "extract_dialogue_parentheticals",
    "speaker_merge",
]

AVAILABLE_PROCESSORS: List[str] = [
    "skip_empty",
    "text_substitution",
    "pattern_replace",
    "capitalization_transform",
]

# Fields present on every dialogue chunk (see parser.screenplay_parser.Chunk)
CHUNK_FIELDS: List[str] = ["type", "speaker", "text", "raw_text"]


def get_chunk_types() -> List[str]:
    """Get all dialogue chunk types produced by the screenplay parser."""
    from ..parser.screenplay_parser import State

    return [state.name.lower() for state in State]


def load_processor_class(
    kind: ProcessorKind, name: str
) -> Union[Type[TextProcessor], Type[TextPreProcessor]]:
    """Load a processor / preprocessor class by its config name.

    Follows the naming convention used in config files: module
    {name}_{kind}.py containing class {CamelCase(name)}{Processor|PreProcessor}
    (e.g. "skip_empty" -> processors/skip_empty_processor.py, SkipEmptyProcessor).

    Args:
        kind: "preprocessor" or "processor"
        name: Snake_case processor name as used in config files

    Returns:
        The processor class

    Raises:
        ValueError: If the module or class cannot be loaded
    """
    if kind == "preprocessor":
        module_path = (
            f"script_to_speech.text_processors.preprocessors.{name}_preprocessor"
        )
        class_suffix = "PreProcessor"
    elif kind == "processor":
        module_path = f"script_to_speech.text_processors.processors.{name}_processor"
        class_suffix = "Processor"
    else:
        raise ValueError(f"Unknown processor kind: {kind}")

    class_name = "".join(word.capitalize() for word in name.split("_")) + class_suffix

    try:
        module = importlib.import_module(module_path)
        loaded_class = getattr(module, class_name)
    except (ImportError, AttributeError) as e:
        raise ValueError(f"Error loading {kind} {name}: {e}")

    return loaded_class  # type: ignore[no-any-return]
