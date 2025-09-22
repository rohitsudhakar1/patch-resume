#!/bin/bash

# Resume Builder - Quick Start Script
# This script helps you get the application running quickly

set -e

echo "🚀 Resume Builder - Quick Start"
echo "================================"

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp env.example .env
    echo "⚠️  Please edit .env file and add your OpenAI API key!"
    echo "   nano .env"
    echo ""
    read -p "Press Enter after you've added your OpenAI API key..."
fi

# Check if Docker is available
if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
    echo "🐳 Docker detected. Starting with Docker Compose..."
    
    # Start services
    docker-compose up -d postgres redis
    echo "⏳ Waiting for database to be ready..."
    sleep 10
    
    # Build and start backend
    docker-compose up -d backend
    
    echo "🔧 Starting frontend..."
    npm install
    npm run dev &
    
    echo ""
    echo "✅ Application is starting up!"
    echo "🌐 Frontend: http://localhost:5173"
    echo "🔧 Backend API: http://localhost:8000"
    echo "📚 API Docs: http://localhost:8000/docs"
    echo ""
    echo "Press Ctrl+C to stop all services"
    
    # Wait for user to stop
    wait
    
else
    echo "🐍 Docker not found. Starting manually..."
    echo ""
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        echo "❌ Python 3 is required but not installed"
        exit 1
    fi
    
    # Check Node.js
    if ! command -v node &> /dev/null; then
        echo "❌ Node.js is required but not installed"
        exit 1
    fi
    
    # Check PostgreSQL
    if ! command -v psql &> /dev/null; then
        echo "❌ PostgreSQL is required but not installed"
        exit 1
    fi
    
    # Check Redis
    if ! command -v redis-server &> /dev/null; then
        echo "❌ Redis is required but not installed"
        exit 1
    fi
    
    echo "📦 Installing Python dependencies..."
    pip install -r requirements.txt
    
    echo "📦 Installing Node.js dependencies..."
    npm install
    
    echo "🗄️  Starting PostgreSQL..."
    sudo systemctl start postgresql 2>/dev/null || brew services start postgresql 2>/dev/null || echo "Please start PostgreSQL manually"
    
    echo "🔄 Starting Redis..."
    redis-server --daemonize yes 2>/dev/null || brew services start redis 2>/dev/null || echo "Please start Redis manually"
    
    echo "🐍 Starting Python backend..."
    python -m uvicorn backend.main:app --reload --port 8000 &
    BACKEND_PID=$!
    
    echo "⏳ Waiting for backend to start..."
    sleep 5
    
    echo "⚛️  Starting React frontend..."
    npm run dev &
    FRONTEND_PID=$!
    
    echo ""
    echo "✅ Application is running!"
    echo "🌐 Frontend: http://localhost:5173"
    echo "🔧 Backend API: http://localhost:8000"
    echo "📚 API Docs: http://localhost:8000/docs"
    echo ""
    echo "Press Ctrl+C to stop all services"
    
    # Cleanup function
    cleanup() {
        echo ""
        echo "🛑 Stopping services..."
        kill $BACKEND_PID 2>/dev/null || true
        kill $FRONTEND_PID 2>/dev/null || true
        exit 0
    }
    
    # Trap Ctrl+C
    trap cleanup SIGINT
    
    # Wait for user to stop
    wait
fi
