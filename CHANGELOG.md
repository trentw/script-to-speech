# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- [Desktop] Feature: click voice name on voice assignemnt page to replace — shows current voice and "Replace Voice" header on voice assignment page
- [Desktop] Feature: clickable character names in "other assignments" tooltip — click to scroll to that character

### Fixed
- [Desktop] Fixed scroll voice casting scroll position issues with voice assignment page / "back" button flow
- [Desktop] Stop voice preview playback when unassigning a voice from a character 
- [Desktop] Added onBlur for ID3 tag edit boxes so that they auto-save when clicked outside of edit box
- [Desktop] Fixed issue where character names with special characters (like "/") would break voice assignment
- [Desktop] Fixed ffmpeg "Bad CPU type" error on Apple Silicon by upgrading `static-ffmpeg` to v3.0 (arm64 support)
- [Docs] Updated development setup instructions with correct `uv sync --all-extras` command, pnpm install step, and pre-commit hook setup

## [2.0.0] - 2026-02-07

Starting with 2.0.0, this changelog covers all components (CLI, backend, frontend, desktop app).

### Added
- [Desktop] First unified release of the Script to Speech desktop application
- [Desktop] Voice casting workflow with LLM-assisted casting, voice preview, and assignment UI
- [Desktop] Audiobook generation pipeline with progress tracking and ID3 tag editing
- [Desktop] Project management with screenplay import, parsing, and review
- [Desktop] Provider API key configuration and management
- [Desktop] macOS code signing and notarization for trusted distribution
- [Desktop] Cross-platform builds (macOS ARM64/Intel, Windows, Linux)
- [CLI] Adding `sts-voice-library-run-script` and corresponding `sts-validate-voice-library-scripts` scripts to load system / user defined voice library scripts + tests and documentation, as well initial `fetch_provider_voices` script
- [CLI] Added `overall_voice_casting_prompt` case to `additional_voice_casting_instructions` to add to overall casting prompt
- [CLI] Added `additional_voice_casting_instructions` field to voice_library_config to specific additional casting instructions for each provider
- [CLI] Added user-configurable voice library directories, and merge logic, so that project-level voices can be modified / added to
- [CLI] Added `voice_library_config` concept on both project and user level, and added first use case: filtering sts_ids that are included in the voice casting prompt
- [CLI] Added new documentation for `sts-generate-standalone-speech` and `sts-batch-generate-standalone-speech`, including sample configuration for batch generation
- [CLI] Expanded elevenlabs voice library with additional voices
- [CLI] Added `sts-batch-generate-standalone-speech` script to generate standalone speech files in bulk (useful for generating sample audio for multiple voices that need to be added to voice library)
- [CLI] Added additional reporting functionality to `validate` mode of `sts-tts-provider-yaml` to report provide stats provider usage + duplicate voice stats 
- [CLI] Added `sts-generate-voice-library-casting-prompt` utility to aid in casting voice configs, utilizing the voice library
- [CLI] Incorporating voice library "expansion" into tts provider manager and standalone speech utility
- [CLI] Added validation for voice library, validation scripts, and pre-commit hook
- [CLI] Added voice library schema an minimal library files
- [CLI] Added more extensive privacy notices and data usage suggestions, including [PRIVACY.md](PRIVACY.md)
- [CLI] Added clearer in-line privacy notices when a 3rd party service is being used
- [CLI] Added `validate` mode to `sts-tts-provider-yaml` script to identify missing / additional / duplicate speakers in .yaml voice configuration, as well as validate fields with `--strict` flag
- [CLI] Added `sts-copy-to-clipboard` utility to copy file contents to clipboard
- [CLI] Added `sts-generate-character-notes-prompt` utility to aid in casting voice configs by generating character notes

### Changed
- [CLI] Changed `--tts_config` to be a required parameter for `sts-generate-audio`, and updated variable naming to `tts_provider_config` to be more consistent with rest of code

### Fixed
- [CLI] Fixing some dict merging edge cases with nested lists, and consolidating dict merging functionality in a `dict_utils.py` file
- [CLI] Added duplicate checking across voice library .yaml files for a given provider to ensure uniqueness
- [CLI] Fixed a couple parser issues where multi-line dialogue_modifiers were being terminated early, and where they were incorrectly being attributed as dialogues
- [CLI] Fixed parser issue where dialogue_modifiers weren't properly being terminated in some cases by adding tracking of last non-blank line, and checking for closed parenthesis
- [CLI] Fixed issue with `sts-parse-regression-check-json` where it could get "out of sync" in some cases and incorrectly show chunks as added / removed

## [1.1.0] - 2025-05-26

### Added
- Added .env file support for TTS Provider API key storage
- Support for [Cartesia](https://play.cartesia.ai/text-to-speech) TTS provider
- Support for [Minimax](https://www.minimax.io/audio/text-to-speech) TTS provider with voice mixing capability

### Changed
- Reduced Minimax concurrent thread count from 5 to 1 thread as rate limit was being constantly hit with even 2 threads
- `generate_standalone_speech` now uses `tts_provider_manger` to generate audio instead of custom provider creation. This aligns the code / behavior with the core audio generation behavior in `script_to_speech.py`
- Pulling `tts_provider_config` parsing out of `tts_provider_manager` so that the manager is instantiated with a configuration dict
- Updating generate_standalone_speech to support outputting and parsing command strings corresponding to complex configs (like the dict-based config for Minimax's `voice_mix`)
- Changed zonos tts-provider to base behavior on `default_voice_name` instead of `voice_seed`, since `voice_seed` is no longer part of the zonos API

### Fixed
- Better handling of rate-limiting / backoff handling for providers with rolling maximum request windows
- `standalone_speech` and `source_screenplay` folders now correctly created on first checkout
- Adding py.typed to src root and updating pyproject.toml to have mypy path = src
- For `--dummy-tts-provider-override` run mode, fall back to speaker name for `dummy_id` in cases where required fields are blank / not present 

## [1.0.1] - 2025-05-14

### Added
- `--max-workers` run mode flag to control global maximum of concurrent downloads (was previously set by `GLOBAL_MAX_WORKERS = 12`). Updated documentation and tests accordingly

### Changed
- Finally switching repository to PUBLIC!
- Consolidated output folder creation utilities between parsing and generating, and moved parser logs to standard output/[screenplay]/logs location
- Changing behavior of `--tts-provider` for `sts-tts-provider-yaml` flag to explicitly populate TTS provider fields to remove the necessity of `--tts-provider` flag for `sts-generate-audio` 
- Naming more consistent and descriptive in commands, code, and documentation
  - "provider" -> "TTS provider"
  - "dialog" -> "dialogue"
  - "processor" -> "text processor"

## [1.0.0] - 2025-05-11

### Added
- All initial files for Script to Speech!
- CHANGELOG.md in preparation of initial release -- for previous changes, see git history
- Documentation: README.md, PROCESSORS.md, PROVIDERS.md, RUN_MODES.md, TROUBLESHOOTING.md

### Changed
- Moved to proper `src`-based directory structure for proper packaging

