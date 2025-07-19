#!/usr/bin/env python3
"""Simple test server with mock data for frontend development."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Create FastAPI app
app = FastAPI(
    title="Script-to-Speech GUI Backend (Test)",
    description="Mock API for frontend development",
    version="0.1.0-test",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "tauri://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock data
mock_providers = [
    {
        "identifier": "openai",
        "name": "OpenAI",
        "description": "OpenAI TTS Provider",
        "required_fields": [
            {
                "name": "voice",
                "type": "string",
                "required": True,
                "description": "OpenAI voice identifier",
                "options": ["alloy", "echo", "fable", "onyx", "nova", "shimmer"],
            }
        ],
        "optional_fields": [],
        "max_threads": 1,
    },
    {
        "identifier": "elevenlabs",
        "name": "ElevenLabs",
        "description": "ElevenLabs TTS Provider",
        "required_fields": [
            {
                "name": "voice_id",
                "type": "string",
                "required": True,
                "description": "ElevenLabs voice ID",
            }
        ],
        "optional_fields": [
            {
                "name": "stability",
                "type": "float",
                "required": False,
                "description": "Voice stability",
                "min_value": 0.0,
                "max_value": 1.0,
            },
            {
                "name": "similarity_boost",
                "type": "float",
                "required": False,
                "description": "Similarity boost",
                "min_value": 0.0,
                "max_value": 1.0,
            },
        ],
        "max_threads": 2,
    },
]

mock_voices = {
    "openai": [
        {
            "sts_id": "nova",
            "provider": "openai",
            "config": {"voice": "nova"},
            "voice_properties": {"gender": "feminine", "age": 0.3},
            "description": {
                "provider_name": "Nova",
                "custom_description": "A warm, friendly voice perfect for conversational content",
            },
            "tags": {"custom_tags": ["friendly", "warm", "conversational"]},
            "preview_url": "https://cdn.openai.com/API/docs/audio/nova.wav",
        }
    ],
    "elevenlabs": [
        {
            "sts_id": "antonio",
            "provider": "elevenlabs",
            "config": {"voice_id": "ErXwobaYiN019PkySvjV"},
            "voice_properties": {"gender": "masculine", "age": 0.5, "authority": 0.8},
            "description": {
                "provider_name": "Antonio",
                "custom_description": "A deep, authoritative voice ideal for narration",
            },
            "tags": {"custom_tags": ["authoritative", "deep", "narrator"]},
            "preview_url": "https://storage.googleapis.com/elevenlabs-public/antonio.mp3",
        }
    ],
}


@app.get("/")
async def root():
    return {
        "message": "Script-to-Speech GUI Backend (Test Mode)",
        "version": "0.1.0-test",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/api/providers")
async def get_providers():
    return [p["identifier"] for p in mock_providers]


@app.get("/api/providers/info")
async def get_providers_info():
    return mock_providers


@app.get("/api/providers/{provider}")
async def get_provider_info(provider: str):
    for p in mock_providers:
        if p["identifier"] == provider:
            return p
    return {"error": "Provider not found"}


@app.post("/api/providers/{provider}/validate")
async def validate_config(provider: str, config: dict):
    # Simple mock validation
    if provider == "openai":
        if "voice" not in config:
            return {
                "valid": False,
                "errors": ["Required field 'voice' is missing"],
                "warnings": [],
            }
        if config["voice"] not in ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]:
            return {"valid": False, "errors": ["Invalid voice option"], "warnings": []}
    elif provider == "elevenlabs":
        if "voice_id" not in config:
            return {
                "valid": False,
                "errors": ["Required field 'voice_id' is missing"],
                "warnings": [],
            }

    return {"valid": True, "errors": [], "warnings": []}


@app.get("/api/voice-library/providers")
async def get_voice_library_providers():
    return list(mock_voices.keys())


@app.get("/api/voice-library/{provider}")
async def get_provider_voices(provider: str):
    return mock_voices.get(provider, [])


@app.get("/api/voice-library/{provider}/{sts_id}")
async def get_voice_details(provider: str, sts_id: str):
    voices = mock_voices.get(provider, [])
    for voice in voices:
        if voice["sts_id"] == sts_id:
            voice["expanded_config"] = voice["config"]
            return voice
    return {"error": "Voice not found"}


@app.post("/api/generate")
async def create_generation_task(request: dict):
    import uuid

    task_id = str(uuid.uuid4())
    return {
        "task_id": task_id,
        "status": "pending",
        "message": "Generation task created (mock)",
    }


@app.get("/api/generate/status/{task_id}")
async def get_task_status(task_id: str):
    # Mock progression: pending -> processing -> completed
    import time
    import hashlib

    # Use task_id hash to simulate consistent "progression"
    hash_val = int(hashlib.md5(task_id.encode()).hexdigest()[:8], 16)
    elapsed = int(time.time()) - 1700000000  # Some base time
    stage = (hash_val + elapsed) % 30  # 30 second cycle

    if stage < 5:
        return {
            "task_id": task_id,
            "status": "pending",
            "message": "Task queued",
            "progress": 0.0,
        }
    elif stage < 25:
        progress = min(1.0, (stage - 5) / 20.0)
        return {
            "task_id": task_id,
            "status": "processing",
            "message": f"Generating audio... {int(progress * 100)}%",
            "progress": progress,
        }
    else:
        return {
            "task_id": task_id,
            "status": "completed",
            "message": "Audio generation completed",
            "progress": 1.0,
            "result": {
                "files": ["mock_audio_file.mp3"],
                "provider": "openai",
                "voice_id": "nova",
                "text_preview": "This is a test generation...",
                "duration_ms": 3500,
            },
        }


if __name__ == "__main__":
    print("🚀 Starting mock TTS backend server...")
    print("📍 Server: http://127.0.0.1:8000")
    print("📍 Docs: http://127.0.0.1:8000/docs")
    uvicorn.run(app, host="127.0.0.1", port=8000)
