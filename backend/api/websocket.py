"""WebSocket manager for real-time data streaming."""
import asyncio
import json
import logging
import time
from typing import Dict, Set
from dataclasses import dataclass, field

from fastapi import WebSocket, WebSocketDisconnect

from backend.utils.redis_client import redis_manager
from backend.config import settings

logger = logging.getLogger(__name__)


@dataclass
class Connection:
    """Represents a WebSocket connection."""
    websocket: WebSocket
    client_id: str
    connected_at: float = field(default_factory=time.time)
    subscriptions: Set[str] = field(default_factory=set)
    last_ping: float = field(default_factory=time.time)


class WebSocketManager:
    """Manages WebSocket connections and message broadcasting."""
    
    def __init__(self):
        self.connections: Dict[str, Connection] = {}
        self._redis_listener_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def connect(self, websocket: WebSocket, client_id: str) -> Connection:
        """Accept a new WebSocket connection."""
        await websocket.accept()
        
        connection = Connection(
            websocket=websocket,
            client_id=client_id
        )
        self.connections[client_id] = connection
        
        # Subscribe to default channels
        await self.subscribe(client_id, "packets")
        await self.subscribe(client_id, "threats")
        await self.subscribe(client_id, "stats")
        
        logger.info(f"Client {client_id} connected. Total connections: {len(self.connections)}")
        return connection
    
    async def disconnect(self, client_id: str) -> None:
        """Disconnect a client."""
        if client_id in self.connections:
            conn = self.connections.pop(client_id)
            try:
                await conn.websocket.close()
            except Exception:
                pass
            logger.info(f"Client {client_id} disconnected. Total connections: {len(self.connections)}")
    
    async def subscribe(self, client_id: str, channel: str) -> bool:
        """Subscribe a client to a channel."""
        if client_id not in self.connections:
            return False
        
        conn = self.connections[client_id]
        conn.subscriptions.add(channel)
        
        # Subscribe to Redis channel if not already
        await redis_manager.subscribe(settings.channel_features, self._redis_message_handler)
        await redis_manager.subscribe(settings.channel_threats, self._redis_message_handler)
        await redis_manager.subscribe(settings.channel_stats, self._redis_message_handler)
        
        return True
    
    async def unsubscribe(self, client_id: str, channel: str) -> bool:
        """Unsubscribe a client from a channel."""
        if client_id not in self.connections:
            return False
        
        self.connections[client_id].subscriptions.discard(channel)
        return True
    
    async def send_personal(self, client_id: str, message: dict) -> bool:
        """Send a message to a specific client."""
        if client_id not in self.connections:
            return False
        
        conn = self.connections[client_id]
        try:
            await conn.websocket.send_json(message)
            return True
        except Exception as e:
            logger.error(f"Error sending to {client_id}: {e}")
            await self.disconnect(client_id)
            return False
    
    async def broadcast(self, channel: str, message: dict, exclude: Optional[str] = None) -> int:
        """Broadcast a message to all clients subscribed to a channel."""
        count = 0
        for client_id, conn in self.connections.items():
            if client_id == exclude:
                continue
            if channel in conn.subscriptions:
                try:
                    await conn.websocket.send_json(message)
                    count += 1
                except Exception as e:
                    logger.error(f"Broadcast error to {client_id}: {e}")
                    # Don't disconnect here, let the receive loop handle it
        return count
    
    async def broadcast_all(self, message: dict) -> int:
        """Broadcast to all connected clients."""
        count = 0
        for client_id, conn in self.connections.items():
            try:
                await conn.websocket.send_json(message)
                count += 1
            except Exception as e:
                logger.error(f"Broadcast error to {client_id}: {e}")
        return count
    
    async def _redis_message_handler(self, message: dict) -> None:
        """Handle messages from Redis pub/sub."""
        # Determine message type from content
        msg_type = "packet"
        if "threat_type" in message or message.get("anomaly"):
            msg_type = "threat"
        elif "packets_per_sec" in message:
            msg_type = "stats"
        
        # Create WS message
        ws_message = {
            "type": msg_type,
            "data": message,
            "timestamp": time.time()
        }
        
        # Broadcast to appropriate subscribers
        channel_map = {
            "packet": "packets",
            "threat": "threats",
            "stats": "stats"
        }
        channel = channel_map.get(msg_type, "packets")
        await self.broadcast(channel, ws_message)
    
    async def start_redis_listener(self) -> None:
        """Start listening to Redis pub/sub."""
        if self._running:
            return
        
        self._running = True
        self._redis_listener_task = asyncio.create_task(self._listen_redis())
        logger.info("WebSocket Redis listener started")
    
    async def _listen_redis(self) -> None:
        """Listen for Redis messages and broadcast to WebSocket clients."""
        try:
            # Subscribe to channels
            await redis_manager.subscribe(settings.channel_features, self._handle_redis_message)
            await redis_manager.subscribe(settings.channel_threats, self._handle_redis_message)
            await redis_manager.subscribe(settings.channel_stats, self._handle_redis_message)
            
            logger.info("Redis listener started for WebSocket broadcasting")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Redis listener error: {e}")
    
    async def _handle_redis_message(self, message: dict) -> None:
        """Process incoming Redis message and broadcast to WebSocket clients."""
        msg_type = "packet"
        if message.get("anomaly") or message.get("threat_type"):
            msg_type = "threat"
        elif "packets_per_sec" in message:
            msg_type = "stats"
        
        ws_message = {
            "type": msg_type,
            "data": message,
            "timestamp": time.time()
        }
        
        channel_map = {
            "packet": "packets",
            "threat": "threats",
            "stats": "stats"
        }
        channel = channel_map.get(msg_type, "packets")
        await self.broadcast(channel, ws_message)
    
    async def stop(self) -> None:
        """Stop the WebSocket manager."""
        self._running = False
        
        if self._redis_listener_task:
            self._redis_listener_task.cancel()
            try:
                await self._redis_listener_task
            except asyncio.CancelledError:
                pass
        
        # Disconnect all clients
        for client_id in list(self.connections.keys()):
            await self.disconnect(client_id)
        
        logger.info("WebSocket manager stopped")
    
    def get_connection_count(self) -> int:
        """Get number of active connections."""
        return len(self.connections)
    
    def get_stats(self) -> dict:
        """Get connection statistics."""
        return {
            "total_connections": len(self.connections),
            "subscriptions": {
                client_id: list(conn.subscriptions)
                for client_id, conn in self.connections.items()
            }
        }


# Global WebSocket manager
ws_manager = WebSocketManager()