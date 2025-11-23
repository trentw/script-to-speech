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
