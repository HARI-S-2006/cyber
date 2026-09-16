#!/usr/bin/env python3
"""
Main entry point for the Cyber Threat Visualizer backend.
Runs packet capture, feature extraction, anomaly detection, and API server.
"""

import asyncio
import argparse
import signal
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from capture.capture_manager import EBpfPacketCapture, LibpcapFallback, PacketMetadata
from features.feature_extractor import FeatureExtractionEngine
from model.anomaly_detector import OnlineAnomalyDetector
from streaming.stream_manager import run_api_server


class CyberThreatVisualizer:
    def __init__(self, args):
        self.args = args
        self.running = False
        
        # Components
        self.capture = None
        self.feature_engine = None
        self.anomaly_detector = None
        
    def setup_capture(self):
        """Initialize packet capture layer."""
        def packet_handler(meta: PacketMetadata):
            if self.feature_engine:
                self.feature_engine.process_packet(meta)
        
        if self.args.fallback or self.args.interface == "any":
            print("Using libpcap fallback capture")
            self.capture = LibpcapFallback(self.args.interface, packet_handler)
        else:
            print("Using eBPF capture")
            self.capture = EBpfPacketCapture(
                interface=self.args.interface,
                ebpf_program_path=self.args.ebpf_program,
                redis_url=self.args.redis,
                callback=packet_handler
            )
            if not self.capture.load_program():
                print("eBPF load failed, falling back to libpcap")
                self.capture = LibpcapFallback(self.args.interface, packet_handler)
    
    def setup_feature_extraction(self):
        """Initialize feature extraction engine."""
        self.feature_engine = FeatureExtractionEngine(
            redis_url=self.args.redis,
            export_interval=1.0
        )
        
        def on_flow_exported(flow_dict):
            if self.anomaly_detector:
                self.anomaly_detector.detect(flow_dict)
        
        self.feature_engine.set_export_callback(on_flow_exported)
    
    def setup_anomaly_detection(self):
        """Initialize anomaly detector."""
        model_path = self.args.model
        if not os.path.exists(model_path):
            print(f"Model not found at {model_path}, using synthetic model")
            model_path = "models/isolation_forest.pkl"
            os.makedirs("models", exist_ok=True)
        
        self.anomaly_detector = OnlineAnomalyDetector(
            model_path=model_path,
            redis_url=self.args.redis
        )
    
    async def run(self):
        """Run all components."""
        self.running = True
        
        # Setup components
        self.setup_anomaly_detection()
        self.setup_feature_extraction()
        self.setup_capture()
        
        # Start API server in background
        api_task = asyncio.create_task(run_api_server(
            host=self.args.api_host,
            port=self.args.api_port
        ))
        
        # Run capture in thread pool
        loop = asyncio.get_event_loop()
        capture_task = loop.run_in_executor(None, self.capture.run)
        
        # Handle shutdown
        def signal_handler():
            print("\nShutting down...")
            self.running = False
            if self.capture:
                self.capture.cleanup()
            if self.feature_engine:
                self.feature_engine.flush_all()
            api_task.cancel()
            capture_task.cancel()
        
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, signal_handler)
            except NotImplementedError:
                # Windows doesn't support add_signal_handler
                pass
        
        try:
            await asyncio.gather(api_task, capture_task)
        except asyncio.CancelledError:
            pass
        finally:
            signal_handler()
        
        print("Shutdown complete")


def main():
    parser = argparse.ArgumentParser(
        description="Live Cyber-Threat Visualizer & Packet Sniffer"
    )
    parser.add_argument(
        "-i", "--interface", 
        default="any", 
        help="Network interface (default: auto-detect, use 'any' for automatic)"
    )
    parser.add_argument(
        "-p", "--ebpf-program",
        default="capture/ebpf/packet_filter.c",
        help="eBPF program path"
    )
    parser.add_argument(
        "-r", "--redis",
        default="redis://localhost:6379",
        help="Redis URL"
    )
    parser.add_argument(
        "-m", "--model",
        default="models/isolation_forest.pkl",
        help="Anomaly detection model path"
    )
    parser.add_argument(
        "--fallback",
        action="store_true",
        help="Force libpcap fallback"
    )
    parser.add_argument(
        "--api-host",
        default="127.0.0.1",
        help="API server host"
    )
    parser.add_argument(
        "--api-port",
        type=int,
        default=8000,
        help="API server port"
    )
    parser.add_argument(
        "--train",
        action="store_true",
        help="Train new model and exit"
    )
    parser.add_argument(
        "--capture-only",
        action="store_true",
        help="Run only packet capture (no API server)"
    )
    parser.add_argument(
        "--api-only",
        action="store_true",
        help="Run only API server (no packet capture)"
    )
    
    args = parser.parse_args()
    
    if args.train:
        print("Training new model...")
        from model.anomaly_detector import ModelTrainer, generate_synthetic_data
        X, y = generate_synthetic_data(50000, 0.02)
        trainer = ModelTrainer("", "models")
        ensemble = trainer.train_ensemble(X, y)
        print("Training complete!")
        return
    
    if args.api_only:
        print("Starting API server only...")
        import uvicorn
        from streaming.stream_manager import create_app
        
        app = create_app()
        
        uvicorn.run(app, host=args.api_host, port=args.api_port, log_level="info")
        return
    
    if args.capture_only:
        print("Running packet capture only...")
        # Setup components without API
        visualizer = CyberThreatVisualizer(args)
        visualizer.setup_anomaly_detection()
        visualizer.setup_feature_extraction()
        visualizer.setup_capture()
        
        def signal_handler():
            print("\nShutting down...")
            visualizer.running = False
            if visualizer.capture:
                visualizer.capture.cleanup()
            if visualizer.feature_engine:
                visualizer.feature_engine.flush_all()
        
        import signal
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                signal.signal(sig, lambda s, f: signal_handler())
            except:
                pass
        
        try:
            visualizer.capture.run()
        except KeyboardInterrupt:
            pass
        finally:
            signal_handler()
        return
    
    # Check for admin/root (needed for eBPF on Linux, Npcap on Windows)
    is_windows = sys.platform == "win32"
    is_admin = False
    
    if is_windows:
        try:
            import ctypes
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        except:
            is_admin = False
    else:
        try:
            is_admin = os.geteuid() == 0
        except:
            is_admin = False
    
    if not is_admin and not args.fallback and not is_windows:
        print("Warning: Not running as root. eBPF requires root privileges.")
        print("Use --fallback for libpcap mode or run with sudo.")
        sys.exit(1)
    elif not is_admin and is_windows and not args.fallback:
        print("Warning: Not running as Administrator. Packet capture requires Admin/Npcap.")
        print("Auto-enabling fallback mode for Windows.")
        args.fallback = True
    
    visualizer = CyberThreatVisualizer(args)
    
    try:
        asyncio.run(visualizer.run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()