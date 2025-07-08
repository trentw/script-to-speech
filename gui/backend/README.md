# Script-to-Speech GUI Backend

FastAPI backend server for the Script-to-Speech TTS Playground GUI.

## Features

- REST API for TTS provider introspection
- Voice library browsing with preview support
- Async audio generation
- File serving for generated audio
- Real-time configuration validation

## Development

```bash
# Install dependencies
uv pip install -e ".[dev]"

# Run development server
uvicorn sts_gui_backend.main:app --reload --host 127.0.0.1 --port 8000

# Run tests
pytest

# Format code
black .
isort .
```

## API Endpoints

- `GET /api/providers` - List available TTS providers
- `GET /api/providers/{provider}/fields` - Get provider field requirements
- `GET /api/voice-library/{provider}` - Browse voice library for provider
- `GET /api/voice-library/{provider}/{sts_id}` - Get voice details with preview
- `POST /api/generate` - Generate speech audio
- `GET /api/generate/status/{task_id}` - Check generation status
- `GET /api/files/{filename}` - Serve generated audio files