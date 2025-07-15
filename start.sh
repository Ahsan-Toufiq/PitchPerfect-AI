#!/bin/bash

# PitchPerfect AI Startup Script
echo "🚀 Starting PitchPerfect AI..."

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Please run: python -m venv .venv"
    exit 1
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source .venv/bin/activate

# Check if dependencies are installed
if ! python -c "import fastapi" 2>/dev/null; then
    echo "📥 Installing Python dependencies..."
    pip install -r requirements.txt
    pip install email-validator loguru tldextract
fi

# Install Playwright browsers if not already installed
if [ ! -d "$HOME/.cache/ms-playwright" ]; then
    echo "🌐 Installing Playwright browsers..."
    playwright install
fi

# Start backend
echo "🔧 Starting backend server..."
python server.py &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Start frontend
echo "🎨 Starting frontend server..."
cd frontend && npm run dev &
FRONTEND_PID=$!

# Wait for frontend to start
sleep 3

echo ""
echo "✅ PitchPerfect AI is now running!"
echo ""
echo "🌐 Frontend: http://localhost:5173"
echo "🔧 Backend API: http://localhost:8000"
echo "📚 API Documentation: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all servers"

# Wait for user to stop
wait 