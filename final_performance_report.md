# Live Cyber-Threat Visualizer & Packet Sniffer
## Final Performance & QA Report

### Overview
The Live Cyber-Threat Visualizer is a comprehensive cybersecurity monitoring platform featuring real-time packet sniffing, anomaly detection via machine learning, and interactive 3D web visualizations. This report summarizes the finalized architecture, recent fixes, and the operational status of the platform.

### Architecture Summary
- **Frontend:** React, Vite, TailwindCSS, React-Three-Fiber (WebGL Globe)
- **Backend:** Python, FastAPI, Uvicorn, Scikit-Learn
- **Event Streaming:** Redis Pub/Sub, WebSockets
- **Infrastructure:** Docker Desktop (Redis, Zookeeper, Kafka)

### QA and Bug Fixes

#### 1. Backend Simulation Reliability (Windows Subprocess Fix)
- **Issue:** The synthetic attack simulation (`mock_ddos_redis.py`) failed to run on Windows due to an incompatibility with `asyncio.create_subprocess_exec` on the default Windows event loop (ProactorEventLoop).
- **Resolution:** Refactored `backend/api/simulation.py` to use `subprocess.Popen` with `creationflags=subprocess.CREATE_NEW_PROCESS_GROUP`. Additionally, the script path was resolved to absolute paths using `os.path.abspath(__file__)` to ensure that Uvicorn can find the script regardless of the current working directory.
- **Result:** The `POST /api/v1/simulation/start` endpoint successfully spawns detached Python processes that continuously publish threat metrics to Redis.

#### 2. Frontend UI Enhancement & Integration
- **Issue:** The "Attack Console" and "Threat Matrix" overlays were previously unlinked or throwing errors, leading to a blank page on the frontend (React ErrorBoundary catch).
- **Resolution:** 
  - Integrated `AttackConsole.tsx` into the main `App.tsx` layout.
  - Fixed syntax errors and string interpolations in `className` properties within the React components.
  - Ensured the UI adheres to the "Live Command Center" aesthetic (neon cyan/red, glassmorphism, dark mode).
- **Result:** The frontend robustly connects via WebSockets and renders live 3D attack arcs. When the simulation is triggered, the globe turns red and threats are aggregated and displayed in real time in the Threat Matrix.

### Operational Instructions
To launch the entire platform, run the provided startup script in an Administrator PowerShell window:
```powershell
.\scripts\start-all.ps1
```
*(Note: Never use `stop-all.ps1` as per strict project guidelines. Terminate the windows manually if needed.)*

### Simulation Testing
1. Navigate to `http://localhost:3000`.
2. Locate the **ATTACK CONSOLE** floating on the dashboard.
3. Click **LAUNCH SYN**.
4. The system will start generating synthetic attack traffic.
5. Watch the 3D globe transition to a red alert state and the **THREAT INTELLIGENCE** panel populate with real-time anomalies.

### Status
**Passed QA.** The platform is fully operational, stable, and ready for demonstration.
