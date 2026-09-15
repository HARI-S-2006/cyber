#!/usr/bin/env python3
"""
Real-time Streaming Pipeline & API Layer
Supports Kafka (primary) and Redis (fallback) for high availability and performance.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable, AsyncGenerator
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager
from collections import defaultdict
import threading

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, BackgroundTasks
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import HTMLResponse
    from pydantic import BaseModel, Field
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    print("Warning: fastapi not available")

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

# Import unified message broker
from backend.utils.kafka_client import (
    message_broker, UnifiedMessageBroker, BrokerConfig, MessageBrokerType,
    get_broker_config, AnomalyDetectionService
)

# Import other components
from backend.ml.model import anomaly_detector, detection_service
from backend.sniffer.feature_extractor import FeatureExtractionEngine


@dataclass
class StreamConfig:
    # Message broker config
    broker_type: str = "kafka"  # "kafka" or "redis"
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_consumer_group: str = "threat-visualizer"
    redis_url: str = "redis://localhost:6379"
    
    # Kafka topics
    kafka_topic_raw: str = "network.raw"
    kafka_topic_features: str = "network.features"
    kafka_topic_threats: str = "network.threats"
    kafka_topic_stats: str = "network.stats"
    kafka_consumer_group: str = "threat-visualizer"
    
    # Redis channels (fallback)
    redis_url: str = "redis://localhost:6379"
    redis_channel_raw: str = "network:raw"
    redis_channel_features: str = "network:features"
    redis_channel_threats: str = "network:threats"
    redis_channel_stats: str = "network:stats"
    
    # Stream config
    max_stream_length: int = 100000
    consumer_group: str = "threat-visualizer"
    consumer_name: str = None
    block_ms: int = 1000
    count: int = 100


class UnifiedStreamManager:
    """Unified stream manager supporting both Kafka and Redis."""
    
    def __init__(self, config: StreamConfig):
        self.config = config
        self.broker_config = BrokerConfig(
            broker_type=MessageBrokerType.KAFKA if config.broker_type == "kafka" else MessageBrokerType.REDIS,
            kafka_bootstrap_servers=config.kafka_bootstrap_servers,
            kafka_consumer_group=config.kafka_consumer_group,
            kafka_topics={
                "raw": config.kafka_topic_raw,
                "features": config.kafka_topic_features,
                "threats": config.kafka_topic_threats,
                "stats": config.kafka_topic_stats,
            },
            redis_url=config.redis_url,
            redis_channels={
                "raw": config.redis_channel_raw,
                "features": config.redis_channel_features,
                "threats": config.redis_channel_threats,
                "stats": config.redis_channel_stats,
            }
        )
        self.broker: Optional[UnifiedMessageBroker] = None
        self.running = False
        self.handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._consume_tasks: List[asyncio.Task] = []
        self.feature_extractor: Optional[FeatureExtractionEngine] = None
        self.anomaly_detector: Optional[AnomalyDetectionService] = None
        self._running = False
    
    async def connect(self) -> None:
        """Initialize connections to message brokers and ML services."""
        # Initialize feature extractor
        self.feature_extractor = FeatureExtractionEngine(
            redis_url="redis://localhost:6379",
            export_interval=1.0
        )
        
        # Initialize anomaly detection service
        self.anomaly_detector = AnomalyDetectionService()
        await self.anomaly_detector.initialize()
        
        # Initialize message broker
        from backend.utils.kafka_client import UnifiedMessageBroker, BrokerConfig, MessageBrokerType
        broker_config = BrokerConfig(
            broker_type=MessageBrokerType.KAFKA if self.config.broker_type == "kafka" else MessageBrokerType.REDIS,
            kafka_bootstrap_servers=self.config.kafka_bootstrap_servers,
            kafka_consumer_group=self.config.kafka_consumer_group,
            kafka_topics={
                "raw": self.config.kafka_topic_raw,
                "features": self.config.kafka_topic_features,
                "threats": self.config.kafka_topic_threats,
                "stats": self.config.kafka_topic_stats,
            },
            redis_url="redis://localhost:6379",
            redis_channels={
                "raw": "network:raw",
                "features": "network:features",
                "threats": "network:threats",
                "stats": "network:stats",
            }
        )
        
        from backend.utils.kafka_client import UnifiedMessageBroker, BrokerConfig, MessageBrokerType
        self.broker = UnifiedMessageBroker(broker_config)
        
        # Connect to message broker
        await self.broker.connect()
        
        # Initialize feature extractor
        self.feature_extractor = FeatureExtractionEngine(
            redis_url="redis://localhost:6379",
            export_interval=1.0
        )
        
        # Set up callbacks
        def on_flow_exported(flow_dict):
            if self.anomaly_detector:
                self.anomaly_detector.detect(flow_dict)
        
        self.feature_extractor.set_export_callback(on_flow_exported)
        
        self.running = True
    
    async def disconnect(self):
        """Gracefully disconnect from all services."""
        self.running = False
        
        # Cancel consume tasks
        for task in self._consume_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Disconnect from message broker
        from backend.utils.kafka_client import message_broker
        await message_broker.disconnect()
    
    def register_handler(self, channel: str, handler: Callable[[Dict], Any]):
        """Register a handler for a specific channel/topic."""
        self.handlers[channel].append(handler)
    
    async def publish(self, channel: str, data: Dict, maxlen: Optional[int] = None):
        """Publish data to a channel/topic."""
        if not self.running:
            return
        
        # Add metadata
        data["_timestamp"] = time.time()
        data["_id"] = str(uuid.uuid4())[:8]
        
        # Determine channel/topic based on type
        if self.config.broker_type == "kafka":
            topic_map = {
                "packets:raw": self.config.kafka_topic_raw,
                "flows:features": self.config.kafka_topic_features,
                "anomalies:detected": self.config.kafka_topic_threats,
                "stats": self.config.kafka_topic_stats,
            }
            topic = topic_map.get(channel, channel)
            await self.broker.publish(topic, data)
        else:
            # Redis fallback
            channel_map = {
                "packets:raw": "network:raw",
                "flows:features": "network:features",
                "anomalies:detected": "network:threats",
                "stats": "network:stats",
            }
            channel = channel_map.get(channel, channel)
            await self._publish_redis(channel, data)
    
    async def _publish_redis(self, channel: str, data: Dict, maxlen: Optional[int] = None):
        """Publish to Redis channel (fallback)."""
        # Implementation would use Redis pub/sub
        pass
    
    async def start_consuming(self, channels: List[str]):
        """Start consuming from channels/topics."""
        self.running = True
        
        for channel in channels:
            task = asyncio.create_task(self._consume_channel(channel))
            self._consume_tasks.append(task)
    
    async def _consume_channel(self, channel: str):
        """Consume messages from a channel/topic."""
        if self.config.broker_type == "kafka":
            await self._consume_kafka(channel)
        else:
            await self._consume_redis(channel)
    
    async def _consume_kafka(self, channel: str):
        """Consume from Kafka topic."""
        topic_map = {
            "packets:raw": "network.raw",
            "flows:features": "network.features",
            "anomalies:detected": "network.threats",
            "stats": "network.stats",
        }
        topic = self._get_kafka_topic(channel)
        if not topic:
            return
        
        from backend.utils.kafka_client import message_broker
        await self.broker.start_consuming([topic])
        
        # Register handlers
        if channel in self.handlers:
            for handler in self.handlers[channel]:
                self.broker.kafka_manager.register_handler(topic, handler)
    
    def _get_kafka_topic(self, channel: str) -> Optional[str]:
        """Map internal channel to Kafka topic."""
        topic_map = {
            "packets:raw": "network.raw",
            "flows:features": "network.features",
            "anomalies:detected": "network.threats",
            "stats": "network.stats",
        }
        return topic_map.get(channel)
    
    async def _consume_redis(self, channel: str):
        """Consume from Redis channel (fallback)."""
        # Redis fallback implementation would go here
        pass
    
    async def get_recent(self, channel: str, count: int = 100) -> List[Dict]:
        """Get recent messages from a channel/stream."""
        # Implementation would query Kafka or Redis
        return []
    
    async def get_stream_info(self, channel: str) -> Dict:
        """Get stream/channel information."""
        return {"length": 0, "mode": "kafka" if self.config.broker_type == "kafka" else "redis_fallback"}


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.subscriptions: Dict[str, set] = defaultdict(set)
        self.lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        async with self.lock:
            self.active_connections[client_id] = websocket

    async def disconnect(self, client_id: str):
        async with self.lock:
            self.active_connections.pop(client_id, None)
            for topic in self.subscriptions:
                self.subscriptions[topic].discard(client_id)

    async def subscribe(self, client_id: str, topic: str):
        async with self.lock:
            self.subscriptions[topic].add(client_id)

    async def unsubscribe(self, client_id: str, topic: str):
        async with self.lock:
            self.subscriptions[topic].discard(client_id)

    async def broadcast(self, topic: str, message: Dict):
        async with self.lock:
            clients = self.subscriptions.get(topic, set()).copy()
        
        for client_id in clients:
            ws = self.active_connections.get(client_id)
            if ws:
                try:
                    await ws.send_json(message)
                except Exception:
                    await self.disconnect(client_id)

    async def send_personal(self, client_id: str, message: Dict):
        ws = self.active_connections.get(client_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception:
                await self.disconnect(client_id)


class ThreatAggregator:
    def __init__(self, window_seconds: int = 60):
        self.window_seconds = window_seconds
        self.flow_buffer: Dict[str, List[Dict]] = defaultdict(list)
        self.anomaly_buffer: List[Dict] = []
        self.stats = {
            "total_flows": 0,
            "total_anomalies": 0,
            "anomalies_by_type": defaultdict(int),
            "top_talkers": defaultdict(int),
            "protocol_dist": defaultdict(int),
            "geo_dist": defaultdict(int)
        }
        self.lock = threading.Lock()
        self.last_cleanup = time.time()

    def add_flow(self, flow: Dict):
        flow_id = flow.get("flow_id", "")
        with self.lock:
            self.flow_buffer[flow_id].append(flow)
            self.stats["total_flows"] += 1
            self.stats["top_talkers"][flow.get("src_ip", "")] += flow.get("bytes_fwd", 0) + flow.get("bytes_bwd", 0)
            self.stats["protocol_dist"][flow.get("protocol", "UNKNOWN")] += 1
            self._maybe_cleanup()

    def add_anomaly(self, anomaly: Dict):
        with self.lock:
            self.anomaly_buffer.append(anomaly)
            self.stats["total_anomalies"] += 1
            threat_level = anomaly.get("threat_level", "UNKNOWN")
            self.stats["anomalies_by_type"][threat_level] += 1
            self._maybe_cleanup()

    def _maybe_cleanup(self):
        now = time.time()
        if now - self.last_cleanup > self.window_seconds:
            cutoff = now - self.window_seconds
            for flow_id, flows in list(self.flow_buffer.items()):
                self.flow_buffer[flow_id] = [f for f in flows if f.get("last_time", 0) > cutoff]
                if not self.flow_buffer[flow_id]:
                    del self.flow_buffer[flow_id]
            
            self.anomaly_buffer = [a for a in self.anomaly_buffer if a.get("timestamp", 0) > cutoff]
            self.last_cleanup = now

    def get_dashboard_stats(self) -> Dict:
        with self.lock:
            recent_anomalies = [a for a in self.anomaly_buffer if a.get("timestamp", 0) > time.time() - 300]
            top_talkers = sorted(self.stats["top_talkers"].items(), key=lambda x: x[1], reverse=True)[:10]
            
            return {
                "timestamp": time.time(),
                "active_flows": len(self.flow_buffer),
                "flows_last_minute": self.stats["total_flows"],
                "anomalies_last_5min": len(recent_anomalies),
                "anomalies_by_level": dict(self.stats["anomalies_by_type"]),
                "top_talkers": [{"ip": ip, "bytes": bytes_} for ip, bytes_ in top_talkers],
                "protocol_distribution": dict(self.stats["protocol_dist"]),
                "anomaly_rate": len(recent_anomalies) / 5.0
            }

    def get_recent_anomalies(self, limit: int = 50) -> List[Dict]:
        with self.lock:
            return sorted(self.anomaly_buffer, key=lambda x: x.get("timestamp", 0), reverse=True)[:limit]

    def get_globe_data(self) -> Dict:
        with self.lock:
            arcs = []
            for anomaly in self.anomaly_buffer[-500:]:
                arcs.append({
                    "src": anomaly.get("features", {}).get("src_ip", ""),
                    "dst": anomaly.get("features", {}).get("dst_ip", ""),
                    "score": anomaly.get("anomaly_score", 0),
                    "level": anomaly.get("threat_level", "INFO"),
                    "timestamp": anomaly.get("timestamp", 0)
                })
            return {"arcs": arcs, "timestamp": time.time()}


# Pydantic Models for API
class FlowSummary(BaseModel):
    flow_id: str
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: str
    packets_total: int
    bytes_total: int
    duration_ms: float
    threat_score: float
    labels: List[str] = []


class AnomalyEvent(BaseModel):
    flow_id: str
    timestamp: float
    is_anomaly: bool
    anomaly_score: float
    threat_level: str
    features: Dict[str, Any]


class DashboardStats(BaseModel):
    timestamp: float
    active_flows: int
    flows_last_minute: int
    anomalies_last_5min: int
    anomalies_by_level: Dict[str, int]
    top_talkers: List[Dict]
    protocol_distribution: Dict[str, int]
    anomaly_rate: float


class GlobeData(BaseModel):
    arcs: List[Dict]
    timestamp: float


# FastAPI Application
def create_app() -> FastAPI:
    stream_manager = UnifiedStreamManager(StreamConfig())
    aggregator = ThreatAggregator()
    manager = ConnectionManager()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        # Startup
        await stream_manager.connect()
        await stream_manager.start_consuming([
            "packets:raw", "flows:features", "anomalies:detected", "stats"
        ])
        
        async def flow_handler(data):
            aggregator.add_flow(data)
            await manager.broadcast("flows", {"type": "FLOW_UPDATE", "payload": data})
        
        async def anomaly_handler(data):
            aggregator.add_anomaly(data)
            await manager.broadcast("anomalies", {"type": "ANOMALY", "payload": data})
            if data.get("threat_level") in ("HIGH", "CRITICAL"):
                await manager.broadcast("alerts", {"type": "ALERT", "payload": data})
        
        # Register handlers
        stream_manager.register_handler("flows:features", flow_handler)
        stream_manager.register_handler("anomalies:detected", anomaly_handler)
        
        yield
        
        # Shutdown
        await stream_manager.disconnect()

    app = FastAPI(
        title="Cyber Threat Visualizer API",
        description="Real-time network threat detection and visualization API with Kafka/Redis support",
        version="2.0.0",
        lifespan=lifespan
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.websocket("/ws/{client_id}")
    async def websocket_endpoint(websocket: WebSocket, client_id: str):
        await manager.connect(websocket, client_id)
        try:
            await manager.subscribe(client_id, "flows")
            await manager.subscribe(client_id, "anomalies")
            await manager.subscribe(client_id, "alerts")
            
            while True:
                data = await websocket.receive_json()
                msg_type = data.get("type")
                
                if msg_type == "subscribe":
                    for topic in data.get("topics", []):
                        await manager.subscribe(client_id, topic)
                elif msg_type == "unsubscribe":
                    for topic in data.get("topics", []):
                        await manager.unsubscribe(client_id, topic)
                elif msg_type == "ping":
                    await manager.send_personal(client_id, {"type": "pong", "timestamp": time.time()})
                    
        except WebSocketDisconnect:
            await manager.disconnect(client_id)
        except Exception as e:
            print(f"WebSocket error: {e}")
        finally:
            await manager.disconnect(client_id)

    @app.get("/api/stats")
    async def get_stats():
        return aggregator.get_dashboard_stats()

    @app.get("/api/anomalies")
    async def get_anomalies(limit: int = 50):
        return aggregator.get_recent_anomalies(limit)

    @app.get("/api/globe")
    async def get_globe_data():
        return aggregator.get_globe_data()

    @app.get("/api/flows/recent")
    async def get_recent_flows(limit: int = 100):
        return await stream_manager.get_recent("flows:features", limit)

    @app.get("/api/health")
    async def health_check():
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "version": "2.0.0",
            "features": ["kafka", "redis", "ml", "websockets"]
        }

    @app.post("/api/alerts/acknowledge")
    async def acknowledge_alert(alert_id: str):
        return {"acknowledged": True, "alert_id": alert_id}

    return app


async def run_api_server(host: str = "0.0.0.0", port: int = 8000):
    config = StreamConfig()
    stream_manager = UnifiedStreamManager(config)
    aggregator = ThreatAggregator()
    app = create_app(stream_manager, aggregator)
    
    config_uvicorn = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config_uvicorn)
    await server.serve()


if __name__ == "__main__":
    if FASTAPI_AVAILABLE:
        asyncio.run(run_api_server())
    else:
        print("FastAPI not available. Install with: pip install fastapi uvicorn")