#!/bin/bash
# Development startup script

set -e

echo "🚀 Starting Cyber Threat Visualizer Development Environment"

# Check for required tools
command -v docker >/dev/null 2>&1 || { echo "Docker is required but not installed. Aborting." >&2; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "Docker Compose is required but not installed. Aborting." >&2; exit 1; }

# Start Redis
echo "📦 Starting Redis..."
docker-compose up -d redis

# Wait for Redis
echo "⏳ Waiting for Redis..."
until docker-compose exec redis redis-cli ping >/dev/null 2>&1; do
    sleep 1
done
echo "✅ Redis ready"

# Build and start backend
echo "🔧 Building backend..."
docker-compose build backend

echo "🚀 Starting backend..."
docker-compose up -d backend

# Build and start frontend
echo "🎨 Building frontend..."
docker-compose build frontend

echo "🚀 Starting frontend..."
docker-compose up -d frontend

echo ""
echo "✅ All services started!"
echo ""
echo "📊 Dashboard: http://localhost:3000"
echo "🔌 API:       http://localhost:8000"
echo "📝 API Docs:  http://localhost:8000/docs"
echo ""
echo "📋 View logs: docker-compose logs -f"
echo "🛑 Stop:      docker-compose down"