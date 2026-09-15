"""Redis client utilities for the Cyber Threat Visualizer."""
import asyncio
import json
import logging
from typing import Any, Callable, Optional
from contextlib import asynccontextmanager

import redis.asyncio as redis
from redis.asyncio import Redis

from backend.config import settings

logger = logging.getLogger(__name__)


class RedisManager:
    """Manages Redis connections and pub/sub operations with retry logic."""
    
    def __init__(self):
        self._redis: Optional[Redis] = None
        self._pubsub: Optional[redis.client.PubSub] = None
        self._subscribers: dict[str, list[Callable]] = {}
        self._listening = False
        self._listen_task: Optional[asyncio.Task] = None
        self._connection_lock = asyncio.Lock()
    
    async def connect(self, max_retries: int = 10, base_delay: float = 1.0) -> None:
        """Initialize Redis connection with retry logic."""
        async with self._connection_lock:
            if self._redis is not None:
                return
            
            last_exception = None
            for attempt in range(max_retries):
                try:
                    self._redis = redis.from_url(
                        settings.redis_url,
                        encoding="utf-8",
                        decode_responses=True,
                        max_connections=20,
                        protocol=2,  # Force RESP2 to avoid HELLO command issues
                        socket_connect_timeout=10,
                        socket_timeout=10,
                        retry_on_timeout=True,
                        health_check_interval=30,
                    )
                    
                    # Test connection with retries
                    for ping_attempt in range(3):
                        try:
                            await self._redis.ping()
                            logger.info(f"Connected to Redis at {settings.redis_host}:{settings.redis_port}")
                            return
                        except Exception as ping_error:
                            if ping_attempt == 2:
                                raise
                            await asyncio.sleep(0.5 * (ping_attempt + 1))
                    
                except Exception as e:
                    last_exception = e
                    logger.warning(f"Redis connection attempt {attempt + 1}/{max_retries} failed: {e}")
                    if self._redis:
                        try:
                            await self._redis.close()
                        except Exception:
                            pass
                        self._redis = None
                    
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)  # Exponential backoff
                        logger.info(f"Retrying Redis connection in {delay}s (attempt {attempt + 2}/{max_retries})")
                        await asyncio.sleep(delay)
            
            logger.error(f"Failed to connect to Redis after {max_retries} attempts")
            raise last_exception or Exception("Failed to connect to Redis")
    
    async def ping(self) -> bool:
        """Test Redis connection."""
        if self._redis is None:
            return False
        try:
            return await self._redis.ping()
        except Exception:
            return False
    
    async def disconnect(self) -> None:
        """Close Redis connection."""
        self._listening = False
        
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
        
        if self._pubsub:
            await self._pubsub.unsubscribe()
            await self._pubsub.close()
        
        if self._redis:
            await self._redis.close()
            self._redis = None
        
        logger.info("Disconnected from Redis")
    
    async def publish(self, channel: str, message: dict) -> int:
        """Publish a message to a channel."""
        if not self._redis:
            await self.connect()
        
        payload = json.dumps(message, default=str)
        return await self._redis.publish(channel, payload)
    
    async def publish_json(self, channel: str, data: dict) -> int:
        """Publish JSON data to a channel."""
        return await self.publish(channel, data)
    
    async def subscribe(self, channel: str, callback: Callable[[dict], None]) -> None:
        """Subscribe to a channel with a callback."""
        if channel not in self._subscribers:
            self._subscribers[channel] = []
        self._subscribers[channel].append(callback)
        
        if not self._listening:
            await self._start_listening()
    
    async def unsubscribe(self, channel: str, callback: Callable[[dict], None]) -> None:
        """Unsubscribe a callback from a channel."""
        if channel in self._subscribers:
            self._subscribers[channel].remove(callback)
            if not self._subscribers[channel]:
                del self._subscribers[channel]
    
    async def _start_listening(self) -> None:
        """Start the Redis pub/sub listener."""
        if self._listening:
            return
            
        self._listening = True
        self._pubsub = self._redis.pubsub()
        
        # Subscribe to all registered channels
        for channel in self._subscribers:
            await self._pubsub.subscribe(channel)
        
        self._listen_task = asyncio.create_task(self._listen_loop())
        logger.info("Started Redis pub/sub listener")
    
    async def _listen_loop(self) -> None:
        """Listen for messages on subscribed channels."""
        try:
            async for message in self._pubsub.listen():
                if message["type"] == "message":
                    channel = message["channel"]
                    data = message["data"]
                    
                    try:
                        parsed = json.loads(data)
                    except json.JSONDecodeError:
                        parsed = {"raw": data}
                    
                    # Call all callbacks for this channel
                    for callback in self._subscribers.get(channel, []):
                        try:
                            if asyncio.iscoroutinefunction(callback):
                                await callback(parsed)
                            else:
                                callback(parsed)
                        except Exception as e:
                            logger.error(f"Error in subscriber callback for {channel}: {e}")
        except asyncio.CancelledError:
            logger.info("Redis listener cancelled")
        except Exception as e:
            logger.error(f"Redis listener error: {e}")
            self._listening = False
    
    # Key-Value Operations
    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """Set a key-value pair with optional expiration."""
        if not self._redis:
            await self.connect()
        return await self._redis.set(key, json.dumps(value, default=str), ex=expire)
    
    async def get(self, key: str) -> Optional[Any]:
        """Get a value by key."""
        if not self._redis:
            await self.connect()
        data = await self._redis.get(key)
        if data:
            return json.loads(data)
        return None
    
    async def delete(self, key: str) -> int:
        """Delete a key."""
        if not self._redis:
            await self.connect()
        return await self._redis.delete(key)
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        if not self._redis:
            await self.connect()
        return await self._redis.exists(key) > 0
    
    async def incr(self, key: str) -> int:
        """Increment a counter."""
        if not self._redis:
            await self.connect()
        return await self._redis.incr(key)
    
    async def hset(self, name: str, key: str, value: Any) -> int:
        """Set hash field."""
        if not self._redis:
            await self.connect()
        return await self._redis.hset(name, key, json.dumps(value, default=str))
    
    async def hget(self, name: str, key: str) -> Optional[Any]:
        """Get hash field."""
        if not self._redis:
            await self.connect()
        data = await self._redis.hget(name, key)
        if data:
            return json.loads(data)
        return None
    
    async def hgetall(self, name: str) -> dict:
        """Get all hash fields."""
        if not self._redis:
            await self.connect()
        data = await self._redis.hgetall(name)
        return {k: json.loads(v) for k, v in data.items()}
    
    # Streams (for time-series data)
    async def xadd(self, stream: str, data: dict, maxlen: int = 10000) -> str:
        """Add entry to a stream."""
        if not self._redis:
            await self.connect()
        return await self._redis.xadd(stream, data, maxlen=maxlen)
    
    async def xread(self, streams: dict[str, str], count: int = 100, block: int = 5000) -> list:
        """Read from streams."""
        if not self._redis:
            await self.connect()
        return await self._redis.xread(streams, count=count, block=block)
    
    async def xlen(self, stream: str) -> int:
        """Get stream length."""
        if not self._redis:
            await self.connect()
        return await self._redis.xlen(stream)


# Global Redis manager instance
redis_manager = RedisManager()


@asynccontextmanager
async def get_redis():
    """Context manager for Redis operations."""
    await redis_manager.connect()
    try:
        yield redis_manager
    finally:
        await redis_manager.disconnect()


def get_sync_redis():
    """Get synchronous Redis client for non-async operations."""
    return redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
        protocol=2,  # Force RESP2 to avoid HELLO command issues
    )