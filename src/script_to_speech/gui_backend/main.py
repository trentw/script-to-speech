"""FastAPI backend server for Script-to-Speech GUI."""

import argparse
import asyncio
import multiprocessing
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator, Callable

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from uvicorn import Config, Server

from script_to_speech.gui_backend.config import settings
from script_to_speech.gui_backend.routers import (
    files,
    generation,
    projects,
    providers,
    screenplay,
    voice_casting,
    voice_library,
)
from script_to_speech.gui_backend.services.voice_casting_service import (
    voice_casting_service,
)
from script_to_speech.utils.logging import get_screenplay_logger

logger = get_screenplay_logger("gui_backend")

# Required for PyInstaller multiprocessing support on macOS/Windows
if getattr(sys, "frozen", False):
    multiprocessing.freeze_support()


# Background task for session cleanup
async def cleanup_sessions_task() -> None:
    """Periodically clean up expired voice casting sessions."""
    while True:
        try:
            # Wait for 1 hour
            await asyncio.sleep(3600)

            # Clean up sessions older than 24 hours
            cleaned = await voice_casting_service.cleanup_expired_sessions(
                expiry_hours=24
            )
            if cleaned > 0:
                logger.info(f"Cleaned up {cleaned} expired voice casting sessions")
        except Exception as e:
            logger.error(f"Error during session cleanup: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifecycle."""
    # Startup
    logger.info("Starting Script-to-Speech GUI Backend")

    # Start background tasks
    cleanup_task = asyncio.create_task(cleanup_sessions_task())

    yield

    # Shutdown
    logger.info("Shutting down Script-to-Speech GUI Backend")

    # Cancel background tasks
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass


# Create FastAPI app
app = FastAPI(
    title="Script-to-Speech GUI Backend",
    description="REST API for TTS Playground functionality",
    version="0.1.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "tauri://localhost",
    ],  # Vite and Tauri
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(providers.router, prefix="/api", tags=["providers"])
app.include_router(voice_library.router, prefix="/api", tags=["voice-library"])
app.include_router(generation.router, prefix="/api", tags=["generation"])
app.include_router(files.router, prefix="/api", tags=["files"])
app.include_router(projects.router, prefix="/api", tags=["projects"])
app.include_router(screenplay.router, prefix="/api/screenplay", tags=["screenplay"])
app.include_router(
    voice_casting.router, prefix="/api/voice-casting", tags=["voice-casting"]
)

# Mount static files directory for generated audio
if settings.AUDIO_OUTPUT_DIR.exists():
    app.mount(
        "/static", StaticFiles(directory=str(settings.AUDIO_OUTPUT_DIR)), name="static"
    )


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "Script-to-Speech GUI Backend", "version": "0.1.0"}


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/api/workspace")
async def get_workspace_info() -> dict[str, str | bool | list[str] | None]:
    """Get workspace directory information."""
    workspace_dir = settings.WORKSPACE_DIR
    if workspace_dir is None:
        return {
            "workspace_dir": "Not configured",
            "exists": False,
            "error": "Workspace directory is not set",
        }

    # Comprehensive debug information for troubleshooting
    is_production = "--production" in sys.argv

    return {
        "workspace_dir": str(workspace_dir),
        "exists": workspace_dir.exists(),
        "input_dir": str(workspace_dir / "input"),
        "output_dir": str(workspace_dir / "output"),
        "source_screenplays_dir": str(workspace_dir / "source_screenplays"),
        # Production detection
        "is_production": is_production,
        "detection_method": "tauri_flag",
        # Debug: All arguments received by Python
        "sys_argv": sys.argv,
        "production_flag_present": "--production" in sys.argv,
        # Debug: PyInstaller state (for comparison)
        "sys_frozen": getattr(sys, "frozen", None),
        "sys_meipass": getattr(sys, "_MEIPASS", None),
        # Platform info
        "sys_platform": sys.platform,
    }


async def monitor_parent_stdin(shutdown_callback: Callable[[], Any]) -> None:
    """
    Monitor stdin for parent process death (pipe closure).

    When Tauri spawns the backend as a sidecar with piped stdin,
    this function blocks until Tauri crashes/exits and the pipe closes.
    Upon EOF, triggers graceful shutdown via the callback.

    Works on Windows, macOS, and Linux with zero dependencies.
    """

    def watch_stdin() -> None:
        try:
            # CRITICAL: No size argument - blocks until EOF
            # Binary mode avoids Unicode errors on Windows
            sys.stdin.buffer.read()
            logger.warning("stdin pipe closed - parent died, triggering shutdown")
        except Exception as e:
            logger.error(f"stdin monitor error: {e}")

    loop = asyncio.get_running_loop()  # Not deprecated get_event_loop()
    await loop.run_in_executor(None, watch_stdin)
    await shutdown_callback()


async def run_server_with_monitoring(
    host: str, port: int, ignore_stdin: bool = False
) -> None:
    """Run uvicorn server with graceful shutdown on parent death.

    Args:
        host: Host address to bind to
        port: Port number to listen on
        ignore_stdin: If True, disable stdin monitoring (for manual testing only)
    """
    config = Config(
        app,
        host=host,
        port=port,
        log_level=settings.LOG_LEVEL.lower(),
        lifespan="on",  # Ensure cleanup runs
    )
    server = Server(config)

    async def shutdown_gracefully() -> None:
        logger.info("Initiating graceful server shutdown...")
        server.should_exit = True

    # Start stdin monitor (unless disabled for manual testing)
    monitor_task = None
    if not ignore_stdin:
        monitor_task = asyncio.create_task(monitor_parent_stdin(shutdown_gracefully))
        logger.info("stdin monitoring enabled (parent death detection active)")
    else:
        logger.warning(
            "stdin monitoring DISABLED - backend will not auto-terminate on parent death"
        )

    # Run server (blocks until shutdown)
    try:
        await server.serve()
    finally:
        # Cancel monitor task to prevent resource leak
        if monitor_task:
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Server shutdown complete")


def main() -> None:
    """Run the FastAPI server."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Script-to-Speech GUI Backend")
    parser.add_argument(
        "--production",
        action="store_true",
        help="Run in production mode (disables reload)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port to listen on (default: auto-detect based on mode)",
    )
    parser.add_argument(
        "--ignore-stdin",
        action="store_true",
        help="Disable stdin monitoring (for manual backend testing only - not for Tauri sidecar use)",
    )
    # Use parse_known_args() to ignore unknown arguments from Python multiprocessing
    # (e.g., when uvicorn spawns workers with -B -S -I -c ... args)
    args, unknown = parser.parse_known_args()

    # Determine the port: use explicit --port if provided, otherwise use settings default
    port = args.port if args.port else settings.PORT

    print(f"Backend starting with workspace: {settings.WORKSPACE_DIR}")
    mode = "production" if args.production else "development"
    logger.info(f"Starting backend on port {port} in {mode} mode")

    if args.production:
        # Production: async server with stdin monitoring for graceful shutdown
        # Detects parent process death and triggers cleanup before exiting
        # Use --ignore-stdin flag to disable monitoring for manual testing
        asyncio.run(run_server_with_monitoring(settings.HOST, port, args.ignore_stdin))
    else:
        # Development: use string import (enables reload/workers)
        uvicorn.run(
            "script_to_speech.gui_backend.main:app",
            host=settings.HOST,
            port=port,
            reload=settings.DEBUG,
            log_level=settings.LOG_LEVEL.lower(),
        )


if __name__ == "__main__":
    # MUST be first call for frozen executables (PyInstaller)
    multiprocessing.freeze_support()
    main()
