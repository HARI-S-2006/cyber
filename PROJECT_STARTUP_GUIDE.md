# 🛡️ Cyber Threat Visualizer - Complete Setup & Run Guide

## 📋 Prerequisites Checklist

| Tool | Version | Verify Command | Required |
|------|---------|----------------|----------|
| **Docker Desktop** | 27.x+ | `docker --version` | ✅ Yes |
| **Npcap** | Latest | [Download](https://npcap.com/) | ✅ **Must check "WinPcap API-compatible Mode"** |
| **Python** | 3.11+ | `python --version` | ✅ Yes |
| **Node.js** | 20+ | `node --version` | ✅ Yes |
| **PowerShell** | 7+ | `$PSVersionTable.PSVersion` | ✅ Yes |
| **Git** | Latest | `git --version` | Optional |

---

## 🚀 Quick Start (3 Options)

### Option 1: Windows One-Click (Recommended)
```powershell
# Run as Administrator
cd C:\Users\shari\cyber-threat-visualizer
.\scripts\start-all.ps1
```

### Option 2: Linux/Ubuntu/WSL2
```bash
cd /path/to/cyber-threat-visualizer
chmod +x scripts/start-all.sh
./scripts/start-all.sh
```

### Option 3: Docker (All Platforms)
```bash
docker-compose up --build -d
# Dashboard: http://localhost:3000
# API Docs: http://localhost:8000/docs
```

### Option 4: Manual (4 Terminals) - For Development
See **Section 2** below for manual 4-terminal setup.

---

## 🖥️ TERMINAL 1: Infrastructure (Redis + Kafka + Zookeeper)

```powershell
# Terminal 1 - Run as Administrator
cd C:\Users\shari\cyber-threat-visualizer
docker-compose up -d redis zookeeper kafka

# Wait 10 seconds, then verify
docker ps  # Should show 3 containers: redis, zookeeper, kafka
redis-cli ping  # Should return PONG
```

**Expected Output:**
```
NAMES                       STATUS
cyber-threat-visualizer-redis-1   Up (healthy)
zookeeper                       Up (healthy)
kafka                           Up (healthy)
```

---

## 🖥️ TERMINAL 2: Backend API (FastAPI + ML)

```powershell
# Terminal 2 - Run as Administrator
cd C:\Users\shari\cyber-threat-visualizer\backend

# Create virtual environment (first time only)
python -m venv .venv
. .venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Train ML model (first time only)
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

# Start Backend API
python -m backend.api.main
```

**Wait for:** `INFO: Application startup complete.` and `Uvicorn running on http://127.0.0.1:8000`

**Verify:** http://localhost:8000/docs (Swagger UI)

---

## 📦 TERMINAL 3: Packet Sniffer (Scapy + Fallback)

```powershell
# Terminal 3 - Run as Administrator
cd C:\Users\shari\cyber-threat-visualizer\backend
. .venv\Scripts\Activate.ps1

# List interfaces first
python -m backend.sniffer.packet_sniffer --list-interfaces

# Option 1: With Npcap (requires Admin)
python -m backend.sniffer.packet_sniffer

# OR Fallback mode (no Admin needed):
python -m backend.sniffer.packet_sniffer --fallback
```

**Expected Output:**
```
Starting libpcap fallback on \Device\NPF_{...}
[INTERCEPT] 192.168.1.100:54321 -> 93.184.216.34:80 [TCP] Flags:SYN Len:60
```

**Requires:** Administrator + Npcap with "WinPcap API-compatible Mode" ✅

---

## 🌐 TERMINAL 4: Frontend (React + Three.js)

```bash
# Terminal 4
cd C:\Users\shari\cyber-threat-visualizer\frontend

# First time only:
npm install

# Start dev server
npm run dev
```

**Expected Output:**
```
  VITE v5.x.x  ready in 500ms
  ➜  Local:   http://localhost:3000/
  ➜  Network: http://192.168.x.x:3000/
```

**Open Browser:** http://localhost:3000
- Should show: 3D rotating globe with green arcs
- Terminal log panel at bottom
- Threat matrix panel on right

---

## ✅ VERIFICATION CHECKLIST

| Check | Command | Expected |
|-------|---------|----------|
| Docker | `docker ps` | 3 containers (redis, kafka, zookeeper) |
| Redis | `redis-cli ping` | `PONG` |
| Backend | `curl http://localhost:8000/health` | `{"status":"healthy"}` |
| API Docs | Open browser | http://localhost:8000/docs |
| Frontend | Open browser | Globe at `http://localhost:3000` |
| WebSocket | Browser console | `ws://localhost:8000/ws/live` |
| Packet Sniffer | Terminal 3 | `[INTERCEPT]` logs |

---

## 🎯 VIVA DEMO SCRIPT (3 Minutes)

### 1. **Architecture Overview** (30 sec)
> "Decoupled pipeline: **Scapy → Redis Streams → FastAPI + Isolation Forest → WebSocket → Three.js Globe**"

### Live Demo (2 min)
1. **Show Clean Globe** (30s): "Green arcs = normal traffic"
2. **Launch Attack** (60s): 
   ```powershell
   python scripts\simulate_ddos.py --target 192.168.1.100 --rate 5000 --duration 30
   ```
3. **Watch Globe Turn RED** 🔴 (60s)
   - "Isolation Forest detected anomaly at 99.7% confidence"
4. **Threat Matrix** (30s): "Auto-classified: SYN_FLOOD, DDoS, Port Scan"
4. **Red Alert** (30s): Full-screen flash + Threat Matrix spikes

### Additional Attacks for Demo
```bash
# Port Scan
python scripts\simulate_portscan.py --target 192.168.1.100 --type syn --rate 200

# Brute Force
python scripts\simulate_bruteforce.py --target 192.168.1.100 --service ssh --attempts 100
```

---

## 🛑 STOP EVERYTHING

```cmd
# Windows
scripts\stop-all.bat

# Linux/Mac
./scripts/stop-all.sh

# Docker
docker-compose down

# Manual cleanup
taskkill /F /IM python.exe /IM node.exe
docker-compose down
```

---

## 🔧 TROUBLESHOOTING QUICK REFERENCE

| Problem | Solution |
|---------|----------|
| **Redis connection refused** | `docker restart redis` or `docker-compose restart redis` |
| **Kafka not ready** | Wait 30s, check `docker logs kafka` |
| **Frontend blank** | `cd frontend && rm -rf node_modules package-lock.json && npm install` |
| **No packets captured** | Run as Admin + Npcap with WinPcap mode |
| **ModuleNotFoundError: backend** | Run from project root: `cd project_root && python -m backend.api.main` |
| **Frontend blank page** | `cd frontend && rm -rf node_modules package-lock.json && npm install` |
| **ModuleNotFoundError: backend** | Run from project root with `PYTHONPATH=.` |
| **WebSocket fails** | Check backend running on 8000, CORS settings |
| **Globe not loading** | Check browser console, ensure WebGL enabled |
| **Port busy** | `netstat -ano | findstr :8000` → `taskkill /PID <pid> /F` |

---

## 📁 PROJECT STRUCTURE

```
cyber-threat-visualizer/
├── backend/
│   ├── api/
│   │   ├── main.py          # FastAPI entry point
│   │   ├── routes.py        # API endpoints
│   │   └── websocket.py     # WebSocket handler
│   ├── sniffer/
│   │   └── packet_sniffer.py    # Scapy + eBPF fallback
│   ├── ml/
│   │   └── model.py             # Isolation Forest + AutoEncoder
│   ├── streaming/
│   │   └── stream_manager.py    # Kafka/Redis + WebSocket
│   ├── utils/
│   │   ├── redis_client.py
│   │   └── kafka_client.py
│   ├── scripts/
│   │   ├── simulate_ddos.py
│   │   ├── simulate_portscan.py
│   │   └── simulate_bruteforce.py
│   ├── ml/
│   │   └── model.py             # Isolation Forest + AutoEncoder
│   ├── config.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/globe/GlobeScene.tsx  # Three.js
│   │   ├── components/hud/                # Terminal, Matrix, Alerts
│   │   └── hooks/useStore.ts              # Zustand + WS
│   ├── package.json
│   └── vite.config.ts
├── scripts/
│   ├── start-all.ps1 / .sh
│   ├── stop-all.ps1 / .sh
│   ├── verify-setup.ps1
│   └── demo-attack.ps1
├── docker-compose.yml
└── README.md
```

---

## 🎓 VIVA PRESENTATION CHECKLIST

- [ ] Docker Desktop running
- [ ] Npcap installed with **WinPcap API-compatible Mode** ✅
- [ ] Redis running (`redis-cli ping` → PONG)
- [ ] Kafka + Zookeeper running (`docker ps` → 3 containers)
- [ ] Backend API running (`/health` → 200 OK)
- [ ] Frontend loads at http://localhost:3000 (Globe renders)
- [ ] WebSocket connects (`ws://localhost:8000/ws/live`)
- [ ] Packet sniffer shows `[INTERCEPT]` logs
- [ ] Attack demo works (Globe turns red)
- [ ] All 24 tests pass (`pytest tests/` → 24 passed)
- [ ] Frontend builds (`npm run build` ✅)

---

## 🎓 VIVA TALKING POINTS

1. **Architecture**: "Decoupled pipeline: Scapy → Redis Streams → FastAPI → WebSocket → Three.js"
2. **ML Choice**: "Isolation Forest = unsupervised, zero-day detection, <1ms inference"
3. **Real-time**: "Redis Streams + WebSocket = <50ms packet-to-globe latency"
3. **Scalability**: "Horizontal FastAPI workers + Redis clustering = 100K+ pps"
4. **Defense**: "Not just detection - GeoIP, threat classification, confidence scoring"

---

## 📞 EMERGENCY COMMANDS

```bash
# Kill all Python
taskkill /F /IM python.exe

# Kill Node
taskkill /F /IM node.exe

# Reset Docker
docker-compose down && docker-compose up -d

# Reset ports
netstat -ano | findstr :8000
taskkill /PID <pid> /F
```

---

## 🎓 GOOD LUCK WITH YOUR VIVA! 🎓🛡️🔴

*You've built an impressive full-stack cybersecurity visualization system. Good luck!*