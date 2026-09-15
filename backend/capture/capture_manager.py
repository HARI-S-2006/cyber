#!/usr/bin/env python3
"""
eBPF Packet Capture Loader
Loads and manages the XDP eBPF program for high-performance packet capture.
"""

import argparse
import signal
import sys
import time
import json
import threading
from typing import Optional, Callable
from dataclasses import dataclass
from datetime import datetime

try:
    from bcc import BPF
    import ctypes
    BCC_AVAILABLE = True
except ImportError:
    BCC_AVAILABLE = False
    print("Warning: bcc not available. Install with: pip install bcc")

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("Warning: redis not available. Install with: pip install redis")


@dataclass
class PacketMetadata:
    timestamp_ns: int
    src_ip: int
    dst_ip: int
    src_port: int
    dst_port: int
    protocol: int
    tcp_flags: int
    payload_len: int
    payload: bytes
    pkt_len: int
    direction: int


class EBpfPacketCapture:
    def __init__(
        self,
        interface: str,
        ebpf_program_path: str,
        redis_url: str = "redis://localhost:6379",
        ringbuf_size: int = 1 << 24,
        callback: Optional[Callable[[PacketMetadata], None]] = None
    ):
        self.interface = interface
        self.ebpf_program_path = ebpf_program_path
        self.redis_url = redis_url
        self.ringbuf_size = ringbuf_size
        self.callback = callback
        self.bpf: Optional[BPF] = None
        self.redis_client = None
        self.running = False
        self.stats = {
            "packets_received": 0,
            "packets_dropped": 0,
            "errors": 0,
            "start_time": None
        }
        self._lock = threading.Lock()

        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=False, protocol=2)
                self.redis_client.ping()
            except Exception as e:
                print(f"Redis connection failed: {e}")
                self.redis_client = None

    def load_program(self) -> bool:
        if not BCC_AVAILABLE:
            print("BCC not available, cannot load eBPF program")
            return False

        try:
            with open(self.ebpf_program_path, 'r') as f:
                program_text = f.read()

            self.bpf = BPF(text=program_text, cflags=["-w"])
            
            fn = self.bpf.load_func("xdp_packet_filter", BPF.XDP)
            self.bpf.attach_xdp(self.interface, fn, 0)

            print(f"eBPF program loaded and attached to {self.interface}")
            return True
        except Exception as e:
            print(f"Failed to load eBPF program: {e}")
            return False

    def _parse_packet(self, data: bytes) -> Optional[PacketMetadata]:
        if len(data) < 80:
            return None

        meta = PacketMetadata(
            timestamp_ns=int.from_bytes(data[0:8], 'little'),
            src_ip=int.from_bytes(data[8:12], 'little'),
            dst_ip=int.from_bytes(data[12:16], 'little'),
            src_port=int.from_bytes(data[16:18], 'little'),
            dst_port=int.from_bytes(data[18:20], 'little'),
            protocol=data[20],
            tcp_flags=data[21],
            payload_len=int.from_bytes(data[22:24], 'little'),
            payload=data[24:24+min(data[22], 128)],
            pkt_len=int.from_bytes(data[24+128:24+128+4], 'little'),
            direction=data[24+128+4]
        )
        return meta

    def _ip_to_str(self, ip: int) -> str:
        return ".".join(str((ip >> (8 * i)) & 0xFF) for i in [3, 2, 1, 0])

    def _proto_to_str(self, proto: int) -> str:
        return {1: "ICMP", 6: "TCP", 17: "UDP"}.get(proto, str(proto))

    def _tcp_flags_to_str(self, flags: int) -> str:
        flag_names = []
        if flags & 0x01: flag_names.append("FIN")
        if flags & 0x02: flag_names.append("SYN")
        if flags & 0x04: flag_names.append("RST")
        if flags & 0x08: flag_names.append("PSH")
        if flags & 0x10: flag_names.append("ACK")
        if flags & 0x20: flag_names.append("URG")
        return "|".join(flag_names) if flag_names else "NONE"

    def process_packet(self, meta: PacketMetadata):
        with self._lock:
            self.stats["packets_received"] += 1

        if self.callback:
            try:
                self.callback(meta)
            except Exception as e:
                print(f"Callback error: {e}")
                with self._lock:
                    self.stats["errors"] += 1

        if self.redis_client:
            try:
                packet_data = {
                    "timestamp_ns": meta.timestamp_ns,
                    "src_ip": self._ip_to_str(meta.src_ip),
                    "dst_ip": self._ip_to_str(meta.dst_ip),
                    "src_port": meta.src_port,
                    "dst_port": meta.dst_port,
                    "protocol": self._proto_to_str(meta.protocol),
                    "tcp_flags": self._tcp_flags_to_str(meta.tcp_flags),
                    "payload_len": meta.payload_len,
                    "payload_hex": meta.payload.hex(),
                    "pkt_len": meta.pkt_len,
                    "direction": meta.direction
                }
                self.redis_client.xadd("packets:raw", packet_data, maxlen=100000)
            except Exception as e:
                if "unknown command" in str(e).lower():
                    import json
                    self.redis_client.rpush("list:packets:raw", json.dumps(packet_data))
                    self.redis_client.ltrim("list:packets:raw", -100000, -1)
                else:
                    print(f"Redis publish error: {e}")

    def run(self):
        if not self.bpf:
            print("eBPF program not loaded")
            return

        self.running = True
        self.stats["start_time"] = time.time()
        ringbuf = self.bpf["packet_ringbuf"]

        print("Starting packet capture... Press Ctrl+C to stop")

        def signal_handler(sig, frame):
            print("\nShutting down...")
            self.running = False

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        while self.running:
            try:
                data = ringbuf.poll(100)
                if data:
                    meta = self._parse_packet(data)
                    if meta:
                        self.process_packet(meta)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Poll error: {e}")
                with self._lock:
                    self.stats["errors"] += 1

        self.cleanup()

    def cleanup(self):
        if self.bpf:
            try:
                self.bpf.remove_xdp(self.interface, 0)
            except:
                pass
        print("Capture stopped")
        self.print_stats()

    def print_stats(self):
        with self._lock:
            elapsed = time.time() - (self.stats["start_time"] or time.time())
            print(f"\n=== Capture Statistics ===")
            print(f"Duration: {elapsed:.1f}s")
            print(f"Packets received: {self.stats['packets_received']}")
            print(f"Packets dropped: {self.stats['packets_dropped']}")
            print(f"Errors: {self.stats['errors']}")
            print(f"Rate: {self.stats['packets_received']/max(elapsed,1):.1f} pps")


def list_interfaces():
    """List available network interfaces"""
    try:
        from scapy.all import get_if_list
        return get_if_list()
    except ImportError:
        pass
    
    try:
        import psutil
        return list(psutil.net_if_addrs().keys())
    except ImportError:
        pass
    
    # Windows fallback
    if sys.platform == "win32":
        try:
            import wmi
            c = wmi.WMI()
            return [nic.Name for nic in c.Win32_NetworkAdapterConfiguration(IPEnabled=True)]
        except ImportError:
            pass
    
    return []


class LibpcapFallback:
    """Fallback capture using libpcap/scapy for non-Linux or non-root environments"""
    
    def __init__(self, interface: str, callback: Optional[Callable] = None):
        self.interface = interface
        self.callback = callback
        self.running = False
        self._sniff_thread = None
        
        # On Windows, "any" or empty means use default
        if sys.platform == "win32" and interface.lower() in ("any", "", "auto"):
            self.interface = self._get_default_windows_interface()
    
    def _get_default_windows_interface(self) -> str:
        """Get the default active interface on Windows"""
        # First try to get from scapy's conf.iface
        try:
            from scapy.all import conf
            if conf.iface and conf.iface != "eth0":
                return conf.iface
        except:
            pass
        
        # Try to find active non-loopback interface using psutil
        try:
            import psutil
            for name, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family == 2 and not addr.address.startswith("127."):  # AF_INET
                        # Check if this interface exists in scapy's list
                        from scapy.all import get_if_list
                        if name in get_if_list():
                            return name
                        # Also check NPF format
                        for iface in get_if_list():
                            if name.lower() in iface.lower() or iface.lower() in name.lower():
                                return iface
        except:
            pass
        
        # Last resort: return first non-loopback from scapy
        try:
            from scapy.all import get_if_list
            for iface in get_if_list():
                if "loopback" not in iface.lower() and "npf_" in iface.lower():
                    return iface
        except:
            pass
        
        # Final fallback
        return "Ethernet"
        
    def cleanup(self):
        """Stop the capture gracefully"""
        self.running = False
        # The sniff() uses stop_filter=lambda x: not self.running
        # So setting running=False will cause it to exit on next packet
        # Give it a moment to stop
        import time
        time.sleep(0.5)
        
    def run(self):
        try:
            from scapy.all import sniff, IP, TCP, UDP, ICMP, Raw
        except ImportError:
            print("Scapy not available for fallback capture")
            return

        self.running = True
        
        def process_packet(pkt):
            if not self.running:
                return True
            
            if IP not in pkt:
                return
            
            ip_layer = pkt[IP]
            meta = PacketMetadata(
                timestamp_ns=int(pkt.time * 1e9),
                src_ip=int.from_bytes(ip_layer.src.encode(), 'big') if False else 
                       sum(int(octet) << (8 * (3-i)) for i, octet in enumerate(ip_layer.src.split('.'))),
                dst_ip=sum(int(octet) << (8 * (3-i)) for i, octet in enumerate(ip_layer.dst.split('.'))),
                src_port=0,
                dst_port=0,
                protocol=ip_layer.proto,
                tcp_flags=0,
                payload_len=0,
                payload=b"",
                pkt_len=len(pkt),
                direction=0
            )
            
            if TCP in pkt:
                tcp = pkt[TCP]
                meta.src_port = tcp.sport
                meta.dst_port = tcp.dport
                meta.tcp_flags = tcp.flags
                if Raw in pkt:
                    payload = bytes(pkt[Raw])
                    meta.payload_len = min(len(payload), 128)
                    meta.payload = payload[:128]
                    
            elif UDP in pkt:
                udp = pkt[UDP]
                meta.src_port = udp.sport
                meta.dst_port = udp.dport
                if Raw in pkt:
                    payload = bytes(pkt[Raw])
                    meta.payload_len = min(len(payload), 128)
                    meta.payload = payload[:128]
                    
            elif ICMP in pkt:
                meta.src_port = 0
                meta.dst_port = 0
            
            if self.callback:
                self.callback(meta)
                
        print(f"Starting libpcap fallback on {self.interface}")
        sniff(iface=self.interface, prn=process_packet, stop_filter=lambda x: not self.running, store=0)


def main():
    parser = argparse.ArgumentParser(description="eBPF Packet Capture for Cyber Threat Visualizer")
    parser.add_argument("-i", "--interface", default="any", help="Network interface (default: auto-detect)")
    parser.add_argument("-p", "--program", default="../capture/ebpf/packet_filter.c", help="eBPF program path")
    parser.add_argument("-r", "--redis", default="redis://localhost:6379", help="Redis URL")
    parser.add_argument("--fallback", action="store_true", help="Use libpcap fallback")
    parser.add_argument("--list-interfaces", action="store_true", help="List available interfaces and exit")
    args = parser.parse_args()
    
    if args.list_interfaces:
        print("Available interfaces:")
        for iface in list_interfaces():
            print(f"  {iface}")
        return

    def packet_handler(meta: PacketMetadata):
        print(f"[{datetime.fromtimestamp(meta.timestamp_ns/1e9).strftime('%H:%M:%S.%f')[:-3]}] "
              f"{meta.src_ip}:{meta.src_port} -> {meta.dst_ip}:{meta.dst_port} "
              f"[{meta.protocol}] Flags:{meta.tcp_flags} Len:{meta.pkt_len}")

    if args.fallback or not BCC_AVAILABLE:
        capture = LibpcapFallback(args.interface, packet_handler)
    else:
        capture = EBpfPacketCapture(
            interface=args.interface,
            ebpf_program_path=args.program,
            redis_url=args.redis,
            callback=packet_handler
        )
        if not capture.load_program():
            print("Falling back to libpcap...")
            capture = LibpcapFallback(args.interface, packet_handler)

    capture.run()


if __name__ == "__main__":
    main()