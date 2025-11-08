#!/bin/bash
# Kora Startup Script
# Starts both backend and frontend services

echo "🎯 Starting Kora AI Vision Assistant..."
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.10+"
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+"
    exit 1
fi

# Check if backend dependencies are installed
echo "📦 Checking backend dependencies..."
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "⚠️  Installing backend dependencies..."
    pip install -r requirements.txt
fi

# Check if frontend dependencies are installed
echo "📦 Checking frontend dependencies..."
if [ ! -d "frontend/node_modules" ]; then
    echo "⚠️  Installing frontend dependencies..."
    cd frontend && npm install && cd ..
fi

# Start backend in background
echo ""
echo "🚀 Starting FastAPI backend on http://localhost:8000"
cd vision
uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# Wait for backend to start
echo "⏳ Waiting for backend to initialize..."
sleep 3

# Start frontend in background
echo "🚀 Starting Next.js frontend on http://localhost:3000"
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ Kora is starting up!"
echo ""
echo "📍 Frontend: http://localhost:3000"
echo "📍 Backend API: http://localhost:8000"
echo "📍 API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping Kora services..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo "✅ Services stopped"
    exit 0
}

# Trap Ctrl+C and cleanup
trap cleanup SIGINT SIGTERM

# Wait for processes
wait
