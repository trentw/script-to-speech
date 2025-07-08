#!/bin/bash

# Script to start both backend and frontend for development

set -e

echo "🚀 Starting Script-to-Speech TTS Playground..."

# Function to cleanup background processes
cleanup() {
    echo "🛑 Shutting down servers..."
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    exit 0
}

# Set up cleanup on script exit
trap cleanup SIGINT SIGTERM EXIT

# Check if we're in the right directory
if [ ! -d "gui" ]; then
    echo "❌ Error: Please run this script from the script-to-speech root directory"
    exit 1
fi

echo "📦 Installing/updating dependencies..."

# Install backend dependencies
echo "  - Backend dependencies..."
cd gui/backend
uv pip install -e . > /dev/null 2>&1
cd ../..

# Install frontend dependencies
echo "  - Frontend dependencies..."
cd gui/frontend
npm install > /dev/null 2>&1
cd ../..

echo "🔧 Starting backend server..."
cd gui/backend
uv run python -m sts_gui_backend.main &
BACKEND_PID=$!
cd ../..

# Wait a moment for backend to start
sleep 3

# Check if backend is running
if ! curl -s http://127.0.0.1:8000/health > /dev/null; then
    echo "❌ Backend failed to start"
    exit 1
fi
echo "✅ Backend server running at http://127.0.0.1:8000"

echo "🎨 Starting frontend server..."
cd gui/frontend
npm run dev &
FRONTEND_PID=$!
cd ../..

echo ""
echo "🎉 TTS Playground is starting up!"
echo ""
echo "📍 Frontend: http://localhost:5173"
echo "📍 Backend:  http://127.0.0.1:8000"
echo "📍 API Docs: http://127.0.0.1:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers"
echo ""

# Wait for user to stop
wait