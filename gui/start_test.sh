#!/bin/bash

# Quick startup script for testing the TTS Playground

echo "🚀 Starting TTS Playground Test Environment..."

# Kill any existing servers
echo "🧹 Cleaning up existing servers..."
pkill -f "test_server.py" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true
sleep 2

echo "📦 Starting backend server..."
cd gui/backend
uv run python test_server.py &
BACKEND_PID=$!
cd ../..

# Wait for backend to start
sleep 3

echo "🎨 Starting frontend server..."
cd gui/frontend
npm run dev &
FRONTEND_PID=$!
cd ../..

echo ""
echo "🎉 TTS Playground is ready!"
echo ""
echo "📍 Frontend: http://localhost:5173 (or next available port)"
echo "📍 Backend:  http://127.0.0.1:8000"
echo "📍 API Docs: http://127.0.0.1:8000/docs"
echo ""
echo "✨ Features to test:"
echo "  • Provider selection (OpenAI, ElevenLabs)"  
echo "  • Voice library browser with preview"
echo "  • Dynamic configuration forms"
echo "  • Mock audio generation with progress"
echo "  • Real-time status updates"
echo ""
echo "Press Ctrl+C to stop servers"

# Wait for user to stop
wait