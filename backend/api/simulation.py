import asyncio
import logging
import subprocess
import sys
import os
from typing import Optional, Dict
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/simulation", tags=["simulation"])

class SimulationStart(BaseModel):
    attack_type: str
    rate: int = 10
    duration: int = 30
    mode: str = "SYNTHETIC"

active_simulations: Dict[str, asyncio.subprocess.Process] = {}

@router.post("/start")
async def start_simulation(params: SimulationStart):
    # Stop existing if running
    await stop_simulation()
    
    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts", "mock_ddos_redis.py"))
    
    cmd = [
        sys.executable, script_path,
        "--type", params.attack_type,
        "--rate", str(params.rate),
        "--duration", str(params.duration)
    ]
    
    try:
        process = subprocess.Popen(
            ["python"] + cmd[1:],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )
        active_simulations["current"] = process
        
        return {"status": "started", "pid": process.pid, "params": params.model_dump()}
    except Exception as e:
        import traceback
        err = traceback.format_exc()
        logger.error(f"Failed to start simulation: {err}")
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {str(e)}\n{err}")

@router.post("/stop")
async def stop_simulation():
    process = active_simulations.get("current")
    if process and process.poll() is None:
        try:
            process.terminate()
            process.wait(timeout=2)
        except Exception:
            pass
    active_simulations.pop("current", None)
    return {"status": "stopped"}

@router.get("/status")
async def get_simulation_status():
    process = active_simulations.get("current")
    is_running = process is not None and process.poll() is None
    return {"is_running": is_running}
