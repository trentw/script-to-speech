"""FastAPI backend server for Script-to-Speech GUI."""

import asyncio
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from script_to_speech.gui_backend.config import settings
from script_to_speech.gui_backend.routers import (
    files,
    generation,
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

# Background task for session cleanup
async def cleanup_sessions_task():
    """Periodically clean up expired voice casting sessions."""
    while True:
        try:
            # Wait for 1 hour
            await asyncio.sleep(3600)
            
            # Clean up sessions older than 24 hours
            cleaned = await voice_casting_service.cleanup_expired_sessions(expiry_hours=24)
            if cleaned > 0:
                logger.info(f"Cleaned up {cleaned} expired voice casting sessions")
        except Exception as e:
            logger.error(f"Error during session cleanup: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
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
    allow_origins=["http://localhost:5173", "tauri://localhost"],  # Vite and Tauri
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(providers.router, prefix="/api", tags=["providers"])
app.include_router(voice_library.router, prefix="/api", tags=["voice-library"])
app.include_router(generation.router, prefix="/api", tags=["generation"])
app.include_router(files.router, prefix="/api", tags=["files"])
app.include_router(screenplay.router, prefix="/api/screenplay", tags=["screenplay"])
app.include_router(voice_casting.router, prefix="/api/voice-casting", tags=["voice-casting"])

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


def main() -> None:
    """Run the FastAPI server."""
    uvicorn.run(
        "script_to_speech.gui_backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    main()
