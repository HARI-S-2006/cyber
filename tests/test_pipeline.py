#!/usr/bin/env python3
"""Test the complete pipeline end-to-end"""

import sys
import time
sys.path.insert(0, 'C:\\Users\\shari\\cyber-threat-visualizer\\backend')

def test_feature_extraction():
    print("=== Testing Feature Extraction ===")
    from features.feature_extractor import FeatureExtractionEngine
    
    engine = FeatureExtractionEngine(redis_url='redis://localhost:6379', export_interval=10.0)
    
    class MockMeta:
        def __init__(self, i):
            self.timestamp_ns = int((time.time() + i * 0.1) * 1e9)
            self.src_ip = 0xC0A80101
            self.dst_ip = 0xC0A80102
            self.src_port = 12345
            self.dst_port = 80
            self.protocol = 6
            self.tcp_flags = 0x10 if i > 0 else 0x02
            self.payload_len = 10
            self.payload = b'GET / HTTP/1.1'
            self.pkt_len = 100
            self.direction = 0
    
    for i in range(10):
        result = engine.process_packet(MockMeta(i))
        if result:
            print(f"  Flow exported: {result['flow_id']} pkts={result['packets_fwd']+result['packets_bwd']} score={result['threat_score']:.2f}")
    
    engine.flush_all()
    stats = engine.get_stats()
    print(f"  Engine stats: {stats}")
    return True

def test_anomaly_detection():
    print("\n=== Testing Anomaly Detection ===")
    from model.anomaly_detector import OnlineAnomalyDetector, generate_synthetic_data
    
    detector = OnlineAnomalyDetector('backend/models/isolation_forest.pkl', redis_url='redis://localhost:6379')
    
    test_flow = {
        "flow_id": "test-flow-1",
        "duration_ms": 5000,
        "packets_fwd": 100,
        "packets_bwd": 80,
        "bytes_fwd": 50000,
        "bytes_bwd": 40000,
        "iat_fwd_mean": 50,
        "iat_fwd_std": 10,
        "iat_bwd_mean": 60,
        "iat_bwd_std": 15,
        "pkt_len_fwd_mean": 500,
        "pkt_len_fwd_std": 50,
        "pkt_len_bwd_mean": 500,
        "pkt_len_bwd_std": 50,
        "tcp_syn_fwd": 1,
        "tcp_ack_fwd": 90,
        "tcp_fin_fwd": 1,
        "tcp_rst_fwd": 0,
        "tcp_psh_fwd": 10,
        "tcp_syn_bwd": 0,
        "tcp_ack_bwd": 75,
        "tcp_fin_bwd": 1,
        "tcp_rst_bwd": 0,
        "tcp_psh_bwd": 5,
        "payload_entropy_fwd_mean": 7.5,
        "payload_entropy_bwd_mean": 7.2,
        "protocol_encoded": 6,
        "src_port_category": 1,
        "dst_port_category": 2
    }
    
    result = detector.detect(test_flow)
    print(f"  Detection result: {result}")
    
    # Test with anomaly-like features
    anomaly_flow = test_flow.copy()
    anomaly_flow["flow_id"] = "test-anomaly-1"
    anomaly_flow["payload_entropy_fwd_mean"] = 7.9
    anomaly_flow["payload_entropy_bwd_mean"] = 7.9
    anomaly_flow["packets_fwd"] = 1000
    anomaly_flow["bytes_fwd"] = 5000000
    
    result2 = detector.detect(anomaly_flow)
    print(f"  Anomaly detection result: {result2}")
    
    stats = detector.get_stats()
    print(f"  Detector stats: {stats}")
    return True

def test_capture_manager():
    print("\n=== Testing Capture Manager (interface listing) ===")
    from capture.capture_manager import list_interfaces
    
    interfaces = list_interfaces()
    print(f"  Available interfaces: {len(interfaces)}")
    for iface in interfaces[:5]:
        print(f"    {iface}")
    return True

def test_streaming():
    print("\n=== Testing Streaming (Redis connectivity) ===")
    import asyncio
    import sys
    sys.path.insert(0, 'C:\\Users\\shari\\cyber-threat-visualizer\\backend')
    
    async def test_async_streaming():
        from streaming.stream_manager import RedisStreamManager, StreamConfig
        
        config = StreamConfig()
        manager = RedisStreamManager(config)
        
        try:
            await manager.connect()
            print(f"  Redis connection: OK (mode: {'streams' if manager._use_streams else 'lists_fallback'})")
            
            # Test publish
            test_data = {'field1': 'value1', 'field2': 'value2', 'test': True}
            await manager.publish('test:stream', test_data)
            print("  Publish: OK")
            
            # Test get recent
            messages = await manager.get_recent('test:stream', count=10)
            print(f"  Get recent: {len(messages)} messages")
            
            # Test stream info
            info = await manager.get_stream_info('test:stream')
            print(f"  Stream info: {info}")
            
            await manager.disconnect()
            return True
        except Exception as e:
            print(f"  Streaming error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    try:
        result = asyncio.run(test_async_streaming())
        return result
    except Exception as e:
        print(f"  Async streaming error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_imports():
    print("\n=== Testing API Imports ===")
    try:
        from streaming.stream_manager import RedisStreamManager, ThreatAggregator, create_app
        print("  Streaming imports: OK")
        return True
    except Exception as e:
        print(f"  Import error: {e}")
        return False

def main():
    print("=" * 60)
    print("CYBER THREAT VISUALIZER - FULL PIPELINE TEST")
    print("=" * 60)
    
    results = []
    results.append(("Feature Extraction", test_feature_extraction()))
    results.append(("Anomaly Detection", test_anomaly_detection()))
    results.append(("Capture Manager", test_capture_manager()))
    results.append(("Streaming/Redis", test_streaming()))
    results.append(("API Imports", test_api_imports()))
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    all_passed = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        color = "\033[92m" if passed else "\033[91m"
        print(f"  {name}: {color}{status}\033[0m")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\nALL TESTS PASSED!")
        return 0
    else:
        print("\nSOME TESTS FAILED!")
        return 1

if __name__ == "__main__":
    sys.exit(main())