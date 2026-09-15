"""Raw packet sniffer using Scapy with async Redis publishing."""
import asyncio
import logging
import signal
import sys
import time
from typing import Optional

from scapy.all import sniff, AsyncSniffer, conf
from scapy.packet import Packet

from backend.config import settings
from backend.utils.redis_client import redis_manager
from backend.sniffer.feature_extractor import PacketProcessor, FlowTracker
from backend.sniffer.geoip_cache import get_batch_locations

logger = logging.getLogger(__name__)


class PacketSniffer:
    """High-performance async packet sniffer with feature extraction."""
    
    def __init__(self, interface: str = "", bpf_filter: str = "ip"):
        self.interface = interface or self._get_default_interface()
        self.bpf_filter = bpf_filter
        self.processor = PacketProcessor()
        self.running = False
        self.sniffer: Optional[AsyncSniffer] = None
        self._stats_task: Optional[asyncio.Task] = None
        self._publish_task: Optional[asyncio.Task] = None
        self._feature_buffer: list[dict] = []
        self._buffer_lock = asyncio.Lock()
        self._shutdown = False
        
        # Configure Scapy
        conf.verb = 0  # Suppress Scapy output
        if self.interface:
            conf.iface = self.interface
    
    @staticmethod
    def _get_default_interface() -> str:
        """Auto-detect the best network interface."""
        try:
            # Get interfaces with IP addresses
            interfaces = conf.ifaces
            for iface in interfaces.values():
                if iface.ip and iface.ip != "127.0.0.1" and not iface.name.startswith("lo"):
                    return iface.name
        except Exception:
            pass
        return ""
    
    async def start(self) -> None:
        """Start the packet sniffer."""
        if self.running:
            logger.warning("Sniffer already running")
            return
        
        # Connect to Redis
        await redis_manager.connect()
        
        self.running = True
        self._shutdown = False
        
        # Start background tasks
        self._stats_task = asyncio.create_task(self._stats_loop())
        self._publish_task = asyncio.create_task(self._publish_loop())
        
        # Start packet capture
        logger.info(f"Starting packet capture on interface: {self.interface or 'auto'}")
        logger.info(f"BPF filter: {self.bpf_filter}")
        
        self.sniffer = AsyncSniffer(
            iface=self.interface or None,
            filter=self.bpf_filter,
            prn=self._packet_callback,
            store=False,
            session=None
        )
        self.sniffer.start()
        
        logger.info("Packet sniffer started successfully")
    
    async def stop(self) -> None:
        """Stop the packet sniffer gracefully."""
        if not self.running:
            return
        
        logger.info("Stopping packet sniffer...")
        self.running = False
        self._shutdown = True
        
        # Stop sniffer
        if self.sniffer:
            self.sniffer.stop()
        
        # Cancel background tasks
        for task in [self._stats_task, self._publish_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Flush remaining features
        await self._flush_buffer()
        
        # Disconnect Redis
        await redis_manager.disconnect()
        
        logger.info("Packet sniffer stopped")
    
    def _packet_callback(self, pkt: Packet) -> None:
        """Callback for each captured packet (runs in Scapy thread)."""
        if not self.running:
            return
        
        # Schedule async processing
        asyncio.run_coroutine_threadsafe(
            self._process_packet_async(pkt),
            asyncio.get_event_loop()
        )
    
    async def _process_packet_async(self, pkt: Packet) -> None:
        """Process packet asynchronously."""
        try:
            features = await self.processor.process_packet(pkt)
            if features:
                async with self._buffer_lock:
                    self._feature_buffer.append(features)
                    
                    # Prevent buffer overflow
                    if len(self._feature_buffer) > 1000:
                        self._feature_buffer = self._feature_buffer[-500:]
        except Exception as e:
            logger.debug(f"Packet processing error: {e}")
    
    async def _flush_buffer(self) -> None:
        """Flush feature buffer to Redis."""
        async with self._buffer_lock:
            if not self._feature_buffer:
                return
            
            features = self._feature_buffer
            self._feature_buffer = []
            
            # Batch publish features
            for feat in features:
                try:
                    await redis_manager.publish_json(settings.channel_features, feat)
                except Exception as e:
                    logger.error(f"Failed to publish feature: {e}")
    
    async def _publish_loop(self) -> None:
        """Periodically flush feature buffer."""
        while self.running:
            try:
                await asyncio.sleep(1.0)  # Flush every second
                await self._flush_buffer()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Publish loop error: {e}")
    
    async def _stats_loop(self) -> None:
        """Periodically log statistics."""
        while self.running:
            try:
                await asyncio.sleep(10)  # Log every 10 seconds
                stats = self.processor.get_stats()
                flow_count = self.processor.flow_tracker.get_flow_count()
                
                logger.info(
                    f"Stats: Packets={stats['total_packets']}, "
                    f"Features={stats['total_features']}, "
                    f"Active Flows={flow_count}"
                )
                
                # Publish stats to Redis
                await redis_manager.publish_json(settings.channel_stats, {
                    "timestamp": time.time(),
                    "packets_per_sec": stats["total_packets"] / max(1, time.time() - getattr(self, '_start_time', time.time())),
                    "total_packets": stats["total_packets"],
                    "features_extracted": stats["total_features"],
                    "active_flows": flow_count
                })
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Stats loop error: {e}")


async def main():
    """Main entry point for the packet sniffer."""
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format=settings.log_format
    )
    
    # Create sniffer
    sniffer = PacketSniffer(
        interface=settings.sniffer_interface,
        bpf_filter=settings.sniffer_bpf_filter
    )
    
    # Handle signals
    loop = asyncio.get_event_loop()
    
    def signal_handler():
        logger.info("Shutdown signal received")
        asyncio.create_task(sniffer.stop())
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler
            pass
    
    try:
        await sniffer.start()
        
        # Keep running until shutdown
        while sniffer.running:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        await sniffer.stop()


if __name__ == "__main__":
    # Add start time for stats
    import time
    PacketSniffer._start_time = time.time()
    asyncio.run(main())