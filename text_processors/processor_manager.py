import yaml
from typing import Dict, List, Tuple
import importlib
from .text_processor_base import TextProcessor


class TextProcessorManager:
    """Manages the loading and execution of text processors."""

    def __init__(self, config_path: str):
        with open(config_path, 'r') as config_file:
            self.config = yaml.safe_load(config_file)
        self.processors = self._initialize_processors()

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

    def process_chunk(self, text_chunk: Dict) -> Tuple[Dict, bool]:
        """Process a text chunk through all configured processors."""
        modified_chunk = text_chunk
        was_modified = False
        for processor in self.processors:
            result, processor_modified = processor.process(modified_chunk)
            modified_chunk = result
            was_modified = was_modified or processor_modified
        return modified_chunk, was_modified
