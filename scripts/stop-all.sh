#!/bin/bash
# Cyber Threat Visualizer - Stop All Services
# Run from project root: ./scripts/stop-all.sh

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "============================================================"
echo "   CYBER THREAT VISUALIZER - STOP ALL SERVICES"
echo "============================================================"
echo ""

# Kill processes from saved PIDs
if [[ -f "$PROJECT_ROOT/.pids" ]]; then
    PIDS=$(cat "$PROJECT_ROOT/.pids")
    for PID in $PIDS; do
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID" 2>/dev/null
            echo "Stopped process $PID"
        fi
    done
    rm "$PROJECT_ROOT/.pids"
fi

# Fallback: kill by name
pkill -f "python.*api.main" 2>/dev/null && echo "Stopped backend API"
pkill -f "python.*sniffer.packet_sniffer" 2>/dev/null && echo "Stopped packet sniffer"
pkill -f "vite" 2>/dev/null && echo "Stopped frontend"
pkill -f "npm.*dev" 2>/dev/null && echo "Stopped npm"

# Stop Redis Docker container
docker stop redis 2>/dev/null && echo "Stopped Redis container"

echo ""
echo "============================================================"
echo "All services stopped."
echo "============================================================"