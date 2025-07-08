"""File serving API routes."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

from ..config import settings

router = APIRouter()


@router.get("/files/{filename}")
async def get_audio_file(filename: str) -> FileResponse:
    """Serve generated audio files."""
    try:
        file_path = settings.AUDIO_OUTPUT_DIR / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File {filename} not found")
        
        if not file_path.is_file():
            raise HTTPException(status_code=404, detail=f"{filename} is not a file")
        
        # Security check: ensure file is within the audio output directory
        try:
            file_path.resolve().relative_to(settings.AUDIO_OUTPUT_DIR.resolve())
        except ValueError:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return FileResponse(
            path=str(file_path),
            media_type="audio/mpeg",
            filename=filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to serve file: {str(e)}")


@router.get("/files")
async def list_audio_files() -> dict:
    """List available audio files."""
    try:
        files = []
        for file_path in settings.AUDIO_OUTPUT_DIR.glob("*.mp3"):
            if file_path.is_file():
                files.append({
                    "filename": file_path.name,
                    "size": file_path.stat().st_size,
                    "modified": file_path.stat().st_mtime
                })
        
        return {"files": files}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")