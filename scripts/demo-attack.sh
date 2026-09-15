#!/bin/bash
# Cyber Threat Visualizer - Attack Demo Script
# Run from project root: ./scripts/demo-attack.sh

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}   CYBER THREAT VISUALIZER - ATTACK DEMO${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""

# Check if services are running
if ! curl -s http://localhost:8000/api/v1/stats >/dev/null; then
    echo -e "${RED}[ERROR] Backend not running. Start services first:${NC}"
    echo "  ./scripts/start-all.sh"
    exit 1
fi

echo -e "${GREEN}[OK] Services are running${NC}"
echo ""
echo -e "${YELLOW}Opening Command Center...${NC}"
echo "  Open: http://localhost:3000"
echo ""
echo -e "${YELLOW}Starting attack simulation in 3 seconds...${NC}"
sleep 3

# Run DDoS simulation
echo -e "${RED}[ATTACK] Starting SYN Flood DDoS simulation...${NC}"
cd "$PROJECT_ROOT/backend"
source .venv/bin/activate
python scripts/simulate_ddos.py --target 192.168.1.100 --rate 5000 --duration 30

echo ""
echo -e "${GREEN}[DEMO COMPLETE]${NC}"
echo "Check the Command Center at http://localhost:3000"
echo "  - Globe should show RED arcs"
echo "  - Terminal log should show [INTERCEPT] entries"
echo "  - Threat Matrix should show DDoS/SYN_FLOOD"
echo "  - Red Alert should have flashed"
echo ""
echo "Run other simulations:"
echo "  cd backend && python scripts/simulate_portscan.py --target 192.168.1.100 --type syn"
echo "  cd backend && python scripts/simulate_bruteforce.py --target 192.168.1.100 --service ssh"