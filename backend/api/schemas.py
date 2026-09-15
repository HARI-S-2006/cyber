"""Pydantic schemas for API requests/responses."""
import time
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# Packet/Flow schemas
class PacketBase(BaseModel):
    timestamp: float
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: str
    length: int
    tcp_flags: str = ""
    ttl: int = 0


class FlowFeatures(BaseModel):
    # Flow identification
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: str
    
    # Time
    start_time: float
    last_time: float
    duration: float
    
    # Volume
    packet_count: int
    byte_count: int
    fwd_packets: int
    fwd_bytes: int
    bwd_packets: int
    bwd_bytes: int
    
    # Rates
    packet_rate: float
    byte_rate: float
    
    # Packet sizes
    avg_packet_size: float
    std_packet_size: float
    min_packet_size: float
    max_packet_size: float
    fwd_avg_size: float
    fwd_std_size: float
    bwd_avg_size: float
    bwd_std_size: float
    
    # Inter-arrival times
    avg_iat: float
    std_iat: float
    min_iat: float
    max_iat: float
    
    # Direction
    fwd_packet_ratio: float
    fwd_byte_ratio: float
    fwd_avg_size: float
    fwd_std_size: float
    bwd_avg_size: float
    bwd_std_size: float
    
    # TCP flags
    syn_ratio: float
    ack_ratio: float
    fin_ratio: float
    rst_ratio: float
    psh_ratio: float
    urg_ratio: float
    
    # Protocol distribution
    protocol_distribution: Dict[str, int] = {}
    tcp_flag_distribution: Dict[str, int] = {}
    
    # GeoIP
    src_lat: float = 0.0
    src_lon: float = 0.0
    dst_lat: float = 0.0
    dst_lon: float = 0.0
    src_country: str = "Unknown"
    dst_country: str = "Unknown"
    src_city: str = "Unknown"
    dst_city: str = "Unknown"
    
    # Anomaly
    anomaly: bool = False
    threat_score: float = 0.0
    threat_type: str = "UNKNOWN"
    threat_details: dict = {}


class FlowFeaturesResponse(FlowFeatures):
    class Config:
        from_attributes = True


# Threat/Anomaly schemas
class ThreatEvent(BaseModel):
    id: str
    timestamp: float
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: str
    threat_type: str
    threat_score: float
    details: dict = {}
    src_lat: float = 0.0
    src_lon: float = 0.0
    dst_lat: float = 0.0
    dst_lon: float = 0.0
    src_country: str = "Unknown"
    dst_country: str = "Unknown"


class ThreatEventResponse(ThreatEvent):
    class Config:
        from_attributes = True


class ThreatStats(BaseModel):
    total_threats: int
    threats_by_type: Dict[str, int]
    threats_by_country: Dict[str, int]
    top_attackers: List[Dict[str, Any]]
    time_window: str


# System schemas
class SystemStats(BaseModel):
    timestamp: float
    packets_per_sec: float
    total_packets: int
    features_extracted: int
    active_flows: int
    threats_detected: int
    anomaly_rate: float
    uptime_seconds: float


class GeoIPResponse(BaseModel):
    ip: str
    latitude: float
    longitude: float
    country: str
    city: str
    isp: str
    timestamp: float


class ConnectionSummary(BaseModel):
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: str
    packet_count: int
    byte_count: int
    duration: float
    anomaly: bool
    threat_score: float
    threat_type: str
    start_time: float
    last_time: float


# WebSocket message schemas
class WSMessage(BaseModel):
    type: str
    data: Any
    timestamp: float = Field(default_factory=time.time)


class WSPacketMessage(WSMessage):
    type: str = "packet"
    data: FlowFeatures


class WSThreatMessage(WSMessage):
    type: str = "threat"
    data: ThreatEvent


class WSStatsMessage(WSMessage):
    type: str = "stats"
    data: SystemStats


class WSErrorMessage(WSMessage):
    type: str = "error"
    data: Dict[str, str]


# Request/Response
class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=500)


class ThreatFilterParams(PaginationParams):
    threat_type: Optional[str] = None
    min_score: Optional[float] = None
    src_ip: Optional[str] = None
    dst_ip: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None


class ConnectionFilterParams(PaginationParams):
    src_ip: Optional[str] = None
    dst_ip: Optional[str] = None
    protocol: Optional[str] = None
    anomaly: Optional[bool] = None
    min_score: Optional[float] = None


# Import time for timestamp default
import time