#!/usr/bin/env python3
"""
Live Feature Extraction Engine
Extracts flow-based and packet-level features from raw packets for anomaly detection.
"""

import time
import hashlib
import struct
import math
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import threading
import json

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


@dataclass
class FlowKey:
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: int

    def __hash__(self):
        return hash((self.src_ip, self.dst_ip, self.src_port, self.dst_port, self.protocol))

    def __eq__(self, other):
        if not isinstance(other, FlowKey):
            return False
        return (self.src_ip == other.src_ip and self.dst_ip == other.dst_ip and
                self.src_port == other.src_port and self.dst_port == other.dst_port and
                self.protocol == other.protocol)

    def reverse(self) -> 'FlowKey':
        return FlowKey(self.dst_ip, self.src_ip, self.dst_port, self.src_port, self.protocol)

    def to_string(self) -> str:
        return f"{self.src_ip}:{self.src_port}-{self.dst_ip}:{self.dst_port}-{self.protocol}"


@dataclass
class PacketInfo:
    timestamp: float
    length: int
    direction: int
    tcp_flags: int
    payload: bytes
    payload_entropy: float = 0.0


@dataclass
class FlowFeatures:
    flow_id: str
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: int
    start_time: float
    last_time: float
    duration_ms: float
    packets_fwd: int
    packets_bwd: int
    bytes_fwd: int
    bytes_bwd: int
    iat_fwd: List[float]
    iat_bwd: List[float]
    pkt_len_fwd: List[int]
    pkt_len_bwd: List[int]
    tcp_flags_fwd: Dict[str, int]
    tcp_flags_bwd: Dict[str, int]
    payload_entropy_fwd: List[float]
    payload_entropy_bwd: List[float]
    tls_sni: Optional[str] = None
    http_host: Optional[str] = None
    dns_queries: List[str] = field(default_factory=list)
    threat_score: float = 0.0
    labels: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "flow_id": self.flow_id,
            "src_ip": self.src_ip,
            "dst_ip": self.dst_ip,
            "src_port": self.src_port,
            "dst_port": self.dst_port,
            "protocol": self.protocol,
            "start_time": self.start_time,
            "last_time": self.last_time,
            "duration_ms": self.duration_ms,
            "packets_fwd": self.packets_fwd,
            "packets_bwd": self.packets_bwd,
            "bytes_fwd": self.bytes_fwd,
            "bytes_bwd": self.bytes_bwd,
            "iat_fwd_mean": np.mean(self.iat_fwd) if self.iat_fwd else 0,
            "iat_fwd_std": np.std(self.iat_fwd) if len(self.iat_fwd) > 1 else 0,
            "iat_bwd_mean": np.mean(self.iat_bwd) if self.iat_bwd else 0,
            "iat_bwd_std": np.std(self.iat_bwd) if len(self.iat_bwd) > 1 else 0,
            "pkt_len_fwd_mean": np.mean(self.pkt_len_fwd) if self.pkt_len_fwd else 0,
            "pkt_len_fwd_std": np.std(self.pkt_len_fwd) if len(self.pkt_len_fwd) > 1 else 0,
            "pkt_len_bwd_mean": np.mean(self.pkt_len_bwd) if self.pkt_len_bwd else 0,
            "pkt_len_bwd_std": np.std(self.pkt_len_bwd) if len(self.pkt_len_bwd) > 1 else 0,
            "tcp_flags_fwd": self.tcp_flags_fwd,
            "tcp_flags_bwd": self.tcp_flags_bwd,
            "payload_entropy_fwd_mean": np.mean(self.payload_entropy_fwd) if self.payload_entropy_fwd else 0,
            "payload_entropy_bwd_mean": np.mean(self.payload_entropy_bwd) if self.payload_entropy_bwd else 0,
            "tls_sni": self.tls_sni,
            "http_host": self.http_host,
            "dns_queries": self.dns_queries,
            "threat_score": self.threat_score,
            "labels": self.labels
        }


class EntropyCalculator:
    @staticmethod
    def calculate(data: bytes) -> float:
        if not data:
            return 0.0
        freq = defaultdict(int)
        for byte in data:
            freq[byte] += 1
        entropy = 0.0
        length = len(data)
        for count in freq.values():
            p = count / length
            entropy -= p * math.log2(p)
        return entropy

    @staticmethod
    def calculate_streaming(prev_entropy: float, prev_len: int, new_data: bytes) -> float:
        if not new_data:
            return prev_entropy
        combined = prev_len + len(new_data)
        if combined == 0:
            return 0.0
        return (prev_entropy * prev_len + EntropyCalculator.calculate(new_data) * len(new_data)) / combined


class PayloadParser:
    @staticmethod
    def parse_tls_client_hello(payload: bytes) -> Optional[str]:
        if len(payload) < 5:
            return None
        if payload[0] != 0x16 or payload[1] != 0x03:
            return None
        try:
            pos = 5
            session_id_len = payload[pos]
            pos += 1 + session_id_len
            if pos + 2 > len(payload):
                return None
            cipher_suites_len = struct.unpack('>H', payload[pos:pos+2])[0]
            pos += 2 + cipher_suites_len
            if pos + 1 > len(payload):
                return None
            compression_methods_len = payload[pos]
            pos += 1 + compression_methods_len
            if pos + 2 > len(payload):
                return None
            extensions_len = struct.unpack('>H', payload[pos:pos+2])[0]
            pos += 2
            end = pos + extensions_len
            while pos + 4 <= end and pos < len(payload):
                ext_type = struct.unpack('>H', payload[pos:pos+2])[0]
                ext_len = struct.unpack('>H', payload[pos+2:pos+4])[0]
                pos += 4
                if ext_type == 0x0000 and pos + ext_len <= len(payload):
                    sni_data = payload[pos:pos+ext_len]
                    if len(sni_data) > 3:
                        list_len = struct.unpack('>H', sni_data[1:3])[0]
                        if 3 + list_len <= len(sni_data):
                            name_type = sni_data[3]
                            if name_type == 0:
                                name_len = struct.unpack('>H', sni_data[4:6])[0]
                                if 6 + name_len <= len(sni_data):
                                    return sni_data[6:6+name_len].decode('utf-8', errors='ignore')
                pos += ext_len
        except Exception:
            pass
        return None

    @staticmethod
    def parse_http_host(payload: bytes) -> Optional[str]:
        try:
            text = payload.decode('utf-8', errors='ignore')
            lines = text.split('\r\n')
            for line in lines:
                if line.lower().startswith('host:'):
                    return line.split(':', 1)[1].strip()
        except Exception:
            pass
        return None

    @staticmethod
    def parse_dns_query(payload: bytes) -> List[str]:
        queries = []
        try:
            if len(payload) < 12:
                return queries
            flags = struct.unpack('>H', payload[2:4])[0]
            if flags & 0x8000:
                return queries
            qdcount = struct.unpack('>H', payload[4:6])[0]
            pos = 12
            for _ in range(qdcount):
                name_parts = []
                while pos < len(payload):
                    length = payload[pos]
                    if length == 0:
                        pos += 1
                        break
                    if length & 0xC0:
                        pos += 2
                        break
                    pos += 1
                    if pos + length <= len(payload):
                        name_parts.append(payload[pos:pos+length].decode('utf-8', errors='ignore'))
                        pos += length
                if name_parts:
                    queries.append('.'.join(name_parts))
        except Exception:
            pass
        return queries


class FlowTracker:
    def __init__(
        self,
        max_flows: int = 500000,
        flow_timeout: float = 300.0,
        cleanup_interval: float = 60.0
    ):
        self.max_flows = max_flows
        self.flow_timeout = flow_timeout
        self.cleanup_interval = cleanup_interval
        self.flows: Dict[FlowKey, FlowFeatures] = {}
        self.packet_buffers: Dict[FlowKey, List[PacketInfo]] = defaultdict(list)
        self.last_cleanup = time.time()
        self.lock = threading.RLock()
        self.stats = {
            "flows_created": 0,
            "flows_expired": 0,
            "flows_exported": 0,
            "packets_processed": 0
        }

    def _get_flow_key(self, src_ip: str, dst_ip: str, src_port: int, dst_port: int, protocol: int) -> FlowKey:
        return FlowKey(src_ip, dst_ip, src_port, dst_port, protocol)

    def _calculate_entropy(self, payload: bytes) -> float:
        return EntropyCalculator.calculate(payload)

    def _parse_application_layer(self, payload: bytes, dst_port: int) -> Tuple[Optional[str], Optional[str], List[str]]:
        tls_sni = None
        http_host = None
        dns_queries = []
        
        if dst_port in (443, 8443) or (dst_port > 1024 and len(payload) > 5):
            tls_sni = PayloadParser.parse_tls_client_hello(payload)
        
        if dst_port in (80, 8080, 8000, 8888) or (dst_port > 1024 and b'HTTP' in payload[:4]):
            http_host = PayloadParser.parse_http_host(payload)
        
        if dst_port == 53:
            dns_queries = PayloadParser.parse_dns_query(payload)
        
        return tls_sni, http_host, dns_queries

    def process_packet(
        self,
        src_ip: str,
        dst_ip: str,
        src_port: int,
        dst_port: int,
        protocol: int,
        timestamp: float,
        length: int,
        tcp_flags: int,
        payload: bytes
    ) -> Optional[FlowFeatures]:
        with self.lock:
            self.stats["packets_processed"] += 1
            now = time.time()
            
            if now - self.last_cleanup > self.cleanup_interval:
                self._cleanup_expired_flows(now)
                self.last_cleanup = now

            fkey = self._get_flow_key(src_ip, dst_ip, src_port, dst_port, protocol)
            rev_key = fkey.reverse()
            
            direction = 0
            existing_flow = None
            
            if fkey in self.flows:
                existing_flow = self.flows[fkey]
                direction = 0
            elif rev_key in self.flows:
                existing_flow = self.flows[rev_key]
                direction = 1
            else:
                if len(self.flows) >= self.max_flows:
                    self._evict_oldest_flow()
                
                payload_entropy = self._calculate_entropy(payload)
                tls_sni, http_host, dns_queries = self._parse_application_layer(payload, dst_port)
                
                flow = FlowFeatures(
                    flow_id=fkey.to_string(),
                    src_ip=src_ip,
                    dst_ip=dst_ip,
                    src_port=src_port,
                    dst_port=dst_port,
                    protocol=protocol,
                    start_time=timestamp,
                    last_time=timestamp,
                    duration_ms=0,
                    packets_fwd=1,
                    packets_bwd=0,
                    bytes_fwd=length,
                    bytes_bwd=0,
                    iat_fwd=[],
                    iat_bwd=[],
                    pkt_len_fwd=[length],
                    pkt_len_bwd=[],
                    tcp_flags_fwd={"SYN": 1 if tcp_flags & 0x02 else 0},
                    tcp_flags_bwd={},
                    payload_entropy_fwd=[payload_entropy],
                    payload_entropy_bwd=[],
                    tls_sni=tls_sni,
                    http_host=http_host,
                    dns_queries=dns_queries
                )
                self.flows[fkey] = flow
                self.stats["flows_created"] += 1
                return None

            flow = existing_flow
            flow.last_time = timestamp
            flow.duration_ms = (timestamp - flow.start_time) * 1000
            payload_entropy = self._calculate_entropy(payload)
            
            tls_sni, http_host, dns_queries = self._parse_application_layer(payload, dst_port if direction == 0 else src_port)
            if tls_sni and not flow.tls_sni:
                flow.tls_sni = tls_sni
            if http_host and not flow.http_host:
                flow.http_host = http_host
            flow.dns_queries.extend(dns_queries)

            buf_key = fkey if direction == 0 else rev_key
            
            if direction == 0:
                flow.packets_fwd += 1
                flow.bytes_fwd += length
                flow.pkt_len_fwd.append(length)
                flow.payload_entropy_fwd.append(payload_entropy)
                if flow.packets_fwd > 1 and self.packet_buffers[buf_key]:
                    flow.iat_fwd.append((timestamp - self.packet_buffers[buf_key][-1].timestamp) * 1000)
                flag_str = self._flags_to_str(tcp_flags)
                flow.tcp_flags_fwd[flag_str] = flow.tcp_flags_fwd.get(flag_str, 0) + 1
            else:
                flow.packets_bwd += 1
                flow.bytes_bwd += length
                flow.pkt_len_bwd.append(length)
                flow.payload_entropy_bwd.append(payload_entropy)
                if flow.packets_bwd > 1 and self.packet_buffers[buf_key]:
                    flow.iat_bwd.append((timestamp - self.packet_buffers[buf_key][-1].timestamp) * 1000)
                flag_str = self._flags_to_str(tcp_flags)
                flow.tcp_flags_bwd[flag_str] = flow.tcp_flags_bwd.get(flag_str, 0) + 1

            self.packet_buffers[fkey if direction == 0 else rev_key].append(
                PacketInfo(timestamp, length, direction, tcp_flags, payload, payload_entropy)
            )

            if len(self.packet_buffers[fkey if direction == 0 else rev_key]) > 100:
                self.packet_buffers[fkey if direction == 0 else rev_key].pop(0)

            return flow

    def _flags_to_str(self, flags: int) -> str:
        names = []
        if flags & 0x01: names.append("FIN")
        if flags & 0x02: names.append("SYN")
        if flags & 0x04: names.append("RST")
        if flags & 0x08: names.append("PSH")
        if flags & 0x10: names.append("ACK")
        if flags & 0x20: names.append("URG")
        return "|".join(names) if names else "NONE"

    def _cleanup_expired_flows(self, now: float):
        expired = []
        for fkey, flow in self.flows.items():
            if now - flow.last_time > self.flow_timeout:
                expired.append(fkey)
        
        for fkey in expired:
            flow = self.flows.pop(fkey)
            self.packet_buffers.pop(fkey, None)
            self.packet_buffers.pop(fkey.reverse(), None)
            self.stats["flows_expired"] += 1
            self.stats["flows_exported"] += 1

    def _evict_oldest_flow(self):
        if not self.flows:
            return
        oldest = min(self.flows.items(), key=lambda x: x[1].last_time)
        fkey = oldest[0]
        self.flows.pop(fkey, None)
        self.packet_buffers.pop(fkey, None)
        self.packet_buffers.pop(fkey.reverse(), None)
        self.stats["flows_expired"] += 1

    def get_ready_flows(self, min_packets: int = 2, min_duration_ms: float = 100) -> List[FlowFeatures]:
        with self.lock:
            ready = []
            for fkey, flow in list(self.flows.items()):
                if (flow.packets_fwd + flow.packets_bwd >= min_packets and 
                    flow.duration_ms >= min_duration_ms):
                    ready.append(flow)
            return ready

    def export_flow(self, flow: FlowFeatures) -> Dict[str, Any]:
        with self.lock:
            fkey = FlowKey(flow.src_ip, flow.dst_ip, flow.src_port, flow.dst_port, flow.protocol)
            self.flows.pop(fkey, None)
            self.packet_buffers.pop(fkey, None)
            self.packet_buffers.pop(fkey.reverse(), None)
            self.stats["flows_exported"] += 1
            return flow.to_dict()

    def get_stats(self) -> Dict[str, Any]:
        with self.lock:
            return {
                **self.stats,
                "active_flows": len(self.flows),
                "buffered_packets": sum(len(b) for b in self.packet_buffers.values())
            }


class FeatureExtractionEngine:
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        export_interval: float = 1.0,
        min_flow_packets: int = 2,
        min_flow_duration_ms: float = 100
    ):
        self.tracker = FlowTracker()
        self.export_interval = export_interval
        self.min_flow_packets = min_flow_packets
        self.min_flow_duration_ms = min_flow_duration_ms
        self.last_export = time.time()
        self.redis_client = None
        
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=True, protocol=2)
                self.redis_client.ping()
            except Exception as e:
                print(f"Redis connection failed: {e}")
                self.redis_client = None

        self.export_callback: Optional[Callable[[Dict], None]] = None

    def set_export_callback(self, callback: Callable[[Dict], None]):
        self.export_callback = callback

    def process_packet(self, packet_meta) -> Optional[Dict]:
        timestamp = packet_meta.timestamp_ns / 1e9
        
        def ip_to_str(ip_int: int) -> str:
            return ".".join(str((ip_int >> (8 * i)) & 0xFF) for i in [3, 2, 1, 0])

        flow = self.tracker.process_packet(
            src_ip=ip_to_str(packet_meta.src_ip),
            dst_ip=ip_to_str(packet_meta.dst_ip),
            src_port=packet_meta.src_port,
            dst_port=packet_meta.dst_port,
            protocol=packet_meta.protocol,
            timestamp=timestamp,
            length=packet_meta.pkt_len,
            tcp_flags=packet_meta.tcp_flags,
            payload=packet_meta.payload
        )

        now = time.time()
        if now - self.last_export > self.export_interval:
            self._export_ready_flows()
            self.last_export = now

        return flow.to_dict() if flow else None

    def _export_ready_flows(self):
        ready_flows = self.tracker.get_ready_flows(self.min_flow_packets, self.min_flow_duration_ms)
        for flow in ready_flows:
            flow_dict = self.tracker.export_flow(flow)
            
            if self.redis_client:
                try:
                    # Serialize values for Redis xadd
                    import json
                    redis_dict = {}
                    for k, v in flow_dict.items():
                        if isinstance(v, (dict, list, bool)) or v is None:
                            redis_dict[k] = json.dumps(v)
                        else:
                            redis_dict[k] = v
                    self.redis_client.xadd("flows:features", redis_dict, maxlen=50000)
                except Exception as e:
                    if "unknown command" in str(e).lower():
                        import json
                        self.redis_client.rpush("list:flows:features", json.dumps(flow_dict))
                        self.redis_client.ltrim("list:flows:features", -50000, -1)
                    else:
                        print(f"Redis export error: {e}")
            
            if self.export_callback:
                try:
                    self.export_callback(flow_dict)
                except Exception as e:
                    print(f"Export callback error: {e}")

    def get_stats(self) -> Dict:
        return self.tracker.get_stats()

    def flush_all(self):
        self._export_ready_flows()
        with self.tracker.lock:
            for fkey, flow in list(self.tracker.flows.items()):
                self.tracker.export_flow(flow)


def main():
    import sys
    sys.path.append("../capture")
    from capture_manager import PacketMetadata, EBpfPacketCapture
    
    engine = FeatureExtractionEngine()
    
    def on_flow_exported(flow_dict):
        print(f"Exported flow: {flow_dict['flow_id']} "
              f"pkts={flow_dict['packets_fwd']+flow_dict['packets_bwd']} "
              f"bytes={flow_dict['bytes_fwd']+flow_dict['bytes_bwd']} "
              f"dur={flow_dict['duration_ms']:.1f}ms "
              f"entropy_fwd={flow_dict['payload_entropy_fwd_mean']:.2f}")

    engine.set_export_callback(on_flow_exported)

    def packet_handler(meta: PacketMetadata):
        engine.process_packet(meta)

    capture = EBpfPacketCapture(
        interface="eth0",
        ebpf_program_path="../capture/ebpf/packet_filter.c",
        callback=packet_handler
    )
    
    if not capture.load_program():
        print("Failed to load eBPF, exiting")
        return

    try:
        capture.run()
    finally:
        engine.flush_all()
        print(f"Engine stats: {engine.get_stats()}")


if __name__ == "__main__":
    main()