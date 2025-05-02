import importlib
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Type, Union, cast

import yaml

from ..utils.logging import get_screenplay_logger
from .text_preprocessor_base import TextPreProcessor
from .text_processor_base import TextProcessor

# Get logger for this module
logger = get_screenplay_logger("text_processors.manager")


class TextProcessorManager:
    """Manages the loading and execution of text processors and pre-processors."""

    def __init__(self, config_paths: List[Path]):
        """
        Initialize with multiple config files that will be processed in order.

        Args:
            config_paths: List of Path objects to YAML config files
        """
        self.configs = []
        for path in config_paths:
            with open(path, "r") as config_file:
                self.configs.append(yaml.safe_load(config_file))

        self.preprocessors = self._initialize_preprocessors()
        self.processors = self._initialize_processors()
        self.preprocessed_chunks: Optional[List[Dict]] = None

    def _filter_by_mode(
        self, processors: List[Union[TextProcessor, TextPreProcessor]]
    ) -> List[Union[TextProcessor, TextPreProcessor]]:
        """
        Filter processors based on their multi_config_mode.

        For "override" mode, only keep the last instance of each processor class.
        For "chain" mode, keep all instances.
        """
        result: List[Union[TextProcessor, TextPreProcessor]] = []
        seen_override_classes = set()

        # Process in reverse to handle override mode (keep last instance)
        for processor in reversed(processors):
            processor_class = processor.__class__

            if processor.multi_config_mode == "override":
                if processor_class not in seen_override_classes:
                    seen_override_classes.add(processor_class)
                    result.insert(
                        0, processor
                    )  # Insert at start to maintain original order
            else:  # "chain" mode
                result.insert(
                    0, processor
                )  # Insert at start to maintain original order

        return result

    def _initialize_preprocessors(self) -> List[TextPreProcessor]:
        """Initialize pre-processors from all configurations."""
        all_preprocessors = []

        # Process each config file in order
        for config in self.configs:
            for preproc_config in config.get("preprocessors", []):
                module_name = preproc_config["name"]
                config_params = preproc_config.get("config", {})

                try:
                    # Import from preprocessors subdirectory
                    module = importlib.import_module(
                        f"script_to_speech.text_processors.preprocessors.{module_name}_preprocessor"
                    )
                    class_name = (
                        "".join(word.capitalize() for word in module_name.split("_"))
                        + "PreProcessor"
                    )
                    preprocessor_class = getattr(module, class_name)

                    # Create and validate pre-processor
                    preprocessor = preprocessor_class(config_params)
                    if not preprocessor.validate_config():
                        raise ValueError(
                            f"Invalid configuration for pre-processor {module_name}"
                        )

                    all_preprocessors.append(preprocessor)
                    logger.info(
                        f"Successfully loaded pre-processor: {module_name} from config"
                    )
                except Exception as e:
                    error_msg = f"Error loading pre-processor {module_name}: {e}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)

        # Apply mode-based filtering and cast the result
        filtered = self._filter_by_mode(all_preprocessors)
        return cast(List[TextPreProcessor], filtered)

    def _initialize_processors(self) -> List[TextProcessor]:
        """Initialize text processors from all configurations."""
        all_processors = []

        # Process each config file in order
        for config in self.configs:
            for processor_config in config.get("processors", []):
                module_name = processor_config["name"]
                config_params = processor_config.get("config", {})

                try:
                    # Import from processors subdirectory
                    module = importlib.import_module(
                        f"script_to_speech.text_processors.processors.{module_name}_processor"
                    )
                    # Convert module_name to class name (e.g., skip_empty -> SkipEmptyProcessor)
                    class_name = (
                        "".join(word.capitalize() for word in module_name.split("_"))
                        + "Processor"
                    )
                    processor_class = getattr(module, class_name)

                    processor = processor_class(config_params)
                    if not processor.validate_config():
                        raise ValueError(
                            f"Invalid configuration for processor {module_name}"
                        )

                    all_processors.append(processor)
                    logger.info(
                        f"Successfully loaded processor: {module_name} from config"
                    )
                except Exception as e:
                    error_msg = f"Error loading processor {module_name}: {e}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)

        # Apply mode-based filtering and cast the result
        filtered = self._filter_by_mode(all_processors)
        return cast(List[TextProcessor], filtered)

    def process_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """
        Convenience method to process chunks through both
        pre-processors and processors.

        Args:
            chunks: List of input chunks

        Returns:
            List[Dict]: The fully processed chunks

        Raises:
            ValueError: If processing fails
        """
        # Run pre-processors
        processed_chunks = self.preprocess_chunks(chunks)

        # Run processors on each chunk
        final_chunks = []
        for chunk in processed_chunks:
            modified_chunk, _ = self.process_chunk(chunk)
            final_chunks.append(modified_chunk)

        return final_chunks

    def preprocess_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """
        Run all pre-processors on the chunks.

        Args:
            chunks: The initial list of chunks from the screenplay

        Returns:
            List[Dict]: The pre-processed chunks

        Raises:
            ValueError: If any pre-processing step fails
        """
        processed_chunks = chunks
        for preprocessor in self.preprocessors:
            processed_chunks, modified = preprocessor.process(processed_chunks)
            if processed_chunks is None:
                error_msg = (
                    f"Pre-processor {preprocessor.__class__.__name__} returned None"
                )
                logger.error(error_msg)
                raise ValueError(error_msg)
            if modified:
                logger.info(
                    f"Pre-processor {preprocessor.__class__.__name__} modified chunks"
                )

        self.preprocessed_chunks = processed_chunks
        return processed_chunks

    def process_chunk(self, chunk: Dict) -> Tuple[Dict, bool]:
        """
        Process a single chunk through all processors.

        Args:
            chunk: The chunk to process

        Returns:
            Tuple[Dict, bool]: Processed chunk and whether it was modified
        """
        if self.preprocessed_chunks is None:
            error_msg = (
                "Must call preprocess_chunks before processing individual chunks"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        modified_chunk = chunk
        was_modified = False
        for processor in self.processors:
            result, processor_modified = processor.process(modified_chunk)
            modified_chunk = result
            was_modified = was_modified or processor_modified

        return modified_chunk, was_modified
