# Package Restructure Plan: Single Pythonic Package

*Created: July 8, 2025*

## Motivation

### Current Issues
1. **Two separate Python packages** (`src/script_to_speech` + `gui/backend`) 
2. **Complex dependency management** between packages
3. **Non-standard structure** for Python projects with optional GUI
4. **Difficult executable creation** due to cross-package dependencies
5. **Tauri bundling challenges** with external path resolution

### Goals
1. **Standard Python packaging** following PEP 621 and modern best practices
2. **Optional dependencies** using `[gui]` extras (like FastAPI, Django, etc.)
3. **Single source of truth** for configuration and versioning
4. **Simplified build process** for self-contained executables
5. **Clean imports** under unified `script_to_speech.*` namespace

## Solution: Single Package with Optional Dependencies

Following the pattern used by major Python projects (FastAPI, Django, SQLAlchemy), we'll merge into a single package with optional GUI capabilities.

### Before (Current Structure)
```
script-to-speech/
├── src/script_to_speech/          # Main package
│   ├── tts_providers/
│   ├── voice_library/
│   ├── parser/
│   ├── audio_generation/
│   └── ... (other modules)
├── gui/
│   ├── backend/                   # Separate Python package
│   │   ├── sts_gui_backend/
│   │   ├── pyproject.toml         # Separate config
│   │   └── README.md
│   └── frontend/                  # React + Tauri
└── pyproject.toml                 # Main package config
```

### After (Pythonic Structure)
```
script-to-speech/
├── src/script_to_speech/          # Unified package
│   ├── tts_providers/             # Existing (no move)
│   ├── voice_library/             # Existing (no move)
│   ├── parser/                    # Existing (no move)
│   ├── audio_generation/          # Existing (no move)
│   ├── gui_backend/              # MOVED from gui/backend/sts_gui_backend/
│   │   ├── main.py
│   │   ├── services/
│   │   ├── routers/
│   │   └── ... (GUI backend code)
│   └── ... (other existing modules)
├── gui/
│   └── frontend/                  # Unchanged (React + Tauri)
└── pyproject.toml                 # Merged configuration
```

## Implementation Steps

### Phase 1: Git-Safe File Movement

**⚠️ CRITICAL: Use `git mv` to preserve file history**

```bash
# 1. Move GUI backend with history preservation
git mv gui/backend/sts_gui_backend src/script_to_speech/gui_backend

# 2. Backup GUI config files for manual merging
git mv gui/backend/pyproject.toml temp_gui_pyproject.toml
git mv gui/backend/README.md temp_gui_readme.md

# 3. Note: DO NOT commit yet - user will handle commits
```

### Phase 2: Configuration Merge

**Merge pyproject.toml files:**
- Use main `pyproject.toml` as base
- Add GUI dependencies as optional `[gui]` extras
- Add build tools as optional `[build]` extras
- Merge script entry points
- Merge development dependencies

**New pyproject.toml structure:**
```toml
[project]
name = "script_to_speech"
dependencies = [
    # All existing core dependencies
    "elevenlabs>=1.57.0",
    "openai>=1.76.0",
    # ... (existing deps unchanged)
]

[project.optional-dependencies]
gui = [
    # From gui/backend/pyproject.toml
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.0.0",
    "python-multipart>=0.0.6",
    "aiofiles>=23.2.1",
]
build = [
    # For creating executables
    "pyinstaller>=6.0.0",
]
dev = [
    # Merged dev dependencies from both packages
    "black>=25.1.0",
    "pytest>=8.3.5",
    # ... (combine all dev deps)
]

[project.scripts]
# Keep all existing CLI scripts
sts-generate-audio = "script_to_speech.script_to_speech:main"
# ... (all existing scripts)

# Add GUI server script
sts-gui-server = "script_to_speech.gui_backend.main:main"
```

### Phase 3: Import Statement Updates

**Files to update in moved GUI backend:**

1. **`src/script_to_speech/gui_backend/main.py`**
   ```python
   # Old imports (when separate package)
   from sts_gui_backend.services import tts_service
   
   # New imports (unified package)
   from script_to_speech.gui_backend.services import tts_service
   ```

2. **All files in `gui_backend/` directory**
   - Update relative imports within GUI backend
   - Update imports to main package functionality
   - Change from cross-package imports to same-package imports

3. **Key import changes:**
   ```python
   # OLD (cross-package dependency)
   from script_to_speech.tts_providers import openai_provider
   
   # NEW (same package)
   from script_to_speech.tts_providers import openai_provider
   ```

### Phase 4: Cleanup

```bash
# Remove temporary files after merging
git rm temp_gui_pyproject.toml temp_gui_readme.md

# Remove empty gui/backend directory
git rm -r gui/backend
```

## New Installation Patterns

### For End Users
```bash
# Core library only (CLI tools)
uv add script-to-speech

# With GUI capabilities
uv add "script-to-speech[gui]"
```

### For Developers
```bash
# Full development setup
uv add "script-to-speech[gui,dev,build]"
```

### For Building Executables
```bash
# Install with build tools
uv add "script-to-speech[build]"

# Create executable
uv run pyinstaller --onefile src/script_to_speech/gui_backend/main.py
```

## Benefits of This Approach

### ✅ Standard Python Packaging
- Follows PEP 621 modern packaging standards
- Same pattern as FastAPI (`fastapi[all]`), Django (`django[postgres]`)
- Single source of truth for version, metadata, dependencies

### ✅ Simplified Development
- One `pyproject.toml` to maintain
- Clean import structure: `from script_to_speech.gui_backend import ...`
- Unified development environment

### ✅ Better Executable Creation
- Single package means PyInstaller can bundle everything cleanly
- No cross-package dependency resolution issues
- Easier to create truly self-contained executables

### ✅ Git History Preservation
- Using `git mv` maintains complete file history
- No loss of development history or blame information

### ✅ Future-Proof
- Ready for PyPI publication with optional GUI
- Standard structure that Python developers expect
- Easy to add more optional features (`[web]`, `[enterprise]`, etc.)

## Validation Steps

After restructuring:

1. **Test CLI functionality** - Ensure existing scripts work
2. **Test GUI backend** - Verify FastAPI server starts correctly
3. **Test imports** - All import statements resolve properly
4. **Test uv installation** - `uv add "script-to-speech[gui]"` works
5. **Test executable creation** - PyInstaller can bundle cleanly
6. **Test Tauri integration** - Desktop app can use bundled executable

## Risk Mitigation

- **Git history preserved** through `git mv` operations
- **Incremental changes** - test each phase before proceeding
- **Rollback possible** - git can revert if issues arise
- **No loss of functionality** - all existing features maintained

This restructure positions the project as a standard, professional Python package while enabling self-contained desktop app creation.