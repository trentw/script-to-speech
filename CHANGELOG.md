# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed
- Changed zonos tts-provider to base behavior on `default_voice_name` instead of `voice_seed`, since `voice_seed` is no longer part of the zonos API

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

