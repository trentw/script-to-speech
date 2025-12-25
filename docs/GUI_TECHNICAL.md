# Script to Speech GUI Technical Documentation

This document outlines the technical architecture and development workflows for the Script to Speech GUI.

## Architecture Overview

The application follows a "Sidecar" architecture, where a modern web frontend communicates with a Python backend that wraps the core CLI functionality.

### Frontend (GUI)
- **Framework**: [React](https://react.dev/) with [Vite](https://vitejs.dev/)
- **Language**: TypeScript
- **Styling**: [Tailwind CSS](https://tailwindcss.com/)
- **UI Components**: [shadcn/ui](https://ui.shadcn.com/) (based on Radix UI)
- **State Management**: [TanStack Query](https://tanstack.com/query/latest) (server state) & [Zustand](https://github.com/pmndrs/zustand) (client state)
- **Routing**: [TanStack Router](https://tanstack.com/router/latest)
- **Host**: [Tauri v2](https://tauri.app/) (provides the native window and system access)

### Backend (Sidecar)
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **Language**: Python
- **Role**: Exposes the `script-to-speech` core library functionality via a REST API.
- **Lifecycle**: Managed by Tauri. When the app starts, Tauri spawns the FastAPI server as a sidecar process.
- **Build**: The backend is frozen into a standalone executable using [PyInstaller](https://pyinstaller.org/). This allows the application to run without requiring the user to have Python installed.
    - **Build Script**: `build_backend.py` handles the PyInstaller build and renames the executable with the target triple (e.g., `sts-gui-backend-x86_64-apple-darwin`) required by Tauri.
    - **Spec File**: `sts-gui-backend.spec` defines the PyInstaller configuration, including hidden imports and data files.

### Communication
1. **Frontend -> Tauri**: Uses Tauri's IPC for system-level operations (file dialogs, window controls).
2. **Frontend -> Backend**: Uses standard HTTP requests (`fetch`) to `localhost` to trigger audio generation, parsing, etc.
    - The frontend `ApiService` manages these requests.
    - The backend runs on port 58735 in production, and port 8000 in development, and exposes endpoints for parsing, voice casting, and generation.

## Design Principles

1. **Thin Wrapper**: The GUI should contain minimal business logic. It should primarily serve as a visual interface for the underlying CLI Script to Speech library.
2. **Interoperability**: The GUI reads and writes the same file (JSON, YAML) as the CLI. A project created in the GUI can be manipulated via the CLI, and vice versa.
3. **Reactive UI**: The UI should reflect the current state of the file system and generation processes in real-time (or near real-time via polling/events).

## Development Setup

### Prerequisites
- **Node.js** (v18+)
- **Rust** (latest stable)
- **Python** (v3.10+)
- **uv** (Python package manager)

### Running Locally
The project includes a `Makefile` to simplify development tasks.

1.  **Start Backend Server**:
    ```bash
    make gui-server
    ```

2.  **Start Frontend (Web Mode)**:
    Recommended for rapid UI development.
    ```bash
    make gui-dev
    ```
    Open [http://localhost:5173](http://localhost:5173) in your browser.

3.  **Start Desktop App (Tauri)**:
    Run the full desktop application in development mode.
    ```bash
    make gui-desktop
    ```

### Building for Production

To build the desktop application:

```bash
# Build debug version (with console)
make gui-build-debug

# Build release version (optimized)
make gui-build-release
```

## Key Directories

- `gui/frontend/src`: React source code.
- `gui/frontend/src-tauri`: Rust Tauri configuration and code.
- `src/script_to_speech/gui_backend`: FastAPI backend application.
- `dist/`: Built backend executables (created by `make gui-build-backend`).
- `gui/frontend/src-tauri/target/`: Tauri build artifacts.

## Build Artifacts

After running `make gui-build-debug` or `make gui-build-release`, find the built applications at:

**macOS:**
- `gui/frontend/src-tauri/target/release/bundle/macos/Script to Speech.app` - Application bundle (includes bundled backend sidecar)
- `gui/frontend/src-tauri/target/release/bundle/dmg/Script to Speech_0.1.0_aarch64.dmg` - Installer

**Standalone Backend Executable:**
The backend can also be built independently:
```bash
make gui-build-backend
```

This creates platform-specific executables in the `dist/` directory (~34MB):
- macOS (Apple Silicon): `dist/sts-gui-backend-aarch64-apple-darwin`
- macOS (Intel): `dist/sts-gui-backend-x86_64-apple-darwin`
- Windows: `dist/sts-gui-backend-x86_64-pc-windows-msvc.exe`
- Linux: `dist/sts-gui-backend-x86_64-unknown-linux-gnu`

The backend sidecar is automatically bundled inside the Tauri application and managed by Tauri's sidecar API.

## Port Configuration

The backend runs on different ports depending on the environment:

- **Development**: Port `8000` (used by `make gui-server`)
- **Production**: Port `58735` (used by Tauri sidecar)

The frontend automatically detects which environment it's running in and connects to the appropriate port.

## Backend Lifecycle Management

The Tauri desktop app uses **stdin EOF monitoring** for robust backend process lifecycle management.

### Problem Solved
- PyInstaller's `--onefile` mode creates a bootloader parent + Python child process
- Tauri's `child.kill()` only kills the bootloader, leaving the Python process orphaned
- Orphaned processes block ports and accumulate on repeated app launches

### Solution Implemented
- Backend monitors stdin for EOF in an async executor thread
- When Tauri closes, stdin pipe closes → EOF detected → graceful shutdown triggered
- FastAPI lifespan cleanup hooks run before process termination
- Works cross-platform (Windows, macOS, Linux) with zero external dependencies

### Key Implementation Details
- **Python**: `monitor_parent_stdin()` in `src/script_to_speech/gui_backend/main.py` blocks on `sys.stdin.buffer.read()` until EOF
- **Rust**: `.stdin(Stdio::piped())` required in both dev and sidecar modes (`gui/frontend/src-tauri/src/lib.rs`)
- **Production**: Uses `uvicorn.Server()` instead of `uvicorn.run()` for shutdown control
- **Manual Testing**: Use `--ignore-stdin` flag to disable monitoring when testing the backend manually

**Important:** Never use `--ignore-stdin` when running as a Tauri sidecar - it disables the orphan prevention mechanism.

### Manual Backend Testing

For manual backend testing (outside of Tauri), use the `--ignore-stdin` flag:

```bash
# Run backend manually for testing
./dist/sts-gui-backend-aarch64-apple-darwin --production --port 58735 --ignore-stdin

# Without --ignore-stdin, the backend expects to be spawned by Tauri with a piped stdin
# and will immediately shut down when stdin closes (which happens in manual shell execution)
```

## Testing

The frontend uses [Playwright](https://playwright.dev/) for end-to-end testing.

**Run tests:**
```bash
cd gui/frontend
npm test
```

**Test utilities:**
- `src/test/router-helpers.ts` - Navigation and routing test helpers
- `src/hooks/__tests__/` - Hook testing examples

## Troubleshooting

### Orphaned Backend Processes

If the backend process doesn't shut down properly (rare with stdin monitoring):

```bash
# Find and kill processes on the production port
lsof -ti:58735 | xargs kill -9

# Or on the development port
lsof -ti:8000 | xargs kill -9
```

### Port Conflicts

If you see errors about port already in use:
1. Check for orphaned processes (see above)
2. Ensure you're not running multiple instances of the backend
3. Check if another application is using port 8000 or 58735

### API Key Configuration

The backend requires API keys for TTS providers. Configure them via:
- **Development**: `.env` file in project root
- **Production**: GUI Settings panel (keys stored securely on local machine)

### Backend Won't Start

If the Tauri app launches but the backend doesn't respond:
1. Check the console logs (in debug builds)
2. Ensure all Python dependencies are bundled correctly in `sts-gui-backend.spec`
3. Verify the backend executable has execute permissions
4. Test the backend manually with `--ignore-stdin` flag to see error messages

### Build Issues

**PyInstaller hidden imports:**
If the backend fails to start after building, you may need to add hidden imports to `sts-gui-backend.spec`.

**Tauri sidecar not found:**
Ensure the backend executable name matches the target triple expected by Tauri (e.g., `sts-gui-backend-aarch64-apple-darwin` for Apple Silicon Mac).
