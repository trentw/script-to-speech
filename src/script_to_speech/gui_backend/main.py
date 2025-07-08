"""FastAPI backend server for Script-to-Speech GUI."""

import os
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from script_to_speech.gui_backend.routers import providers, voice_library, generation, files
from script_to_speech.gui_backend.config import settings

# Create FastAPI app
app = FastAPI(
    title="Script-to-Speech GUI Backend",
    description="REST API for TTS Playground functionality",
    version="0.1.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
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

# Mount static files directory for generated audio
if settings.AUDIO_OUTPUT_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(settings.AUDIO_OUTPUT_DIR)), name="static")


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