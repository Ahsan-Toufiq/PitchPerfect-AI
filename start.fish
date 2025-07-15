#!/usr/bin/env fish

# PitchPerfect AI Startup Script (Fish Shell)
echo "🚀 Starting PitchPerfect AI..."

# Check if virtual environment exists
if not test -d ".venv"
    echo "❌ Virtual environment not found. Please run: python -m venv .venv"
    exit 1
end

# Activate virtual environment
echo "📦 Activating virtual environment..."
source .venv/bin/activate.fish

# Check if dependencies are installed
if not python -c "import fastapi" 2>/dev/null
    echo "📥 Installing Python dependencies..."
    pip install -r requirements.txt
    pip install email-validator loguru tldextract
end

# Install Playwright browsers if not already installed
if not test -d "$HOME/.cache/ms-playwright"
    echo "🌐 Installing Playwright browsers..."
    playwright install
end

# Start backend
echo "🔧 Starting backend server..."
python server.py &
set BACKEND_PID $last_pid

# Wait for backend to start
sleep 3

# Start frontend
echo "🎨 Starting frontend server..."
cd frontend && npm run dev &
set FRONTEND_PID $last_pid

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