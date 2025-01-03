import yaml
from typing import Dict, List, Tuple
import importlib
from .text_processor_base import TextProcessor
from .text_preprocessor_base import TextPreProcessor


class TextProcessorManager:
    """Manages the loading and execution of text processors and pre-processors."""

    def __init__(self, config_path: str):
        with open(config_path, 'r') as config_file:
            self.config = yaml.safe_load(config_file)
        self.preprocessors = self._initialize_preprocessors()
        self.processors = self._initialize_processors()
        self.preprocessed_chunks = None

    def _initialize_preprocessors(self) -> List[TextPreProcessor]:
        """Initialize pre-processors based on configuration."""
        preprocessors = []
        for preproc_config in self.config.get('preprocessors', []):
            module_name = preproc_config['name']
            config = preproc_config.get('config', {})

            try:
                # Import from preprocessors subdirectory
                module = importlib.import_module(
                    f"text_processors.preprocessors.{module_name}_preprocessor")
                class_name = ''.join(word.capitalize()
                                     for word in module_name.split('_')) + 'PreProcessor'
                preprocessor_class = getattr(module, class_name)

                # Create and validate pre-processor
                preprocessor = preprocessor_class(config)
                if not preprocessor.validate_config():
                    raise ValueError(
                        f"Invalid configuration for pre-processor {module_name}")

                preprocessors.append(preprocessor)
                print(f"Successfully loaded pre-processor: {module_name}")
            except Exception as e:
                raise ValueError(
                    f"Error loading pre-processor {module_name}: {e}")

        return preprocessors

    def _initialize_processors(self) -> List[TextProcessor]:
        """Initialize text processors based on configuration."""
        processors = []
        for processor_config in self.config.get('processors', []):
            module_name = processor_config['name']
            config = processor_config.get('config', {})

            try:
                # Import from processors subdirectory
                module = importlib.import_module(
                    f"text_processors.processors.{module_name}_processor")
                # Convert module_name to class name (e.g., skip_empty -> SkipEmptyProcessor)
                class_name = ''.join(word.capitalize()
                                     for word in module_name.split('_')) + 'Processor'
                processor_class = getattr(module, class_name)
                processors.append(processor_class(config))
                print(f"Successfully loaded processor: {module_name}")
            except (ImportError, AttributeError) as e:
                print(f"Error loading processor {module_name}: {e}")

        return processors

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
                raise ValueError(
                    f"Pre-processor {preprocessor.__class__.__name__} returned None")
            if modified:
                print(
                    f"Pre-processor {preprocessor.__class__.__name__} modified chunks")

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
            raise ValueError(
                "Must call preprocess_chunks before processing individual chunks")

        modified_chunk = chunk
        was_modified = False
        for processor in self.processors:
            result, processor_modified = processor.process(modified_chunk)
            modified_chunk = result
            was_modified = was_modified or processor_modified

        return modified_chunk, was_modified
