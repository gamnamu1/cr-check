#!/bin/bash

# Check for API Key
if [ -f "backend/.env" ]; then
    echo "✅ Found backend/.env file. Using it for configuration."
elif [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "⚠️  Warning: ANTHROPIC_API_KEY is not set in environment and no .env file found."
    echo "Please set it before running: export ANTHROPIC_API_KEY='your-key-here'"
    echo "Continuing anyway (backend might fail on analysis)..."
    sleep 2
else
    echo "✅ ANTHROPIC_API_KEY is set in environment."
fi

# Kill ports 8000 and 3000 if running
echo "🧹 Cleaning up ports..."
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:3000 | xargs kill -9 2>/dev/null

# Start Backend
echo "🚀 Starting Backend (FastAPI)..."
cd backend
# Check if venv exists, if so activate it
if [ -d "venv" ]; then
    source venv/bin/activate
fi
# Install requirements if needed (optional, skipping to save time)
# pip install -r requirements.txt

PYTHONUNBUFFERED=1 uvicorn main:app --reload --port 8000 > backend_stdout.log 2>&1 &
BACKEND_PID=$!
cd ..

# Wait for backend to start
sleep 3

# Start Frontend
echo "🚀 Starting Frontend (Next.js)..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo "✅ Servers started!"
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo "Press CTRL+C to stop both servers."

# Handle shutdown
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT

wait
