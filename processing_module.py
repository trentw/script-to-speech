import yaml
from typing import Dict, List, Tuple
import importlib
from processing_submodule import ProcessingSubModule


class ProcessingModule:
    def __init__(self, config_path: str):
        with open(config_path, 'r') as config_file:
            self.config = yaml.safe_load(config_file)
        self.submodules = self._initialize_submodules()

    def _initialize_submodules(self) -> List[ProcessingSubModule]:
        submodules = []
        for submodule_config in self.config.get('submodules', []):
            module_name = submodule_config['name']
            config = submodule_config.get('config', {})

            try:
                module = importlib.import_module(
                    f"submodules.{module_name}_submodule")
                class_name = ''.join(word.capitalize()
                                     for word in module_name.split('_')) + 'SubModule'
                submodule_class = getattr(module, class_name)
                submodules.append(submodule_class(config))
            except (ImportError, AttributeError) as e:
                print(f"Error loading submodule {module_name}: {e}")

        return submodules

    def process_chunk(self, json_chunk: Dict) -> Tuple[Dict, bool]:
        modified_chunk = json_chunk
        was_modified = False
        for submodule in self.submodules:
            result, submodule_modified = submodule.process(modified_chunk)
            modified_chunk = result
            was_modified = was_modified or submodule_modified
        return modified_chunk, was_modified
