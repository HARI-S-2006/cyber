"""Kafka client utilities for the Cyber Threat Visualizer.
Supports both Kafka and Redis as message brokers for high availability."""
import asyncio
import json
import logging
import os
from typing import Any, Callable, Optional, Dict, List
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

try:
    from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
    from aiokafka.admin import AIOKafkaAdminClient, NewTopic
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    logging.warning("aiokafka not available. Kafka support disabled.")

import redis.asyncio as redis
from redis.asyncio import Redis

from backend.config import settings

logger = logging.getLogger(__name__)


class MessageBrokerType(Enum):
    KAFKA = "kafka"
    REDIS = "redis"


@dataclass
class BrokerConfig:
    """Configuration for message broker."""
    broker_type: MessageBrokerType = MessageBrokerType.KAFKA
    # Kafka settings
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_consumer_group: str = "threat-visualizer"
    kafka_topics: Dict[str, str] = None
    # Redis settings
    redis_url: str = "redis://localhost:6379"
    redis_channels: Dict[str, str] = None
    
    def __post_init__(self):
        if self.kafka_topics is None:
            self.kafka_topics = {
                "raw": "network.raw",
                "features": "network.features",
                "threats": "network.threats",
                "stats": "network.stats",
            }
        if self.redis_channels is None:
            self.redis_channels = {
                "raw": "network:raw",
                "features": "network:features",
                "threats": "network:threats",
                "stats": "network:stats",
            }


class KafkaManager:
    """Manages Kafka producer/consumer operations."""
    
    def __init__(self, config: BrokerConfig):
        self.config = config
        self._producer: Optional[AIOKafkaProducer] = None
        self._consumers: Dict[str, AIOKafkaConsumer] = {}
        self._admin_client: Optional[AIOKafkaAdminClient] = None
        self._running = False
        self._handlers: Dict[str, List[Callable]] = {}
        self._consume_tasks: Dict[str, asyncio.Task] = {}
    
    async def connect(self) -> bool:
        """Initialize Kafka connections."""
        if not KAFKA_AVAILABLE:
            logger.warning("aiokafka not available, Kafka support disabled")
            return False
        
        try:
            # Create producer
            self._producer = AIOKafkaProducer(
                bootstrap_servers=self.config.kafka_bootstrap_servers,
                value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                compression_type="gzip",
                max_batch_size=16384,
                linger_ms=10,
            )
            await self._producer.start()
            
            # Create admin client for topic management
            self._admin_client = AIOKafkaAdminClient(
                bootstrap_servers=self.config.kafka_bootstrap_servers
            )
            await self._admin_client.start()
            
            # Create topics if they don't exist
            await self._ensure_topics()
            
            logger.info(f"Connected to Kafka at {self.config.kafka_bootstrap_servers}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            return False
    
    async def _ensure_topics(self):
        """Create Kafka topics if they don't exist."""
        if not self._admin_client:
            return
            
        existing_topics = await self._admin_client.list_topics()
        topics_to_create = []
        
        for topic_name in self.config.kafka_topics.values():
            if topic_name not in existing_topics:
                topics_to_create.append(NewTopic(
                    name=topic_name,
                    num_partitions=6,
                    replication_factor=1
                ))
        
        if topics_to_create:
            try:
                await self._admin_client.create_topics(topics_to_create)
                logger.info(f"Created Kafka topics: {[t.name for t in topics_to_create]}")
            except Exception as e:
                logger.warning(f"Some topics may already exist: {e}")
    
    async def disconnect(self):
        """Close Kafka connections."""
        self._running = False
        
        for task in self._consume_tasks.values():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        for consumer in self._consumers.values():
            await consumer.stop()
        
        if self._producer:
            await self._producer.stop()
        
        if self._admin_client:
            await self._admin_client.close()
        
        logger.info("Disconnected from Kafka")
    
    def register_handler(self, topic: str, callback: Callable[[dict], None]):
        """Register a message handler for a topic."""
        if topic not in self._handlers:
            self._handlers[topic] = []
        self._handlers[topic].append(callback)
    
    async def publish(self, topic: str, message: dict, key: Optional[str] = None) -> bool:
        """Publish a message to a Kafka topic."""
        if not self._producer:
            logger.warning("Kafka producer not initialized")
            return False
        
        try:
            message["_timestamp"] = datetime.utcnow().isoformat()
            await self._producer.send_and_wait(
                topic=topic,
                value=message,
                key=key.encode('utf-8') if key else None
            )
            return True
        except Exception as e:
            logger.error(f"Failed to publish to {topic}: {e}")
            return False
    
    async def publish_batch(self, topic: str, messages: List[dict], key: Optional[str] = None) -> bool:
        """Publish multiple messages to a Kafka topic."""
        if not self._producer or not messages:
            return False
        
        try:
            for msg in messages:
                msg["_timestamp"] = datetime.utcnow().isoformat()
                await self._producer.send(
                    topic=topic,
                    value=msg,
                    key=key.encode('utf-8') if key else None
                )
            await self._producer.flush()
            return True
        except Exception as e:
            logger.error(f"Failed to publish batch to {topic}: {e}")
            return False
    
    async def start_consuming(self, topics: List[str]):
        """Start consuming from Kafka topics."""
        self._running = True
        
        for topic in topics:
            if topic in self._consumers:
                continue
            
            consumer = AIOKafkaConsumer(
                topic,
                bootstrap_servers=self.config.kafka_bootstrap_servers,
                group_id=self.config.kafka_consumer_group,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                key_deserializer=lambda k: k.decode('utf-8') if k else None,
                auto_offset_reset='latest',
                enable_auto_commit=True,
                auto_commit_interval_ms=5000,
            )
            
            self._consumers[topic] = consumer
            await consumer.start()
            
            task = asyncio.create_task(self._consume_loop(topic))
            self._consume_tasks[topic] = task
            
            logger.info(f"Started consuming from Kafka topic: {topic}")
    
    async def _consume_loop(self, topic: str):
        """Consume messages from a Kafka topic."""
        consumer = self._consumers.get(topic)
        if not consumer:
            return
        
        try:
            async for message in consumer:
                if not self._running:
                    break
                
                try:
                    data = message.value
                    for callback in self._handlers.get(topic, []):
                        try:
                            if asyncio.iscoroutinefunction(callback):
                                await callback(data)
                            else:
                                callback(data)
                        except Exception as e:
                            logger.error(f"Error in handler for {topic}: {e}")
                except Exception as e:
                    logger.error(f"Error processing message from {topic}: {e}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Consumer error for {topic}: {e}")
    
    # Topic management
    async def create_topic(self, topic: str, partitions: int = 6, replication_factor: int = 1):
        """Create a Kafka topic."""
        if not self._admin_client:
            return False
        
        try:
            new_topic = NewTopic(
                name=topic,
                num_partitions=partitions,
                replication_factor=replication_factor
            )
            await self._admin_client.create_topics([new_topic])
            logger.info(f"Created topic: {topic}")
            return True
        except Exception as e:
            logger.warning(f"Topic may already exist: {e}")
            return False


class UnifiedMessageBroker:
    """Unified message broker supporting both Kafka and Redis with automatic failover."""
    
    def __init__(self, config: BrokerConfig):
        self.config = config
        self.kafka_manager: Optional[KafkaManager] = None
        self.redis: Optional[Redis] = None
        self._current_broker = config.broker_type
        self._running = False
        self._handlers: Dict[str, List[Callable]] = {}
        self._running = False
    
    async def connect(self) -> bool:
        """Connect to the primary broker with fallback."""
        # Try Kafka first (primary)
        if self.config.broker_type == MessageBrokerType.KAFKA and KAFKA_AVAILABLE:
            self.kafka_manager = KafkaManager(self.config)
            if await self.kafka_manager.connect():
                self._current_broker = MessageBrokerType.KAFKA
                logger.info("Using Kafka as primary message broker")
                return True
        
        # Fallback to Redis
        logger.info("Falling back to Redis message broker")
        self._current_broker = MessageBrokerType.REDIS
        return await self._connect_redis()
    
    async def _connect_redis(self) -> bool:
        """Connect to Redis as fallback."""
        try:
            import redis.asyncio as redis
            self.redis = redis.from_url(
                self.config.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20,
            )
            await self.redis.ping()
            logger.info(f"Connected to Redis at {self.config.redis_url}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from all brokers."""
        if self.kafka_manager:
            await self.kafka_manager.disconnect()
        
        if self.redis:
            await self.redis.close()
        
        logger.info("Disconnected from all message brokers")
    
    def register_handler(self, channel: str, callback: Callable[[dict], None]):
        """Register a message handler for a channel/topic."""
        if channel not in self._handlers:
            self._handlers[channel] = []
        self._handlers[channel].append(callback)
    
    async def publish(self, channel: str, message: dict, key: Optional[str] = None) -> bool:
        """Publish a message to the current broker."""
        message["_timestamp"] = datetime.utcnow().isoformat()
        message["_broker"] = self._current_broker.value
        
        if self._current_broker == MessageBrokerType.KAFKA and self.kafka_manager:
            return await self.kafka_manager.publish(channel, message)
        elif self._current_broker == MessageBrokerType.REDIS:
            return await self._publish_redis(channel, message)
        return False
    
    async def _publish_redis(self, channel: str, message: dict) -> bool:
        """Publish to Redis channel."""
        if not self.redis:
            return False
        try:
            payload = json.dumps(message, default=str)
            await self.redis.publish(channel, payload)
            return True
        except Exception as e:
            logger.error(f"Redis publish error: {e}")
            return False
    
    async def publish_batch(self, channel: str, messages: List[dict]) -> bool:
        """Publish multiple messages."""
        if not messages:
            return False
        
        if self._current_broker == MessageBrokerType.KAFKA and self.kafka_manager:
            return await self.kafka_manager.publish_batch(channel, messages)
        elif self._current_broker == MessageBrokerType.REDIS:
            # Redis doesn't have native batch, send sequentially
            for msg in messages:
                await self._publish_redis(channel, msg)
            return True
        return False
    
    async def start_consuming(self, channels: List[str]):
        """Start consuming from channels/topics."""
        if self._current_broker == MessageBrokerType.KAFKA and self.kafka_manager:
            await self.kafka_manager.start_consuming(channels)
        elif self._current_broker == MessageBrokerType.REDIS:
            await self._start_redis_consuming(channels)
    
    async def _start_redis_consuming(self, channels: List[str]):
        """Start consuming from Redis pub/sub."""
        if not self.redis:
            return
        
        self._running = True
        pubsub = self.redis.pubsub()
        
        for channel in channels:
            await pubsub.subscribe(channel)
        
        async def listen():
            async for message in pubsub.listen():
                if not self._running:
                    break
                if message["type"] == "message":
                    channel = message["channel"]
                    try:
                        data = json.loads(message["data"])
                        for callback in self._handlers.get(channel, []):
                            try:
                                if asyncio.iscoroutinefunction(callback):
                                    await callback(data)
                                else:
                                    callback(data)
                            except Exception as e:
                                logger.error(f"Handler error for {channel}: {e}")
                    except json.JSONDecodeError:
                        pass
        
        asyncio.create_task(listen())
        logger.info(f"Started Redis consumer for channels: {channels}")
    
    async def disconnect(self):
        """Disconnect from all brokers."""
        self._running = False
        
        if self.kafka_manager:
            await self.kafka_manager.disconnect()
        
        if self.redis:
            await self.redis.close()


# Global message broker instance
_broker_config = BrokerConfig()
message_broker = UnifiedMessageBroker(_broker_config)


@asynccontextmanager
async def get_message_broker():
    """Context manager for message broker operations."""
    await message_broker.connect()
    try:
        yield message_broker
    finally:
        await message_broker.disconnect()


def get_broker_config() -> BrokerConfig:
    """Get broker configuration from settings."""
    return BrokerConfig(
        broker_type=MessageBrokerType.KAFKA if KAFKA_AVAILABLE else MessageBrokerType.REDIS,
        kafka_bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
        kafka_consumer_group=os.getenv("KAFKA_CONSUMER_GROUP", "threat-visualizer"),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
    )


# Backward compatibility - Redis manager (deprecated, use message_broker instead)
redis_manager = None  # Deprecated - use message_broker instead


async def get_redis():
    """Deprecated - use get_message_broker instead."""
    import warnings
    warnings.warn("get_redis is deprecated, use get_message_broker instead", DeprecationWarning)
    return None