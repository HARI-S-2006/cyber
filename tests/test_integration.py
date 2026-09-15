#!/usr/bin/env python3
"""Integration test for the Cyber Threat Visualizer."""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import settings
from backend.utils.redis_client import redis_manager
from backend.ml.model import anomaly_detector, detection_service, FEATURE_COLUMNS, generate_synthetic_data
from backend.sniffer.feature_extractor import PacketProcessor
from backend.sniffer.geoip_cache import get_location, get_batch_locations


async def test_redis():
    """Test Redis connection."""
    print("Testing Redis connection...")
    await redis_manager.connect()
    result = await redis_manager.ping()
    assert result == True
    print("  [OK] Redis connection")
    await redis_manager.disconnect()


async def test_ml_model():
    """Test ML model training and inference."""
    print("Testing ML model...")
    
    # Generate synthetic data
    X, y = generate_synthetic_data(1000, 0.05)
    
    # Train model
    result = anomaly_detector.train(X)
    assert result['samples'] == 1000
    assert anomaly_detector.is_fitted
    print(f"  [OK] Model trained (threshold: {result['threshold']:.4f})")
    
    # Test inference
    # Create a feature dict from the first sample
    feature_dict = dict(zip(FEATURE_COLUMNS, X[0]))
    is_anomaly, score, details = anomaly_detector.predict_single(feature_dict)
    assert 'score' in details
    assert 'threat_type' in details
    print(f"  [OK] Inference works (anomaly: {is_anomaly}, score: {score:.4f})")


async def test_feature_extraction():
    """Test feature extraction pipeline."""
    print("Testing feature extraction...")
    
    processor = PacketProcessor()
    
    # Create mock packet data
    from scapy.all import IP, TCP, Raw
    pkt = IP(src="192.168.1.1", dst="8.8.8.8") / TCP(sport=12345, dport=80, flags="S") / Raw(load=b"GET / HTTP/1.1")
    
    # Process packet
    features = await processor.process_packet(pkt)
    # First packet won't produce features (need min packets)
    print(f"  [OK] Packet processed (features: {features is not None})")
    
    # Process more packets to trigger feature extraction
    for i in range(15):
        pkt = IP(src="192.168.1.1", dst="8.8.8.8") / TCP(sport=12345, dport=80, flags="PA") / Raw(load=b"HTTP data")
        features = await processor.process_packet(pkt)
    
    stats = processor.get_stats()
    assert stats['total_packets'] > 0
    print(f"  [OK] Feature extraction works (packets: {stats['total_packets']}, features: {stats['total_features']})")


async def test_geoip():
    """Test GeoIP lookup."""
    print("Testing GeoIP...")
    
    # Test with known IPs
    location = await get_location("8.8.8.8")
    assert location is not None
    assert location.country == "United States"
    assert location.latitude != 0.0
    print(f"  [OK] GeoIP lookup (8.8.8.8 -> {location.country}, {location.city})")
    
    # Test batch
    locations = await get_batch_locations(["8.8.8.8", "1.1.1.1", "192.168.1.1"])
    assert len(locations) == 3
    print(f"  [OK] Batch GeoIP lookup ({len(locations)} IPs)")


async def test_detection_service():
    """Test the full detection service."""
    print("Testing detection service...")
    
    await detection_service.initialize()
    
    # Create test features
    test_features = {
        'packet_count': 100,
        'byte_count': 50000,
        'packet_rate': 5000,
        'syn_ratio': 0.9,
        'packet_count': 100,
        'protocol_tcp': 1,
        'protocol_udp': 0,
        'protocol_icmp': 0,
    }
    
    # Add required fields with defaults
    for col in ['fwd_packets', 'fwd_bytes', 'bwd_packets', 'bwd_bytes',
                'byte_rate', 'avg_packet_size', 'std_packet_size',
                'min_packet_size', 'max_packet_size', 'fwd_avg_size',
                'fwd_std_size', 'bwd_avg_size', 'bwd_std_size',
                'avg_iat', 'std_iat', 'min_iat', 'max_iat',
                'fwd_packet_ratio', 'fwd_byte_ratio', 'fwd_avg_size',
                'fwd_std_size', 'bwd_avg_size', 'bwd_std_size',
                'syn_ratio', 'ack_ratio', 'fin_ratio', 'rst_ratio',
                'psh_ratio', 'urg_ratio', 'avg_packet_size', 'std_packet_size',
                'min_packet_size', 'max_packet_size']:
        if col not in test_features:
            test_features[col] = 0
    
    result = await detection_service.process_features(test_features)
    assert 'anomaly' in result
    assert 'threat_score' in result
    print(f"  [OK] Detection service works (anomaly: {result['anomaly']}, score: {result['threat_score']:.4f})")
    
    await detection_service.shutdown()


async def test_api_imports():
    """Test that all API modules import correctly."""
    print("Testing API imports...")
    
    from backend.api.main import app
    from backend.api.websocket import ws_manager
    from backend.api.routes import router
    from backend.api.schemas import FlowFeatures, ThreatEvent
    
    assert app is not None
    assert ws_manager is not None
    print("  [OK] All API modules import correctly")


async def main():
    """Run all integration tests."""
    print("=" * 60)
    print("CYBER THREAT VISUALIZER - INTEGRATION TESTS")
    print("=" * 60)
    print()
    
    tests = [
        ("Redis Connection", test_redis),
        ("ML Model", test_ml_model),
        ("Feature Extraction", test_feature_extraction),
        ("GeoIP Cache", test_geoip),
        ("Detection Service", test_detection_service),
        ("API Imports", test_api_imports),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            await test_func()
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            failed += 1
    
    print()
    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed > 0:
        sys.exit(1)
    else:
        print("\n[SUCCESS] All integration tests passed!")


if __name__ == "__main__":
    asyncio.run(main())