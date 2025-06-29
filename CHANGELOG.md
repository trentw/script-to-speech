# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Added user-configurable voice library directories, and merge logic, so that project-level voices can be modified / added to
- Added `voice_library_config` concept on both project and user level, and added first use case: filtering sts_ids that are included in the voice casting prompt
- Added new documentation for `sts-generate-standalone-speech` and `sts-batch-generate-standalone-speech`, including sample configuration for batch generation
- Expanded elevenlabs voice library with additional voices
- Added `sts-batch-generate-standalone-speech` script to generate standalone speech files in bulk (useful for generating sample audio for multiple voices that need to be added to voice library)
- Added additional reporting functionality to `validate` mode of `sts-tts-provider-yaml` to report provide stats provider usage + duplicate voice stats 
- Added `sts-generate-voice-library-casting-prompt` utility to aid in casting voice configs, utilizing the voice library
- Incorporating voice library "expansion" into tts provider manager and standalone speech utility
- Added validation for voice library, validation scripts, and pre-commit hook
- Added voice library schema an minimal library files
- Added more extensive privacy notices and data usage suggestions, including [PRIVACY.md](PRIVACY.md)
- Added clearer in-line privacy notices when a 3rd party service is being used
- Added `validate` mode to `sts-tts-provider-yaml` script to identify missing / additional / duplicate speakers in .yaml voice configuration, as well as validate fields with `--strict` flag
- Added `sts-copy-to-clipboard` utility to copy file contents to clipboard
- Added `sts-generate-character-notes-prompt` utility to aid in casting voice configs by generating character notes

### Changed
- Changed `--tts_config` to be a required parameter for `sts-generate-audio`, and updated variable naming to `tts_provider_config` to be more consistent with rest of code

### Fixed
- Added duplicate checking across voice library .yaml files for a given provider to ensure uniqueness
- Fixed a couple parser issues where multi-line dialogue_modifiers were being terminated early, and where they were incorrectly being attributed as dialogues
- Fixed parser issue where dialogue_modifiers weren't properly being terminated in some cases by adding tracking of last non-blank line, and checking for closed parenthesis
- Fixed issue with `sts-parse-regression-check-json` where it could get "out of sync" in some cases and incorrectly show chunks as added / removed

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

