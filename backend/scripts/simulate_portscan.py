#!/usr/bin/env python3
"""Port scan simulation for testing the Cyber Threat Visualizer."""
import asyncio
import random
import time
import argparse
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scapy.all import IP, TCP, UDP, ICMP, Raw, send
from scapy.layers.inet import TCP, UDP, ICMP


class PortScanSimulator:
    """Simulates various port scanning techniques."""
    
    def __init__(self, target_ip: str, source_ips: list = None):
        self.target_ip = target_ip
        self.source_ips = source_ips or [
            f"192.168.{random.randint(1, 255)}.{random.randint(1, 254)}"
            for _ in range(20)
        ]
    
    async def syn_scan(self, ports: list, rate: int = 100) -> int:
        """SYN scan (half-open scan)."""
        print(f"[+] Starting SYN scan on {self.target_ip}")
        print(f"    Ports: {len(ports)} | Rate: {rate} pps")
        
        packet_count = 0
        interval = 1.0 / rate
        
        for port in random.sample(ports, len(ports)):
            src_ip = random.choice(self.source_ips)
            src_port = random.randint(1024, 65535)
            
            # SYN packet
            pkt = IP(src=src_ip, dst=self.target_ip) / TCP(sport=src_port, dport=port, flags='S')
            send(pkt, verbose=0)
            
            packet_count += 1
            await asyncio.sleep(interval)
        
        return packet_count
    
    async def connect_scan(self, ports: list, rate: int = 50) -> int:
        """Full TCP connect scan (completes handshake)."""
        print(f"[+] Starting Connect scan on {self.target_ip}")
        
        packet_count = 0
        for port in random.sample(ports, len(ports)):
            src_ip = random.choice(self.source_ips)
            src_port = random.randint(1024, 65535)
            
            # SYN
            syn = IP(src=src_ip, dst=self.target_ip) / TCP(sport=src_port, dport=port, flags='S')
            send(syn, verbose=0)
            
            await asyncio.sleep(0.01)
            
            # ACK
            ack = IP(src=src_ip, dst=self.target_ip) / TCP(sport=src_port, dport=port, flags='A')
            send(ack, verbose=0)
            
            await asyncio.sleep(0.01)
            
            # FIN to close
            await asyncio.sleep(0.01)
            fin = IP(src=src_ip, dst=self.target_ip) / TCP(sport=src_port, dport=port, flags='FA')
            send(fin, verbose=0)
            
            packet_count += 3
            await asyncio.sleep(1.0 / rate)
        
        return packet_count
    
    async def udp_scan(self, ports: list, rate: int = 20) -> int:
        """UDP scan (fire and forget)."""
        print(f"[+] Starting UDP scan on {self.target_ip}")
        
        packet_count = 0
        for port in random.sample(ports, len(ports)):
            src_ip = random.choice(self.source_ips)
            src_port = random.randint(1024, 65535)
            
            payload = bytes([random.randint(0, 255) for _ in range(random.randint(64, 512))])
            pkt = IP(src=src_ip, dst=self.target_ip) / UDP(sport=src_port, dport=port) / Raw(load=payload)
            send(pkt, verbose=0)
            
            packet_count += 1
            await asyncio.sleep(1.0 / rate)
        
        return packet_count
    
    async def xmas_scan(self, ports: list, rate: int = 50) -> int:
        """Xmas scan (FIN, URG, PSH flags)."""
        print(f"[+] Starting Xmas scan on {self.target_ip}")
        
        packet_count = 0
        for port in random.sample(ports, len(ports)):
            src_ip = random.choice(self.source_ips)
            src_port = random.randint(1024, 65535)
            
            pkt = IP(src=src_ip, dst=self.target_ip) / TCP(sport=src_port, dport=port, flags='FPU')
            send(pkt, verbose=0)
            
            packet_count += 1
            await asyncio.sleep(1.0 / rate)
        
        return packet_count
    
    async def fin_scan(self, ports: list, rate: int = 50) -> int:
        """FIN scan."""
        print(f"[+] Starting FIN scan on {self.target_ip}")
        
        packet_count = 0
        for port in random.sample(ports, len(ports)):
            src_ip = random.choice(self.source_ips)
            src_port = random.randint(1024, 65535)
            
            pkt = IP(src=src_ip, dst=self.target_ip) / TCP(sport=src_port, dport=port, flags='F')
            send(pkt, verbose=0)
            
            packet_count += 1
            await asyncio.sleep(1.0 / rate)
        
        return packet_count
    
    async def null_scan(self, ports: list, rate: int = 50) -> int:
        """NULL scan (no flags)."""
        print(f"[+] Starting NULL scan on {self.target_ip}")
        
        packet_count = 0
        for port in random.sample(ports, len(ports)):
            src_ip = random.choice(self.source_ips)
            src_port = random.randint(1024, 65535)
            
            pkt = IP(src=src_ip, dst=self.target_ip) / TCP(sport=src_port, dport=port, flags=0)
            send(pkt, verbose=0)
            
            packet_count += 1
            await asyncio.sleep(1.0 / rate)
        
        return packet_count
    
    async def version_scan(self, ports: list, rate: int = 30) -> int:
        """Version detection scan (banner grabbing)."""
        print(f"[+] Starting Version scan on {self.target_ip}")
        
        packet_count = 0
        for port in random.sample(ports, len(ports)):
            src_ip = random.choice(self.source_ips)
            src_port = random.randint(1024, 65535)
            
            # SYN
            syn = IP(src=src_ip, dst=self.target_ip) / TCP(sport=src_port, dport=port, flags='S')
            send(syn, verbose=0)
            
            await asyncio.sleep(0.05)
            
            # ACK + PSH with probe
            ack = IP(src=src_ip, dst=self.target_ip) / TCP(sport=src_port, dport=port, flags='PA') / Raw(load=b'HEAD / HTTP/1.0\r\n\r\n')
            send(ack, verbose=0)
            
            packet_count += 2
            await asyncio.sleep(1.0 / rate)
        
        return packet_count


async def main():
    parser = argparse.ArgumentParser(description='Port Scan Simulator for Cyber Threat Visualizer')
    parser.add_argument('--target', required=True, help='Target IP address')
    parser.add_argument('--ports', default='1-1000', help='Port range (e.g., 1-1000, 80,443,22)')
    parser.add_argument('--type', choices=['syn', 'connect', 'udp', 'xmas', 'fin', 'null', 'version', 'all'], default='syn', help='Scan type')
    parser.add_argument('--rate', type=int, default=100, help='Packets per second')
    parser.add_argument('--source-ip', help='Source IP (for spoofing)')
    
    args = parser.parse_args()
    
    # Parse ports
    ports = []
    for part in args.ports.split(','):
        if '-' in part:
            start, end = map(int, part.split('-'))
            ports.extend(range(start, end + 1))
        else:
            ports.append(int(part))
    
    # Remove duplicates and sort
    ports = sorted(set(ports))
    
    simulator = PortScanSimulator(args.target)
    
    if args.source_ip:
        simulator.source_ips = [args.source_ip]
    
    print(f"[+] Target: {args.target}")
    print(f"[+] Ports: {len(ports)} ({min(ports)}-{max(ports)})")
    print(f"[+] Scan type: {args.type}")
    print(f"[+] Rate: {args.rate} pps")
    
    try:
        total_packets = 0
        
        if args.type in ['syn', 'all']:
            total_packets += await simulator.syn_scan(ports, args.rate)
        
        if args.type in ['connect', 'all']:
            total_packets += await simulator.connect_scan(ports, args.rate)
        
        if args.type in ['udp', 'all']:
            total_packets += await simulator.udp_scan(ports, min(args.rate, 20))
        
        if args.type in ['xmas', 'all']:
            total_packets += await simulator.xmas_scan(ports, args.rate)
        
        if args.type in ['fin', 'all']:
            total_packets += await simulator.fin_scan(ports, args.rate)
        
        if args.type in ['null', 'all']:
            total_packets += await simulator.null_scan(ports, args.rate)
        
        if args.type in ['version', 'all']:
            total_packets += await simulator.version_scan(ports, min(args.rate, 30))
        
        print(f"\n[+] Scan completed. Total packets sent: {total_packets}")
        
    except KeyboardInterrupt:
        print("\n[!] Interrupted by user")
    except Exception as e:
        print(f"[!] Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())