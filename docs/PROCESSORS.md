# Text Processing Pipeline

Script to Speech uses a flexible text processing pipeline to transform screenplay text before audio generation. This guide explains how processors work and how to configure them.

## Preprocessors vs Processors

### Preprocessors
- **Operate on**: Entire dialogue structure
- **When to use**: Modify data structure (merge / add / remove dialogue chunks, change dialogue chunk types, etc.)
- **Execution**: Run once on the whole file before processing
- **State**: Can maintain state between dialogue lines, as it operates on whole screenplay

### Processors
- **Operate on**: Individual text lines
- **When to use**: Modify spoken text (text substitution, capitalization, etc.)
- **Execution**: Run on each line during processing
- **State**: Completely stateless between calls

### Choosing Between Them
- **Use a Processor** when modifying how a line is spoken
- **Use a Preprocessor** when changing how data is structured
- **Default to Processor** when possible for simplicity and predictability

## Configuration Flow

Any number of text processors can be chained together in the processing pipeline. Output of one text preprocessor / processor is input to the next. Within a specific text preprocessor / processor, configs are ran in top-to-bottom order. Text processors are loaded using a specific precedence order:

1. **Command Line Configs**: Always take precedence
   ```bash
   uv run sts-generate-audio --processor-configs custom1.yaml custom2.yaml
   ```

2. **Matching Dialogue Chunk Config**: If exists, combines with default config
   - File: `input/[screenplay_name]/[screenplay_name]_processor_config.yaml`
   - Load order: `[DEFAULT_CONFIG, chunk_config]`

3. **Default Config Only**: No other configs found. Should be sufficient for most use cases
   - File: `src/script_to_speech/text_processors/configs/default_processor_config.yaml`

## Configuration Syntax

### Basic Structure

Preprocessors and processors each have their own configuration sections. Each preprocessor / processor is identified by `name`, and a `config` section

```yaml
preprocessors:
  - name: skip_and_merge
    config:
      skip_types:
        - page_number

processors:
  - name: text_substitution
    config:
      substitutions:
        - from: "INT."
          to: "Interior"
          fields:
            - text
```

### Multiple Instances of Preprocessor / Processor in Chained Configs
Processors support two modes when multiple instances of the same configuration are present. Check processor documentation for which mode a specific config operates under:

1. **Chain Mode**: Multiple instances run in sequence -- output from one is input to the next. This is the default mode that most preprocessors / processors operate under
   ```yaml
   # First substitution instance, transforms "INT." -> "Interior"
   processors:
     - name: text_substitution
       config:
         substitutions:
           - from: "INT."
             to: "Interior"
             fields:
               - text
   ```

   ```yaml
   # Second substitution instance
     - name: text_substitution
       config:
         substitutions:
           - from: "INT."
             to: "Interior Hall" # Won't have any effect as previous rule transformed all instances of "INT." to "Interior"
             fields:
               - text
   ```

2. **Override Mode**: Last instance replaces previous ones. Operation is only applied once, using the configuration of the last instance
   ```yaml
   # First configuration
   preprocessors:
     - name: dual_dialog
       config:
         min_speaker_spacing: 3
   ```

   ```yaml
   # Second configurtion
     - name: dual_dialog
       config:
         min_speaker_spacing: 8  # This one is used
   ```

## Available Preprocessors

### skip_and_merge
- **Purpose**: Remove specific chunk types and merge adjacent chunks if appropriate (e.g. if a page number bisects a line of dialog)
- **Run Mode**: Chain (multiple instances can be used together)
```yaml
preprocessors:
  - name: skip_and_merge
    config:
      skip_types:
        - page_number      # Example skip type     
```

### dual_dialog
- **Purpose**: Convert dual dialogue chunks into sequential dialogue
- **Run Mode**: Override (last instance wins)
```yaml
preprocessors:
  - name: dual_dialog
    config:
      min_speaker_spacing: 3    # Minimum spaces between speaker attributions
      min_dialog_spacing: 2     # Minimum spaces between dialog columns
```

### extract_dialog_parentheticals
- **Purpose**: Extract parentheticals from dialogue so that they are spoken by the "default" speaker instead of the assigned speaker (e.g. for the dialog line "What are you doing? (gasps) Don't come any closer!" )
- **Run Mode**: Chain (multiple instances can be used together)

```yaml
# Basic config to extract any parentheticals 10 words 
preprocessors:
  - name: extract_dialog_parentheticals
    config:
      max_words: 10            # (optional) Skip extracting parentheticals that have more than 10 words
```

```yaml
# Advanced "allow list" config to extract only specific parantheticals  containing less than 10 words
preprocessors:
  - name: extract_dialog_parentheticals
    config:
      max_words: 10            # (optional) Skip extracting parentheticals that have more than 10 words
      extract_only:            # (optional) extract only the following parentheticals
        - pause                # exact match, case insensitive, for (pause) / (PAUSE) / etc.
        - in irish*            # Wildcard for partial matches (matches "in irish", "in irish accent", "in irish scream", etc.)
```

```yaml
# Advanced "deny list" config to extract all parentheticals, except those listed, that contain less than 10 words
preprocessors:
  - name: extract_dialog_parentheticals
    config:
      max_words: 10            # Skip extracting parentheticals that have more than 10 words
      extract_all_except:      # (optional) extract all, except the following, parentheticals
        - pause                # exact match, case insensitive, for (pause) / (PAUSE) / etc.
        - in irish*            # Wildcard for partial matches (matches "in irish", "in irish accent", "in irish scream", etc.)
```

### speaker_merge
- **Purpose**: Merge speaker variations to canonical forms. Each instance of the child speaker will be replaced the parent. This allows for a cleaner voice configuration file (you collapse multiple voices into a single entry), and a more consistent experience for preprocessors / processors that have operation logic based on speaker (like the `skip_and_merge` preprocessor)
- **Run Mode**: Chain (multiple instances can be used together)
```yaml
preprocessors:
  - name: speaker_merge
    config:
      speakers_to_merge:
        BOB:
          - BO B
          - BOB OS
        ALICE:
          - ALICE CU
```

## Available Processors

### skip_empty
- **Purpose**: Replace the text content of specific chunks with empty text. For a variant that will merge the preceding / following text chunk around the empty chunk, if appropriate, see `skip_and_merge` preprocessor
- **Run Mode**: Chain (multiple instances can be used together)
```yaml
processors:
  - name: skip_empty
    config:
      skip_types:
        - page_number
```

### text_substitution
- **Purpose**: Replace specific text with substitution
- **Run Mode**: Chain (multiple instances can be used together)
```yaml
processors:
  - name: text_substitution
    config:
      substitutions:
        - from: "CONT'D"
          to: "CONTINUED"
          fields:
            - text         # Make replacements in the "text" field of dialogue chunks
```

### pattern_replace
- **Purpose**: Complex regex-based text replacement
- **Run Mode**: Chain (multiple instances can be used together)
```yaml
# Example to remove second occurrence of scene number in scene headings,
# e.g. "22 INT. HEADQUARTERS -- NIGHT 22" -> "22 INT. HEADQUARTERS -- NIGHT"
processors:
 - name: pattern_replace
    config:
      replacements:
        - match_field: "type"                 # Dialogue chunk type to check match_pattern (such as type, speaker, etc.)
          match_pattern: "^scene_heading$"    # If the type in match_field matches this pattern, then the dialogue chunk is eligible for substitution
          replace_field: "text"               # Field in dialogue chunk to apply regex
          # Regex to match text of the form "[number] [text] [same number]"
          replace_pattern: '^(?P<scene_num>[A-Z]?\d+(\.\d+)?)\b(.*)\b(?P=scene_num)$'
          replace_string: '\1\3'              # Replace "[number] [text] [same number]" with "[number] [text]"
```

### capitalization_transform
- **Purpose**: Change text case based on chunk type. Useful as some TTS providers treat all-upper-case text as "yelling". Supports `lower_case`, `upper_case`, and `sentence_case` (first letter of each sentence capitalized)
- **Run Mode**: Chain (multiple instances can be used together)
```yaml
processors:
  - name: capitalization_transform
    config:
      transformations:
        - chunk_type: speaker_attribution        # Dialogue chunk type to transform
          case: sentence_case
        - chunk_type: dialog_modifier
          case: lower_case
          text_must_contain_string: "(gasps)"    # (optional) Only apply transform when matching this string
```

## Custom Processor Configuration
There are a number of default preprocessors / processors that are applied by default and can be seen in the [default_processor_config.yaml](../src/script_to_speech/text_processors/configs/default_processor_config.yaml)

### Adding to the default_processor_config.yaml
Additional preprocessors / processors can be run in addition to the default by creating a processor_config file with the filename of `[screenplay_name]_processor_config.yaml` and placing it in the same directory 

### Replacing the default_processor_config.yaml
When `uv run sts-generate-audio` is run with the `--processor-configs` argument, only the supplied config(s) will be used

### Example Custom Config
If the following config was placed at `input/[screenplay_name]/[screenplay_name]_processor_config.yaml` these preprocessors / processors would be run in addition to the defaults.

The following call would use this custom config instead of the default (assuming the custom config is named `my_custom_config.yaml`)
```bash
uv run sts-generate-audio /input/[screenplay_name]/[screenplay].json \
   --tts-config /input/[screenplay_name]/[screenplay]_voice_config.yaml \
   --processor-configs my_custom_config.yaml
```

```yaml
# Custom processor configuration
preprocessors:
  - name: extract_dialog_parentheticals
    config:
      max_words: 5
      extract_only:
        - quietly
        - whisper*

processors:
  - name: text_substitution
    config:
      substitutions:
        # Custom abbreviations
        - from: "CU"
          to: "close up"
          fields:
            - text
        - from: "ECU"
          to: "extreme close up"
          fields:
            - text
  
  - name: pattern_replace
    config:
      replacements:
        # Remove scene numbers from headings
        - match_field: type
          match_pattern: "^scene_heading$"
          replace_field: text
          replace_pattern: '^\d+\s*'
          replace_string: ''
```

## Creating Custom Processors

### Adding a New Processor
1. Create a new file in `src/script_to_speech/text_processors/processors/`
2. Name it `[processor_name]_processor.py`
3. Implement the `TextProcessor` base class:

```python
from ..text_processor_base import TextProcessor

class MyCustomProcessor(TextProcessor):
    def process(self, json_chunk: Dict) -> Tuple[Dict, bool]:
        # Your processing logic here for individual dialogue chunk
        modified_chunk = json_chunk.copy()

        # Track if your Processor made changes to the chunk
        changes_made = False

        # Get configuration info from the .yaml config; 
        # this example would iterate through each entry in a config item "actions"
        for action in self.config.get("actions", []):
          # ... modify the chunk based on the config ...
        return modified_chunk, changes_made
    
    @property
    def multi_config_mode(self) -> Literal["chain", "override"]:
        # Default mode is "chain"; set to "override" if needed
        return "override"

    def get_transformed_fields(self) -> List[str]:
        return ["text"]  # Fields this processor modifies
    
    def validate_config(self) -> bool:
        # Validate self.config for required fields, correct types, etc.
        return True
```

### Adding a New Preprocessor
1. Create a new file in `src/script_to_speech/text_processors/preprocessors/`
2. Name it `[preprocessor_name]_preprocessor.py`
3. Implement the `TextPreProcessor` base class:

```python
from ..text_preprocessor_base import TextPreProcessor

class MyCustomPreProcessor(TextPreProcessor):
    def process(self, chunks: List[Dict]) -> Tuple[List[Dict], bool]:
        # Your preprocessing logic here to modify the full list 
        # of dialog chunks
        result_chunks = []

        # Track if your Processor made changes to the chunk
        changes_made = False

        # Get configuration info from the .yaml config; 
        # this example would get the set of "actions" from a config item "actions"
        actions = set(self.config.get("actions", []))

        # Modify the chunk list, like the following
        while i < len(chunks):
          current_chunk = chunks[i]

          # ... modify the chunk based on the config ...

          result_chunks.append(current_chunk)

        return result, changes_made
    
    @property
    def multi_config_mode(self) -> Literal["chain", "override"]:
        # Default mode is "chain"; set to "override" if needed
        return "override"

    def get_transformed_fields(self) -> List[str]:
        return ["text"]  # Fields this processor modifies
    
    def validate_config(self) -> bool:
        # Validate self.config for required fields, correct types, etc.
        return True
```

## Example Recipes

### Abbreviation Expansion
Focus on expanding common screenplay abbreviations:
```yaml
processors:
  - name: text_substitution
    config:
      substitutions:
        - from: "CU"
          to: "close up"
          fields:
            - text
        - from: "ECU"
          to: "extreme close up"
          fields:
            - text
        - from: "POV"
          to: "point of view"
          fields:
            - text
        - from: "OTS"
          to: "over the shoulder"
          fields:
            - text
```

### Voice-Friendly Formatting
Optimize text for TTS reading:
```yaml
processors:
  - name: pattern_replace
    config:
      replacements:
        # Remove em dashes
        - match_field: text
          match_pattern: '.*'
          replace_field: text
          replace_pattern: '—'
          replace_string: ', '
        
        # Convert ellipses to comma
        - match_field: text
          match_pattern: '.*'
          replace_field: text
          replace_pattern: '\.\.\.'
          replace_string: ', '
  
  - name: capitalization_transform
    config:
      transformations:
        - chunk_type: speaker_attribution
          case: sentence_case
        - chunk_type: scene_heading
          case: sentence_case
```

## Troubleshooting

### Common Issues

1. **Processor Not Found**
   - Check file naming: `[name]_processor.py`
   - Verify class name matches pattern: `[Name]Processor`
   - Ensure file is in correct directory

2. **Config Validation Failed**
   - Check required fields in config
   - Verify data types (strings, lists, etc.)
   - Test regex patterns separately

3. **Unexpected Results**
   - Check processor order
   - Test with --dry-run first
   - Use `sts-apply-text-processors-json` to test specific configs. Compare [screenplay_name].json to [screenplay_name]-modified.json to see if the intended changes were applied