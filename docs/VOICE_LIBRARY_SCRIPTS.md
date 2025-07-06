# Voice Library Scripts Guide

Voice Library Scripts provide a powerful and extensible way to automate tasks and manage data related to your voice library. This system allows for custom Python scripts to be executed via the CLI, operating over voice configurations and data.

## Purpose

The voice library script system serves several key purposes:

- **Automation**: Automate repetitive tasks related to voice library management (e.g., fetching available voices, updating exclusions).
- **Custom Logic**: Implement custom logic for voice data processing that is specific to your project or workflow.
- **Extensibility**: Easily add new functionalities without modifying the core application code.
- **User Customization**: Override system-defined scripts with your own versions for tailored behavior.

## Running Scripts

Scripts are executed using the `sts-voice-library-run-script` CLI command:

```bash
uv run sts-voice-library-run-script [script_name] [script_parameters]
```

Each script is expected to define its own command-line arguments. The system dynamically loads the script's argument parser to handle parameters. To see the expected arguments for a specific script, use the `--help` flag:

```bash
uv run sts-voice-library-run-script [script_name] --help
```

### Script Interface Contract

For a script to be discoverable and executable by `sts-voice-library-run-script`, it must adhere to the following interface:

-   **`get_argument_parser() -> argparse.ArgumentParser`**: A function that returns a configured `ArgumentParser` instance for the script's specific arguments.
-   **`run(args: argparse.Namespace) -> None`**: The main entry point function that receives the parsed arguments as a `Namespace` object.

## Script Discovery and Structure

Voice library scripts are discovered from two primary locations, with user-defined scripts taking precedence:

1.  **System Directory**: `src/script_to_speech/voice_library/voice_library_scripts/` (part of the codebase)
2.  **User Directory**: `voice_library/voice_library_scripts/` (located in your project's root directory)

If a script with the same name exists in both directories, the version in the user directory will be used.

Scripts can be structured in two ways:

-   **Single File Script**: A `.py` file directly within the script directory (e.g., `my_script.py`). The script name is the filename (e.g., `my_script`).
-   **Directory Script**: A directory containing a `.py` file with the same name as the directory (e.g., `my_script/my_script.py`). This is useful for scripts that require supporting files (e.g., data, additional modules).

## Script Validation

To ensure scripts are correctly structured and adhere to the required interface, you can use the `sts-validate-voice-library-scripts` command:

```bash
uv run sts-validate-voice-library-scripts
```

This command checks for:
-   Duplicate script names (between single-file and directory scripts, or user/system conflicts).
-   Correct directory structure for directory-based scripts (e.g., `script_name/script_name.py`).
-   Adherence to the script interface contract (`get_argument_parser()` and `run()` functions).

To validate only the system-defined scripts (excluding user-defined ones), use the `--project-only` flag:

```bash
uv run sts-validate-voice-library-scripts --project-only
```

## Current Scripts

### `fetch_available_voices`

This script fetches a list of available voice IDs from a specified TTS provider and generates an `sts_included_ids.yaml` configuration file. This file can then be used to whitelist voices for voice casting prompts (see `docs/VOICE_LIBRARY_CONFIG.md`).

**Usage**:

```bash
uv run sts-voice-library-run-script fetch_available_voices [provider] [--file_name FILE_NAME]
```

-   **`provider` (required)**: The name of the TTS provider (e.g., `elevenlabs`, `openai`).
-   **`--file_name` (optional)**: The base name for the output YAML file. If not provided, the default is `[provider]_fetched_voices.yaml`.

**Example**:

```bash
uv run sts-voice-library-run-script fetch_available_voices elevenlabs --file_name elevenlabs_my_voices
```

This would create `voice_library/voice_library_config/elevenlabs_my_voices.yaml`.

**Output File Structure**:

The generated YAML file will have the following structure:

```yaml
included_sts_ids:
  [provider_name]:
    - voice_id_1
    - voice_id_2
    - ...
```

If the output file already exists, it will be overwritten.

**Provider-Specific Logic**: The `fetch_available_voices` script looks for provider-specific voice fetching logic in subdirectories named after the provider. For example, for the `elevenlabs` provider, it will look for `fetch_available_voices/elevenlabs/fetch_provider_voices.py`.

This provider-specific file is responsible for returning a list of `sts_id` strings. The main `fetch_available_voices` script then handles the creation and storage of the YAML configuration file.

Similar to overall script discovery, user-defined provider-specific files take precedence over system-defined ones.

## Best Practices

1.  **Descriptive Naming**: Use clear and descriptive names for your scripts and their arguments.
2.  **Modular Design**: For complex scripts, use the directory structure to organize supporting files and provider-specific logic.
3.  **Clear Arguments**: Define arguments clearly with helpful descriptions, leveraging `argparse`.
4.  **Error Handling**: Implement robust error handling within your scripts.
5.  **Validation**: Regularly run `sts-validate-voice-library-scripts` to ensure your scripts conform to the expected structure and interface.
