"""API routes for the Cyber Threat Visualizer."""
import time
import json
import logging
from typing import Optional, List
from fastapi import APIRouter, Query, HTTPException, Depends
from fastapi.responses import JSONResponse

from backend.api.schemas import (
    FlowFeaturesResponse, ThreatEventResponse, ThreatStats,
    SystemStats, GeoIPResponse, ConnectionSummary,
    ThreatFilterParams, ConnectionFilterParams, PaginationParams
)
from backend.utils.redis_client import redis_manager
from backend.ml.model import anomaly_detector, detection_service
from backend.config import settings

router = APIRouter()

logger = logging.getLogger(__name__)


# System endpoints
@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "2.0.0"
    }


@router.get("/stats", response_model=SystemStats)
async def get_system_stats():
    """Get current system statistics."""
    # Get stats from Redis
    stats_data = await redis_manager.get("system:stats") or {}
    
    # Get ML stats
    ml_stats = anomaly_detector.get_stats()
    
    return SystemStats(
        timestamp=time.time(),
        packets_per_sec=stats_data.get("packets_per_sec", 0),
        total_packets=stats_data.get("total_packets", 0),
        features_extracted=stats_data.get("features_extracted", 0),
        active_flows=stats_data.get("active_flows", 0),
        threats_detected=ml_stats.get("anomaly_count", 0),
        anomaly_rate=ml_stats.get("anomaly_rate", 0.0),
        uptime_seconds=time.time() - getattr(settings, '_start_time', time.time())
    )


@router.get("/threats", response_model=List[ThreatEventResponse])
async def get_threats(
    threat_type: Optional[str] = Query(None),
    min_score: Optional[float] = Query(None, ge=0, le=1),
    src_ip: Optional[str] = None,
    dst_ip: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """Get recent threats with filtering."""
    # Get threats from Redis stream
    threats = []
    try:
        streams = await redis_manager.xread(
            {settings.channel_threats: "0"},
            count=limit + offset
        )
        
        for stream_name, messages in streams:
            for msg_id, msg_data in messages:
                threat = json.loads(msg_data) if isinstance(msg_data, str) else msg_data
                
                # Apply filters
                if threat_type and threat.get("threat_type") != threat_type:
                    continue
                if min_score and threat.get("threat_score", 0) < min_score:
                    continue
                if src_ip and threat.get("src_ip") != src_ip:
                    continue
                if dst_ip and threat.get("dst_ip") != dst_ip:
                    continue
                
                threats.append(threat)
    except Exception as e:
        logger.error(f"Error fetching threats: {e}")
    
    return threats[offset:offset + limit]


@router.get("/threats/stats", response_model=ThreatStats)
async def get_threat_stats(
    time_window: str = Query("1h", regex="^(1h|6h|24h|7d)$")
):
    """Get threat statistics for a time window."""
    # Calculate time range
    now = time.time()
    window_seconds = {
        "1h": 3600,
        "6h": 21600,
        "24h": 86400,
        "7d": 604800
    }[time_window]
    
    cutoff = time.time() - window_seconds
    
    # Get threats from stream
    threats = []
    try:
        streams = await redis_manager.xread(
            {settings.channel_threats: "0"},
            count=10000
        )
        
        threat_types = {}
        countries = {}
        attackers = {}
        
        for stream_name, messages in streams:
            for msg_id, msg_data in messages:
                threat = json.loads(msg_data) if isinstance(msg_data, str) else msg_data
                
                if threat.get("timestamp", 0) < cutoff:
                    continue
                
                # Count by type
                ttype = threat.get("threat_type", "UNKNOWN")
                threat_types[ttype] = threat_types.get(ttype, 0) + 1
                
                # Count by country
                country = threat.get("src_country", "Unknown")
                countries[country] = countries.get(country, 0) + 1
                
                # Count attackers
                src_ip = threat.get("src_ip", "unknown")
                if src_ip not in attackers:
                    attackers[src_ip] = {
                        "ip": src_ip,
                        "count": 0,
                        "max_score": 0,
                        "threat_types": set()
                    }
                attackers[src_ip]["count"] += 1
                attackers[src_ip]["max_score"] = max(
                    attackers[src_ip]["max_score"],
                    threat.get("threat_score", 0)
                )
                attackers[src_ip]["threat_types"].add(
                    threat.get("threat_type", "UNKNOWN")
                )
        
        # Top attackers
        top_attackers = sorted(
            attackers.values(),
            key=lambda x: (x["count"], x["max_score"]),
            reverse=True
        )[:10]
        
        # Convert sets to lists for JSON
        for a in top_attackers:
            a["threat_types"] = list(a["threat_types"])
        
        return ThreatStats(
            total_threats=sum(threat_types.values()),
            threats_by_type=threat_types,
            threats_by_country=countries,
            top_attackers=top_attackers,
            time_window=time_window
        )
    except Exception as e:
        logger.error(f"Error getting threat stats: {e}")
        return ThreatStats(
            total_threats=0,
            threats_by_type={},
            threats_by_country={},
            top_attackers=[],
            time_window=time_window
        )


@router.get("/connections", response_model=List[ConnectionSummary])
async def get_connections(
    src_ip: Optional[str] = None,
    dst_ip: Optional[str] = None,
    protocol: Optional[str] = None,
    anomaly: Optional[bool] = None,
    min_score: Optional[float] = Query(None, ge=0, le=1),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """Get active connections with filtering."""
    # Get from Redis stream
    connections = []
    try:
        streams = await redis_manager.xread(
            {settings.channel_features: "0"},
            count=limit + offset
        )
        
        for stream_name, messages in streams:
            for msg_id, msg_data in messages:
                conn = json.loads(msg_data) if isinstance(msg_data, str) else msg_data
                
                # Apply filters
                if src_ip and conn.get("src_ip") != src_ip:
                    continue
                if dst_ip and conn.get("dst_ip") != dst_ip:
                    continue
                if protocol and conn.get("protocol") != protocol:
                    continue
                if anomaly is not None and conn.get("anomaly") != anomaly:
                    continue
                if min_score and conn.get("threat_score", 0) < min_score:
                    continue
                
                connections.append(ConnectionSummary(**conn))
    except Exception as e:
        logger.error(f"Error fetching connections: {e}")
    
    return connections[offset:offset + limit]


@router.get("/geoip/{ip}", response_model=GeoIPResponse)
async def get_geoip(ip: str):
    """Get GeoIP information for an IP address."""
    from backend.sniffer.geoip_cache import get_location
    
    location = await get_location(ip)
    if not location:
        raise HTTPException(status_code=404, detail="IP location not found")
    
    return GeoIPResponse(**location.__dict__)


@router.get("/api/ml/stats")
async def get_ml_stats():
    """Get ML model statistics."""
    return anomaly_detector.get_stats()


@router.post("/api/ml/retrain")
async def retrain_model():
    """Manually trigger model retraining."""
    from backend.ml.model import detection_service
    
    async with detection_service._buffer_lock:
        if len(detection_service._retrain_buffer) < 500:
            return {"error": "Insufficient data for retraining", "samples": len(detection_service._retrain_buffer)}
        
        # Trigger retraining
        normal_samples = [
            f for f in detection_service._retrain_buffer
            if not f.get("anomaly", False)
        ]
        
        if len(normal_samples) < 500:
            return {"error": "Insufficient normal samples", "normal_samples": len(normal_samples)}
        
        result = anomaly_detector.train(normal_samples)
        
        # Clear buffer
        detection_service._retrain_buffer.clear()
        
        return {"status": "retrained", "result": result}


@router.get("/api/packets/recent")
async def get_recent_packets(limit: int = Query(100, ge=1, le=1000)):
    """Get recent packets from the features stream."""
    packets = []
    try:
        streams = await redis_manager.xread(
            {settings.channel_features: "0"},
            count=limit
        )
        
        for stream_name, messages in streams:
            for msg_id, msg_data in messages:
                pkt = json.loads(msg_data) if isinstance(msg_data, str) else msg_data
                packets.append(pkt)
    except Exception as e:
        logger.error(f"Error fetching recent packets: {e}")
    
    return packets[-limit:]


# Import for logging
import logging
import time
import json

logger = logging.getLogger(__name__)