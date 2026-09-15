"""Feature extraction from raw network packets."""
import time
import statistics
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Optional
from collections import Counter

from scapy.layers.inet import IP, TCP, UDP, ICMP
from scapy.layers.l2 import Ether
from scapy.packet import Packet

from backend.config import settings
from backend.sniffer.geoip_cache import get_location, GeoLocation


@dataclass
class FlowKey:
    """Unique identifier for a network flow."""
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: str
    
    def __hash__(self):
        return hash((self.src_ip, self.dst_ip, self.src_port, self.dst_port, self.protocol))
    
    def __eq__(self, other):
        if not isinstance(other, FlowKey):
            return False
        return (self.src_ip == other.src_ip and 
                self.dst_ip == other.dst_ip and
                self.src_port == other.src_port and
                self.dst_port == other.dst_port and
                self.protocol == other.protocol)
    
    def reverse(self) -> 'FlowKey':
        """Return the reverse flow key."""
        return FlowKey(
            src_ip=self.dst_ip,
            dst_ip=self.src_ip,
            src_port=self.dst_port,
            dst_port=self.src_port,
            protocol=self.protocol
        )


@dataclass
class PacketInfo:
    """Information extracted from a single packet."""
    timestamp: float
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: str
    length: int
    tcp_flags: str = ""
    ttl: int = 0


@dataclass
class FlowFeatures:
    """Aggregated features for a network flow."""
    # Flow identification
    flow_key: FlowKey
    start_time: float
    last_time: float
    
    # Packet counts
    packet_count: int = 0
    byte_count: int = 0
    fwd_packets: int = 0
    fwd_bytes: int = 0
    bwd_packets: int = 0
    bwd_bytes: int = 0
    
    # Timing
    inter_arrival_times: list[float] = field(default_factory=list)
    last_packet_time: float = 0
    
    # Packet sizes
    packet_sizes: list[int] = field(default_factory=list)
    fwd_packet_sizes: list[int] = field(default_factory=list)
    bwd_packet_sizes: list[int] = field(default_factory=list)
    
    # TCP flags
    tcp_flags: Counter = field(default_factory=Counter)
    
    # Protocol
    protocols: Counter = field(default_factory=Counter)
    
    # Direction (for determining forward/backward)
    first_packet_direction: Optional[str] = None
    
    # GeoIP
    src_geo: Optional[object] = None
    dst_geo: Optional[object] = None
    
    def add_packet(self, pkt_info: PacketInfo, is_forward: bool) -> None:
        """Add a packet to this flow."""
        now = pkt_info.timestamp
        
        # Timing
        if self.last_packet_time > 0:
            self.inter_arrival_times.append(now - self.last_packet_time)
        self.last_packet_time = now
        
        # Counts
        self.packet_count += 1
        self.byte_count += pkt_info.length
        self.packet_sizes.append(pkt_info.length)
        self.protocols[pkt_info.protocol] += 1
        
        if is_forward:
            self.fwd_packets += 1
            self.fwd_bytes += pkt_info.length
            self.fwd_packet_sizes.append(pkt_info.length)
        else:
            self.bwd_packets += 1
            self.bwd_bytes += pkt_info.length
            self.bwd_packet_sizes.append(pkt_info.length)
        
        # TCP flags
        if pkt_info.tcp_flags:
            self.tcp_flags[pkt_info.tcp_flags] += 1
        
        self.last_time = now
    
    def compute_features(self) -> dict:
        """Compute ML-ready features from aggregated data."""
        duration = self.last_time - self.start_time if self.last_time > self.start_time else 0.001
        
        # Basic rates
        packet_rate = self.packet_count / duration
        byte_rate = self.byte_count / duration
        
        # Packet size stats
        if self.packet_sizes:
            avg_pkt_size = statistics.mean(self.packet_sizes)
            std_pkt_size = statistics.stdev(self.packet_sizes) if len(self.packet_sizes) > 1 else 0
            min_pkt_size = min(self.packet_sizes)
            max_pkt_size = max(self.packet_sizes)
        else:
            avg_pkt_size = std_pkt_size = min_pkt_size = max_pkt_size = 0
        
        # Inter-arrival stats
        if self.inter_arrival_times:
            avg_iat = statistics.mean(self.inter_arrival_times)
            std_iat = statistics.stdev(self.inter_arrival_times) if len(self.inter_arrival_times) > 1 else 0
            min_iat = min(self.inter_arrival_times)
            max_iat = max(self.inter_arrival_times)
        else:
            avg_iat = std_iat = min_iat = max_iat = 0
        
        # TCP flag ratios
        total_tcp = sum(self.tcp_flags.values())
        if total_tcp > 0:
            syn_ratio = self.tcp_flags.get('S', 0) / total_tcp
            ack_ratio = self.tcp_flags.get('A', 0) / total_tcp
            fin_ratio = self.tcp_flags.get('F', 0) / total_tcp
            rst_ratio = self.tcp_flags.get('R', 0) / total_tcp
            psh_ratio = self.tcp_flags.get('P', 0) / total_tcp
            urg_ratio = self.tcp_flags.get('U', 0) / total_tcp
        else:
            syn_ratio = ack_ratio = fin_ratio = rst_ratio = psh_ratio = urg_ratio = 0
        
        # Direction ratios
        fwd_pkt_ratio = self.fwd_packets / self.packet_count if self.packet_count > 0 else 0
        fwd_byte_ratio = self.fwd_bytes / self.byte_count if self.byte_count > 0 else 0
        
        # Forward/backward packet size stats
        if self.fwd_packet_sizes:
            fwd_avg_size = statistics.mean(self.fwd_packet_sizes)
            fwd_std_size = statistics.stdev(self.fwd_packet_sizes) if len(self.fwd_packet_sizes) > 1 else 0
        else:
            fwd_avg_size = fwd_std_size = 0
            
        if self.bwd_packet_sizes:
            bwd_avg_size = statistics.mean(self.bwd_packet_sizes)
            bwd_std_size = statistics.stdev(self.bwd_packet_sizes) if len(self.bwd_packet_sizes) > 1 else 0
        else:
            bwd_avg_size = bwd_std_size = 0
        
        # Unique destination ports (for port scan detection)
        # This would need port tracking - simplified here
        
        return {
            # Flow identification
            "src_ip": self.flow_key.src_ip,
            "dst_ip": self.flow_key.dst_ip,
            "src_port": self.flow_key.src_port,
            "dst_port": self.flow_key.dst_port,
            "protocol": self.flow_key.protocol,
            
            # Time
            "start_time": self.start_time,
            "last_time": self.last_time,
            "duration": duration,
            
            # Volume
            "packet_count": self.packet_count,
            "byte_count": self.byte_count,
            "fwd_packets": self.fwd_packets,
            "fwd_bytes": self.fwd_bytes,
            "bwd_packets": self.bwd_packets,
            "bwd_bytes": self.bwd_bytes,
            
            # Rates
            "packet_rate": packet_rate,
            "byte_rate": byte_rate,
            
            # Packet sizes
            "avg_packet_size": avg_pkt_size,
            "std_packet_size": std_pkt_size,
            "min_packet_size": min_pkt_size,
            "max_packet_size": max_pkt_size,
            
            # Inter-arrival times
            "avg_iat": avg_iat,
            "std_iat": std_iat,
            "min_iat": min_iat,
            "max_iat": max_iat,
            
            # Direction
            "fwd_packet_ratio": fwd_pkt_ratio,
            "fwd_byte_ratio": fwd_byte_ratio,
            "fwd_avg_size": fwd_avg_size,
            "fwd_std_size": fwd_std_size,
            "bwd_avg_size": bwd_avg_size,
            "bwd_std_size": bwd_std_size,
            
            # TCP flags
            "syn_ratio": syn_ratio,
            "ack_ratio": ack_ratio,
            "fin_ratio": fin_ratio,
            "rst_ratio": rst_ratio,
            "psh_ratio": psh_ratio,
            "urg_ratio": urg_ratio,
            
            # Protocol distribution
            "protocol_distribution": dict(self.protocols),
            "tcp_flag_distribution": dict(self.tcp_flags),
            
            # GeoIP (will be filled in later)
            "src_lat": getattr(self.src_geo, 'latitude', 0.0) if self.src_geo else 0.0,
            "src_lon": getattr(self.src_geo, 'longitude', 0.0) if self.src_geo else 0.0,
            "dst_lat": getattr(self.dst_geo, 'latitude', 0.0) if self.dst_geo else 0.0,
            "dst_lon": getattr(self.dst_geo, 'longitude', 0.0) if self.dst_geo else 0.0,
            "src_country": getattr(self.src_geo, 'country', 'Unknown') if self.src_geo else 'Unknown',
            "dst_country": getattr(self.dst_geo, 'country', 'Unknown') if self.dst_geo else 'Unknown',
        }


class FlowTracker:
    """Tracks network flows and extracts features."""
    
    def __init__(self, window_seconds: int = 60, max_flows: int = 10000):
        self.window_seconds = window_seconds
        self.max_flows = max_flows
        self.flows: dict[FlowKey, FlowFeatures] = {}
        self.flow_timestamps: dict[FlowKey, float] = {}
    
    def process_packet(self, pkt: Packet) -> Optional[FlowFeatures]:
        """Process a raw packet and update flow tracking."""
        try:
            # Extract basic packet info
            if IP not in pkt:
                return None
            
            ip_layer = pkt[IP]
            src_ip = ip_layer.src
            dst_ip = ip_layer.dst
            protocol_num = ip_layer.proto
            ttl = ip_layer.ttl
            length = len(pkt)
            
            # Determine protocol and ports
            protocol = "UNKNOWN"
            src_port = 0
            dst_port = 0
            tcp_flags = ""
            
            if TCP in pkt:
                protocol = "TCP"
                tcp_layer = pkt[TCP]
                src_port = tcp_layer.sport
                dst_port = tcp_layer.dport
                tcp_flags = self._get_tcp_flags(tcp_layer.flags)
            elif UDP in pkt:
                protocol = "UDP"
                udp_layer = pkt[UDP]
                src_port = udp_layer.sport
                dst_port = udp_layer.dport
            elif ICMP in pkt:
                protocol = "ICMP"
                src_port = 0
                dst_port = 0
            else:
                protocol = f"PROTO_{protocol_num}"
                src_port = 0
                dst_port = 0
            
            # Create packet info
            pkt_info = PacketInfo(
                timestamp=time.time(),
                src_ip=src_ip,
                dst_ip=dst_ip,
                src_port=src_port,
                dst_port=dst_port,
                protocol=protocol,
                length=length,
                tcp_flags=tcp_flags,
                ttl=ttl
            )
            
            # Create flow key
            flow_key = FlowKey(src_ip, dst_ip, src_port, dst_port, protocol)
            rev_key = flow_key.reverse()
            
            # Determine direction
            is_forward = True
            if flow_key in self.flows:
                is_forward = True
            elif rev_key in self.flows:
                flow_key = rev_key
                is_forward = False
            else:
                # New flow
                if len(self.flows) >= settings.sniffer_packet_buffer_size:
                    self._evict_oldest()
                
                flow = FlowFeatures(
                    flow_key=flow_key,
                    start_time=time.time(),
                    last_time=time.time(),
                    first_packet_direction="forward"
                )
                self.flows[flow_key] = flow
                self.flow_timestamps[flow_key] = time.time()
                return flow
            
            # Update existing flow
            flow = self.flows[flow_key]
            flow.add_packet(pkt_info, is_forward)
            self.flow_timestamps[flow_key] = time.time()
            
            # Clean up expired flows
            self._cleanup_expired()
            
            return flow
            
        except Exception as e:
            # Silently ignore parsing errors
            return None
    
    @staticmethod
    def _get_tcp_flags(flags) -> str:
        """Convert TCP flags to string representation."""
        flag_str = ""
        if flags & 0x02:  # SYN
            flag_str += "S"
        if flags & 0x10:  # ACK
            flag_str += "A"
        if flags & 0x01:  # FIN
            flag_str += "F"
        if flags & 0x04:  # RST
            flag_str += "R"
        if flags & 0x08:  # PSH
            flag_str += "P"
        if flags & 0x20:  # URG
            flag_str += "U"
        if flags & 0x40:  # ECE
            flag_str += "E"
        if flags & 0x80:  # CWR
            flag_str += "C"
        return flag_str
    
    def _evict_oldest(self) -> None:
        """Remove the oldest flow."""
        if self.flow_timestamps:
            oldest_key = min(self.flow_timestamps, key=self.flow_timestamps.get)
            self.flows.pop(oldest_key, None)
            self.flow_timestamps.pop(oldest_key, None)
    
    def _cleanup_expired(self) -> None:
        """Remove flows older than the window."""
        now = time.time()
        expired = [
            key for key, ts in self.flow_timestamps.items()
            if now - ts > self.window_seconds
        ]
        for key in expired:
            self.flows.pop(key, None)
            self.flow_timestamps.pop(key, None)
    
    def get_all_features(self) -> list[dict]:
        """Get computed features for all active flows."""
        features = []
        for flow in self.flows.values():
            if flow.packet_count >= settings.feature_min_packets:
                features.append(flow.compute_features())
        return features
    
    def get_flow_count(self) -> int:
        """Get current number of tracked flows."""
        return len(self.flows)


class PacketProcessor:
    """High-level packet processing pipeline."""
    
    def __init__(self):
        self.flow_tracker = FlowTracker(
            window_seconds=settings.feature_window_seconds,
            max_flows=settings.sniffer_packet_buffer_size
        )
        self.packet_count = 0
        self.feature_count = 0
    
    async def process_packet(self, pkt: Packet) -> Optional[dict]:
        """Process a single packet through the pipeline."""
        self.packet_count += 1
        
        # Extract flow features
        flow = self.flow_tracker.process_packet(pkt)
        if not flow:
            return None
        
        # Compute features if enough packets
        if flow.packet_count >= settings.feature_min_packets:
            self.feature_count += 1
            features = flow.compute_features()
            
            # Enrich with GeoIP
            src_geo = await get_location(flow.flow_key.src_ip)
            dst_geo = await get_location(flow.flow_key.dst_ip)
            
            if src_geo:
                features["src_lat"] = src_geo.latitude
                features["src_lon"] = src_geo.longitude
                features["src_country"] = src_geo.country
                features["src_city"] = src_geo.city
            
            if dst_geo:
                features["dst_lat"] = dst_geo.latitude
                features["dst_lon"] = dst_geo.longitude
                features["dst_country"] = dst_geo.country
                features["dst_city"] = dst_geo.city
            
            return features
        
        return None
    
    def get_stats(self) -> dict:
        """Get processing statistics."""
        return {
            "total_packets": self.packet_count,
            "total_features": self.feature_count,
            "active_flows": self.flow_tracker.get_flow_count()
        }