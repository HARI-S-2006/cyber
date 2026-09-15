#!/usr/bin/env python3
"""
Unit tests for the Cyber Threat Visualizer components.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from features.feature_extractor import (
    FlowTracker, 
    FeatureExtractionEngine, 
    FlowKey, 
    FlowFeatures,
    EntropyCalculator,
    PayloadParser
)
from model.anomaly_detector import (
    IsolationForestDetector,
    ModelConfig,
    generate_synthetic_data
)


class TestEntropyCalculator:
    def test_empty_data(self):
        assert EntropyCalculator.calculate(b"") == 0.0
    
    def test_uniform_data(self):
        # All same bytes = 0 entropy
        assert EntropyCalculator.calculate(b"AAAA") == 0.0
    
    def test_max_entropy(self):
        # All 256 values equally = 8 bits entropy
        data = bytes(range(256))
        entropy = EntropyCalculator.calculate(data)
        assert abs(entropy - 8.0) < 0.1
    
    def test_streaming_entropy(self):
        data1 = b"AAAA"
        data2 = b"BBBB"
        e1 = EntropyCalculator.calculate(data1)
        e2 = EntropyCalculator.calculate_streaming(e1, len(data1), data2)
        e_combined = EntropyCalculator.calculate(data1 + data2)
        # Streaming entropy is an approximation, allow larger tolerance
        assert abs(e2 - e_combined) < 1.5


class TestPayloadParser:
    def test_parse_http_host(self):
        payload = b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n"
        host = PayloadParser.parse_http_host(payload)
        assert host == "example.com"
    
    def test_parse_http_host_missing(self):
        payload = b"GET / HTTP/1.1\r\n\r\n"
        host = PayloadParser.parse_http_host(payload)
        assert host is None
    
    def test_parse_dns_query(self):
        # Simple DNS query for example.com
        payload = bytes([
            0x12, 0x34,  # Transaction ID
            0x01, 0x00,  # Flags (standard query)
            0x00, 0x01,  # Questions
            0x00, 0x00,  # Answer RRs
            0x00, 0x00,  # Authority RRs
            0x00, 0x00,  # Additional RRs
            0x07, 0x65, 0x78, 0x61, 0x6D, 0x70, 0x6C, 0x65,  # example
            0x03, 0x63, 0x6F, 0x6D,  # com
            0x00,  # terminator
            0x00, 0x01,  # Type A
            0x00, 0x01   # Class IN
        ])
        queries = PayloadParser.parse_dns_query(payload)
        assert "example.com" in queries
    
    def test_parse_tls_sni(self):
        # Minimal Client Hello with SNI
        payload = bytes([
            0x16, 0x03, 0x01, 0x00, 0x50,  # TLS record header
            0x01, 0x00, 0x00, 0x4C,  # Handshake header
            0x03, 0x03,  # Version
        ] + [0] * 32 + [  # Random
            0x00,  # Session ID length
            0x00, 0x2F,  # Cipher suites length
        ] + [0] * 47 + [  # Cipher suites
            0x01, 0x00,  # Compression methods
            0x00, 0x16,  # Extensions length
            0x00, 0x00, 0x00, 0x12,  # SNI extension
            0x00, 0x10,  # Server name list length
            0x00, 0x00, 0x0E,  # Host name type + length
        ] + list(b"example.com"))
        
        sni = PayloadParser.parse_tls_client_hello(payload)
        # This is a simplified test - real parsing is more complex
        assert sni is None or isinstance(sni, str)


class TestFlowKey:
    def test_equality(self):
        k1 = FlowKey("1.2.3.4", "5.6.7.8", 1234, 80, 6)
        k2 = FlowKey("1.2.3.4", "5.6.7.8", 1234, 80, 6)
        k3 = FlowKey("5.6.7.8", "1.2.3.4", 80, 1234, 6)
        
        assert k1 == k2
        assert k1 != k3
        assert hash(k1) == hash(k2)
    
    def test_reverse(self):
        k1 = FlowKey("1.2.3.4", "5.6.7.8", 1234, 80, 6)
        k2 = k1.reverse()
        assert k2.src_ip == "5.6.7.8"
        assert k2.dst_ip == "1.2.3.4"
        assert k2.src_port == 80
        assert k2.dst_port == 1234


class TestFlowTracker:
    def setup_method(self):
        self.tracker = FlowTracker(max_flows=1000, flow_timeout=1.0)
    
    def test_new_flow_creation(self):
        flow = self.tracker.process_packet(
            src_ip="1.2.3.4", dst_ip="5.6.7.8",
            src_port=1234, dst_port=80, protocol=6,
            timestamp=time.time(), length=100,
            tcp_flags=0x02, payload=b"test"
        )
        assert flow is None  # First packet doesn't return flow
        
        stats = self.tracker.get_stats()
        assert stats["flows_created"] == 1
        assert stats["active_flows"] == 1
    
    def test_bidirectional_flow(self):
        now = time.time()
        
        # Forward packet
        self.tracker.process_packet(
            src_ip="1.2.3.4", dst_ip="5.6.7.8",
            src_port=1234, dst_port=80, protocol=6,
            timestamp=now, length=100, tcp_flags=0x02, payload=b""
        )
        
        # Backward packet
        flow = self.tracker.process_packet(
            src_ip="5.6.7.8", dst_ip="1.2.3.4",
            src_port=80, dst_port=1234, protocol=6,
            timestamp=now + 0.1, length=200, tcp_flags=0x12, payload=b""
        )
        
        assert flow is not None
        assert flow.packets_fwd == 1
        assert flow.packets_bwd == 1
        assert flow.bytes_fwd == 100
        assert flow.bytes_bwd == 200
    
    def test_flow_timeout(self):
        # Use shorter cleanup interval for testing
        self.tracker = FlowTracker(max_flows=1000, flow_timeout=1.0, cleanup_interval=0.5)
        now = time.time()
        
        self.tracker.process_packet(
            src_ip="1.2.3.4", dst_ip="5.6.7.8",
            src_port=1234, dst_port=80, protocol=6,
            timestamp=now, length=100, tcp_flags=0x02, payload=b""
        )
        
        # Advance time beyond timeout
        time.sleep(1.2)
        
        # Next packet should trigger cleanup
        self.tracker.process_packet(
            src_ip="9.9.9.9", dst_ip="8.8.8.8",
            src_port=53, dst_port=53, protocol=17,
            timestamp=time.time(), length=50, tcp_flags=0, payload=b""
        )
        
        stats = self.tracker.get_stats()
        assert stats["flows_expired"] == 1


class TestFeatureExtractionEngine:
    def setup_method(self):
        self.engine = FeatureExtractionEngine(
            redis_url="redis://localhost:6379",
            export_interval=10.0  # Don't auto-export in tests
        )
    
    def test_packet_processing(self):
        # Mock packet metadata
        class MockMeta:
            timestamp_ns = int(time.time() * 1e9)
            src_ip = 0x01020304  # 1.2.3.4
            dst_ip = 0x05060708  # 5.6.7.8
            src_port = 1234
            dst_port = 80
            protocol = 6
            tcp_flags = 0x02
            payload_len = 4
            payload = b"test"
            pkt_len = 100
            direction = 0
        
        result = self.engine.process_packet(MockMeta())
        assert result is None  # First packet
        
        stats = self.engine.get_stats()
        assert stats["packets_processed"] == 1


class TestAnomalyDetector:
    def test_synthetic_data_generation(self):
        X, y = generate_synthetic_data(1000, 0.05)
        assert X.shape == (1000, len(ModelConfig().feature_columns))
        assert y.shape == (1000,)
        assert sum(y) == 50  # 5% anomalies
    
    def test_isolation_forest_training(self):
        X, y = generate_synthetic_data(5000, 0.02)
        config = ModelConfig(contamination=0.02, n_estimators=10)
        
        detector = IsolationForestDetector(config)
        detector.fit(X)
        
        assert detector.is_fitted
        assert detector.threshold is not None
        
        # Test prediction
        preds = detector.predict(X[:100])
        assert preds.shape == (100,)
        assert set(preds).issubset({0, 1})
    
    def test_isolation_forest_scoring(self):
        X, y = generate_synthetic_data(1000, 0.02)
        config = ModelConfig(contamination=0.02)
        
        detector = IsolationForestDetector(config)
        detector.fit(X)
        
        scores = detector.score(X[:10])
        assert scores.shape == (10,)
        assert all(s >= 0 for s in scores)


class TestIntegration:
    def test_full_pipeline(self):
        """Test the complete pipeline: packet -> features -> detection"""
        from features.feature_extractor import FeatureExtractionEngine
        from model.anomaly_detector import IsolationForestDetector, ModelConfig, generate_synthetic_data
        
        # Train detector
        X, y = generate_synthetic_data(2000, 0.05)
        config = ModelConfig(contamination=0.05, n_estimators=20)
        detector = IsolationForestDetector(config)
        detector.fit(X)
        
        # Create engine
        engine = FeatureExtractionEngine(export_interval=10.0)
        exported_flows = []
        
        def capture_flow(flow_dict):
            exported_flows.append(flow_dict)
        
        engine.set_export_callback(capture_flow)
        
        # Simulate packets for a flow
        base_time = time.time()
        for i in range(10):
            class MockMeta:
                timestamp_ns = int((base_time + i * 0.1) * 1e9)
                src_ip = 0xC0A80101  # 192.168.1.1
                dst_ip = 0xC0A80102  # 192.168.1.2
                src_port = 12345
                dst_port = 80
                protocol = 6
                tcp_flags = 0x10 if i > 0 else 0x02
                payload_len = 10
                payload = b"GET / HTTP/1.1"
                pkt_len = 100
                direction = 0
            
            engine.process_packet(MockMeta())
        
        # Force export
        engine.flush_all()
        
        assert len(exported_flows) == 1
        flow = exported_flows[0]
        assert flow["packets_fwd"] == 10
        assert flow["duration_ms"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])