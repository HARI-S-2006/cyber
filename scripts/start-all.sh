#!/bin/bash
# Cyber Threat Visualizer - Linux/Ubuntu/WSL2 Startup Script
# Run from project root: ./scripts/start-all.sh
# Requires: Docker, Python 3.11+, Node.js 20+, Npcap (not needed on Linux)

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if running as root (needed for packet capture)
if [[ $EUID -ne 0 ]]; then
    log_warn "Not running as root - packet capture will use fallback mode"
    log_warn "For full eBPF capture, run with: sudo ./scripts/start-all.sh"
fi

# Check prerequisites
check_command() {
    if command -v "$1" &> /dev/null; then
        log_ok "$1: $($1 --version 2>&1 | head -1)"
        return 0
    else
        log_error "$1 not found"
        return 1
    fi
}

log_info "Checking prerequisites..."
MISSING=0
check_command docker || MISSING=1
check_command docker compose || MISSING=1
check_command python3 || MISSING=1
check_command node || MISSING=1
check_command npm || MISSING=1
check_command redis-cli || MISSING=1

if [[ $MISSING -eq 1 ]]; then
    log_error "Missing prerequisites. Install them first:"
    echo "  Ubuntu: sudo apt update && sudo apt install -y docker.io docker-compose python3 python3-pip nodejs npm redis-tools"
    echo "  Then: sudo usermod -aG docker \$USER && newgrp docker"
    exit 1
fi

# Check Docker daemon
if ! docker info >/dev/null 2>&1; then
    log_error "Docker daemon not running. Start with: sudo systemctl start docker"
    exit 1
fi

log_ok "All prerequisites met"

# 1. Start infrastructure services
log_info "Starting infrastructure services (Redis, Kafka, Zookeeper)..."
docker compose up -d redis zookeeper kafka

log_info "Waiting for services to be healthy..."
sleep 5

# Wait for Redis
for i in {1..10}; do
    if redis-cli ping >/dev/null 2>&1; then
        log_ok "Redis ready"
        break
    fi
    sleep 1
done

# Wait for Kafka
for i in {1..15}; do
    if docker exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092 >/dev/null 2>&1; then
        log_ok "Kafka ready"
        break
    fi
    sleep 2
done

# 2. Setup Python environment
log_info "Setting up Python environment..."
cd "$PROJECT_ROOT/backend"
if [[ ! -d ".venv" ]]; then
    log_info "Creating virtual environment..."
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q -r requirements.txt
log_ok "Python dependencies ready"

# 3. Install Node dependencies
log_info "Installing Node.js dependencies..."
cd "$PROJECT_ROOT/frontend"
if [[ ! -d "node_modules" ]]; then
    npm install --silent 2>/dev/null
fi
log_ok "Node.js dependencies ready"

# 3. Build frontend
log_info "Building frontend..."
npm run build 2>/dev/null
log_ok "Frontend built"

# 4. Train ML model if needed
if [[ ! -f "$PROJECT_ROOT/backend/ml/models/anomaly_detector.pkl" ]]; then
    log_info "Training ML model..."
    cd "$PROJECT_ROOT/backend"
    source .venv/bin/activate
    python -c "
from ml.model import AnomalyDetector, ModelConfig, generate_synthetic_data
from pathlib import Path
detector = AnomalyDetector(ModelConfig())
X, y = generate_synthetic_data(5000, 0.05)
detector.fit(X)
Path('ml/models').mkdir(parents=True, exist_ok=True)
detector.save('ml/models/anomaly_detector.pkl')
print('Model trained and saved')
"
    log_ok "ML model trained"
fi

# 5. Start services in background
log_info "Starting services..."

# Backend API
cd "$PROJECT_ROOT/backend"
source .venv/bin/activate
nohup python -m api.main > backend.log 2>&1 &
BACKEND_PID=$!
sleep 3
if curl -s http://localhost:8000/api/v1/stats >/dev/null; then
    log_ok "Backend API running on http://localhost:8000 (PID: $BACKEND_PID)"
else
    log_error "Backend failed to start. Check backend.log"
    cat backend.log
    exit 1
fi

# Packet Sniffer (fallback mode)
nohup python -m sniffer.packet_sniffer --fallback > sniffer.log 2>&1 &
SNIFFER_PID=$!
sleep 2
log_ok "Packet sniffer started (PID: $SNIFFER_PID)"

# Frontend
cd "$PROJECT_ROOT/frontend"
nohup npm run dev -- --host 0.0.0.0 > frontend.log 2>&1 &
FRONTEND_PID=$!
sleep 5
if curl -s http://localhost:3000 >/dev/null; then
    log_ok "Frontend running on http://localhost:3000 (PID: $FRONTEND_PID)"
else
    log_error "Frontend failed to start. Check frontend.log"
    exit 1
fi

# Save PIDs for cleanup
echo "$BACKEND_PID $SNIFFER_PID $FRONTEND_PID" > "$PROJECT_ROOT/.pids"

echo ""
echo "============================================================"
echo -e "${GREEN}[SUCCESS] All services started!${NC}"
echo "============================================================"
echo ""
echo -e "${BLUE}Access Points:${NC}"
echo "  🌐 Command Center:  http://localhost:3000"
echo "  📚 API Docs:        http://localhost:8000/docs"
echo "  📊 Live Stats:      http://localhost:8000/api/v1/stats"
echo "  🔌 WebSocket:       ws://localhost:8000/ws/live"
echo "  📨 Kafka UI:        http://localhost:9101 (if kafka-ui enabled)"
echo ""
echo -e "${YELLOW}Process IDs saved to .pids${NC}"
echo -e "${YELLOW}Stop all: ./scripts/stop-all.sh${NC}"
echo ""

# Keep script running to show logs
log_info "Showing backend logs (Ctrl+C to stop all)..."
tail -f backend.log sniffer.log frontend.log 2>/dev/null