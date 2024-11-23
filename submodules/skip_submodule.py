from typing import Dict, Tuple, List
from processing_submodule import ProcessingSubModule


class SkipSubModule(ProcessingSubModule):
    def process(self, json_chunk: Dict) -> Tuple[Dict, bool]:
        if json_chunk.get('type') in self.config.get('skip_types', []):
            modified_chunk = json_chunk.copy()
            modified_chunk['text'] = ''
            return modified_chunk, True
        return json_chunk, False

    def get_transformed_fields(self) -> List[str]:
        return ['text']

    def validate_config(self) -> bool:
        return isinstance(self.config.get('skip_types'), list)
