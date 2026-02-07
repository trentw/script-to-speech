# Versioning & Releases

This project uses a **single unified version** across all components: the Python CLI, the desktop app (Tauri), the React frontend, and the FastAPI backend. The version follows [Semantic Versioning](https://semver.org/) (`MAJOR.MINOR.PATCH`).

## Quick Reference

### Creating a Release

```bash
# 1. Update CHANGELOG.md
#    Move items from [Unreleased] to a new [X.Y.Z] section with today's date.
#    Use component labels where helpful: [CLI], [Desktop], [Frontend], [Backend]

# 2. Bump the version (pick one)
make bump-patch    # Bug fixes:        2.0.0 -> 2.0.1
make bump-minor    # New features:     2.0.0 -> 2.1.0
make bump-major    # Breaking changes: 2.0.0 -> 3.0.0

# 3. Push to trigger the release build
git push origin master --tags
```

That's it. Step 2 automatically updates all version files, commits, and creates a git tag. Step 3 triggers the GitHub Actions workflow that builds the desktop app for all platforms and creates a draft GitHub Release.

### Preview Before Bumping

```bash
make bump-dry-run        # Shows exactly what would change (no modifications)
make check-version       # Verifies all version files are in sync
```

### Using bump-my-version Directly

The Makefile targets are thin wrappers. You can also run the tool directly for more control:

```bash
uv run bump-my-version bump patch                  # Same as make bump-patch
uv run bump-my-version bump minor                  # Same as make bump-minor
uv run bump-my-version bump --dry-run -vv patch    # Verbose dry-run
uv run bump-my-version show-bump                   # Show available bumps
uv run bump-my-version show current_version        # Show current version
```

---

## How It Works

### Source of Truth

The version is defined in **`pyproject.toml`** under `[project] version`. This is the canonical version for the entire project. All other version files are kept in sync by [bump-my-version](https://github.com/callowayproject/bump-my-version).

### Files Updated on Each Bump

When you run a version bump, these 5 files are updated simultaneously:

| File | Field | Used By |
|------|-------|---------|
| `pyproject.toml` | `version = "X.Y.Z"` | Python package (pip/uv install), CLI tools |
| `src/script_to_speech/_version.py` | `__version__ = "X.Y.Z"` | FastAPI backend at runtime, PyInstaller builds |
| `gui/frontend/src-tauri/tauri.conf.json` | `"version": "X.Y.Z"` | Tauri desktop app, GitHub Release tag (`v__VERSION__`) |
| `gui/frontend/src-tauri/Cargo.toml` | `version = "X.Y.Z"` | Rust crate metadata |
| `gui/frontend/package.json` | `"version": "X.Y.Z"` | Frontend build (injected via Vite `define`) |

Additionally, bump-my-version automatically updates its own `current_version` in the `[tool.bumpversion]` section of `pyproject.toml`.

### What Happens During a Bump

When you run `make bump-patch` (for example), this is the full sequence:

1. **Version calculation** — bump-my-version reads the current version and calculates the new one (e.g., `2.0.0` -> `2.0.1`)
2. **File updates** — All 5 files listed above are updated with the new version string via search/replace
3. **Pre-commit hooks** — `cargo generate-lockfile` runs in `gui/frontend/src-tauri/` to regenerate `Cargo.lock`, which is then staged
4. **Git commit** — All changed files are staged and committed with message `release: vX.Y.Z`
5. **Git tag** — An annotated tag `vX.Y.Z` is created

### How the Version Reaches Each Component

```
pyproject.toml (source of truth)
  |
  ├── Python CLI tools
  |     Read by pip/uv at install time
  |
  ├── _version.py
  |     ├── FastAPI backend: imported as _APP_VERSION
  |     |     Used in FastAPI(version=...) and GET / endpoint
  |     └── PyInstaller: bundled into frozen executable
  |
  ├── tauri.conf.json
  |     ├── Desktop app window title and metadata
  |     └── GitHub Actions: tagName = "v__VERSION__"
  |           Creates GitHub Release as "Script to Speech vX.Y.Z"
  |
  ├── Cargo.toml
  |     Rust crate metadata (must stay in sync with tauri.conf.json)
  |
  └── package.json
        └── vite.config.ts: define { __APP_VERSION__ }
              └── React frontend: displayed in sidebar navigation
```

### Version Not Managed Here

**`website/package.json`** — The marketing website is deployed independently to GitHub Pages and has its own version that is not tied to product releases.

---

## Configuration Details

### bump-my-version Config

The full configuration lives in `pyproject.toml` under `[tool.bumpversion]`. Key settings:

```toml
[tool.bumpversion]
current_version = "2.0.0"      # Tracks the current version
commit = true                   # Auto-commit after bumping
tag = true                      # Auto-create git tag
tag_name = "v{new_version}"     # Tag format: v2.0.1
message = "release: v{new_version}"  # Commit message format
```

Each `[[tool.bumpversion.files]]` entry defines a file to update, with `search` and `replace` patterns using `{current_version}` and `{new_version}` placeholders.

### Pre-commit Hook

A `check-version-sync` hook in `.pre-commit-config.yaml` runs `scripts/check_version_sync.py` when version-related files change. This catches accidental version drift (e.g., manually editing one file but not the others).

### Frontend Version Injection

The frontend gets its version at **build time**, not runtime:

1. `vite.config.ts` reads `version` from `package.json` and defines `__APP_VERSION__` as a global constant
2. TypeScript type is declared in `src/vite-env.d.ts`
3. Components reference `__APP_VERSION__` directly (e.g., `AdaptiveNavigation.tsx`)

This works in both web dev mode (`make gui-dev`) and the Tauri desktop build.

### Backend Version Access

The FastAPI backend imports the version from `_version.py`:

```python
from script_to_speech._version import __version__ as _APP_VERSION
```

This file is used instead of `importlib.metadata` because it works reliably in PyInstaller-frozen executables, where package metadata may not be available.

---

## GitHub Release Pipeline

### Trigger

Pushing a tag matching `v*` (e.g., `v2.0.1`) triggers `.github/workflows/build-desktop.yml`.

### What It Does

1. Builds the Python backend sidecar via PyInstaller (`build_backend.py`)
2. Builds the Tauri desktop app for 4 platforms in parallel:
   - macOS ARM64 (Apple Silicon)
   - macOS x86_64 (Intel)
   - Linux x86_64
   - Windows x86_64
3. Signs and notarizes the macOS builds
4. Extracts the matching section from `CHANGELOG.md` for the release body
5. Creates a **draft** GitHub Release with all platform binaries attached

### After the Build

The release is created in **draft** mode. Review it on GitHub, then publish when ready. The release body includes the changelog content followed by a download table.

---

## CHANGELOG Convention

The changelog follows [Keep a Changelog](https://keepachangelog.com/) format. Starting with 2.0.0, it covers all components. Use optional labels to clarify which part of the project a change affects:

```markdown
## [Unreleased]

### Added
- [Desktop] New feature in the desktop app
- [CLI] New command-line tool
- [Frontend] New UI component
- [Backend] New API endpoint
- Feature that spans multiple components (no label needed)

### Changed
- ...

### Fixed
- ...
```

When preparing a release, move items from `[Unreleased]` to a new version section with today's date:

```markdown
## [2.1.0] - 2026-03-15
```
