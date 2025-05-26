# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

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

