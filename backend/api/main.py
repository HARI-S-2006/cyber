"""Main FastAPI application for Cyber Threat Visualizer."""
import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from backend.config import settings
from backend.utils.redis_client import redis_manager
from backend.api.routes import router
from backend.api.websocket import ws_manager
from backend.api.simulation import router as simulation_router
from backend.ml.model import detection_service
from backend.sniffer.geoip_cache import geoip_cache

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format=settings.log_format
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Cyber Threat Visualizer API...")
    
    # Store start time
    settings._start_time = time.time()
    
    # Initialize Redis
    await redis_manager.connect()
    logger.info("Redis connected")
    
    # Initialize ML detection service
    await detection_service.initialize()
    logger.info("ML detection service initialized")
    
    # Initialize GeoIP cache
    logger.info("GeoIP cache initialized")
    
    # Start WebSocket manager
    await ws_manager.start_redis_listener()
    logger.info("WebSocket manager started")
    
    logger.info("Cyber Threat Visualizer API started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Cyber Threat Visualizer API...")
    
    # Stop WebSocket manager
    await ws_manager.stop()
    logger.info("WebSocket manager stopped")
    
    # Shutdown detection service
    await detection_service.shutdown()
    logger.info("Detection service stopped")
    
    # Disconnect Redis
    await redis_manager.disconnect()
    logger.info("Redis disconnected")
    
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title="Cyber Threat Visualizer API",
        description="Real-time network threat detection and visualization API",
        version="2.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API routes
    app.include_router(router, prefix="/api/v1")
    app.include_router(simulation_router, prefix="/api/v1")
    
    # WebSocket endpoint
    @app.websocket("/ws/live")
    async def websocket_endpoint(websocket: WebSocket):
        client_id = f"client_{int(time.time() * 1000)}"
        
        # Accept connection
        connection = await ws_manager.connect(websocket, client_id)
        
        try:
            # Send welcome message
            await websocket.send_json({
                "type": "welcome",
                "data": {
                    "client_id": client_id,
                    "message": "Connected to Cyber Threat Visualizer",
                    "timestamp": time.time()
                },
                "timestamp": time.time()
            })
            
            # Keep connection alive and handle incoming messages
            while True:
                try:
                    data = await websocket.receive_json()
                    
                    # Handle client messages
                    msg_type = data.get("type")
                    
                    if msg_type == "ping":
                        await websocket.send_json({
                            "type": "pong",
                            "timestamp": time.time()
                        })
                    elif msg_type == "subscribe":
                        channel = data.get("channel")
                        if channel:
                            await ws_manager.subscribe(connection.client_id, channel)
                            await websocket.send_json({
                                "type": "subscribed",
                                "data": {"channel": channel},
                                "timestamp": time.time()
                            })
                    elif msg_type == "unsubscribe":
                        channel = data.get("channel")
                        if channel:
                            await ws_manager.unsubscribe(connection.client_id, channel)
                            await websocket.send_json({
                                "type": "unsubscribed",
                                "data": {"channel": channel},
                                "timestamp": time.time()
                            })
                    elif msg_type == "get_stats":
                        stats = ws_manager.get_stats()
                        await websocket.send_json({
                            "type": "stats",
                            "data": stats,
                            "timestamp": time.time()
                        })
                        
                except WebSocketDisconnect:
                    await ws_manager.disconnect(connection.client_id)
                except Exception as e:
                    logger.error(f"WebSocket error: {e}")
                    break
                    
        except WebSocketDisconnect:
            await ws_manager.disconnect(connection.client_id)
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            await ws_manager.disconnect(connection.client_id)
    
    @app.get("/")
    async def root():
        return {
            "name": "Cyber Threat Visualizer API",
            "version": "2.0.0",
            "status": "running",
            "docs": "/docs",
            "websocket": "/ws/live"
        }
    
    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "version": "2.0.0"
        }
    
    return app


# Create the app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "backend.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )