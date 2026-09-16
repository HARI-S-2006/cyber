#!/usr/bin/env python3
"""Brute force attack simulation for testing the Cyber Threat Visualizer."""
import asyncio
import random
import time
import argparse
import sys
import os
from scapy.all import IP, TCP, UDP, Raw, send
from scapy.layers.inet import TCP, UDP

from backend.utils.redis_client import redis_manager
from backend.config import settings


class BruteForceSimulator:
    """Simulates brute force attacks on various services."""
    
    # Common credentials for simulation
    USERNAMES = [
        'admin', 'administrator', 'root', 'user', 'test', 'guest',
        'ubuntu', 'centos', 'debian', 'ec2-user', 'pi', 'oracle',
        'postgres', 'mysql', 'oracle', 'ftp', 'webmaster', 'admin123',
        'administrator', 'root123', 'admin1', 'admin2', 'user1', 'test'
    ]
    
    PASSWORDS = [
        'password', '123456', 'password123', 'admin', 'admin123',
        'root', 'root123', 'toor', 'pass', 'pass123', 'admin1',
        'welcome', 'welcome123', 'changeme', 'secret', 'password1',
        'qwerty', 'qwerty123', 'abc123', '12345678', 'letmein',
        'monkey', 'dragon', 'master', 'shadow', 'superman'
    ]
    
    SERVICES = {
        'ssh': {'port': 22, 'protocol': 'TCP', 'banner': 'SSH-2.0-OpenSSH_8.2p1'},
        'ftp': {'port': 21, 'protocol': 'TCP', 'banner': '220 FTP Server ready'},
        'telnet': {'port': 23, 'protocol': 'TCP', 'banner': 'Login: '},
        'rdp': {'port': 3389, 'protocol': 'TCP', 'banner': ''},
        'mysql': {'port': 3306, 'protocol': 'TCP', 'banner': ''},
        'postgres': {'port': 5432, 'protocol': 'TCP', 'banner': ''},
        'redis': {'port': 6379, 'protocol': 'TCP', 'banner': ''},
        'mongodb': {'port': 27017, 'protocol': 'TCP', 'banner': ''},
        'vnc': {'port': 5900, 'protocol': 'TCP', 'banner': 'RFB 003.008'},
        'smb': {'port': 445, 'protocol': 'TCP', 'banner': ''},
        'snmp': {'port': 161, 'protocol': 'UDP', 'banner': ''},
    }
    
    def __init__(self, target_ip: str, service: str = 'ssh', source_ips: list = None):
        self.target_ip = target_ip
        self.service = service.lower()
        self.service_info = self.SERVICES.get(self.service, self.SERVICES['ssh'])
        self.target_port = self.service_info['port']
        self.protocol = self.service_info['protocol']
        self.banner = self.service_info['banner']
        self.source_ips = source_ips or [
            f"192.168.{random.randint(1, 255)}.{random.randint(1, 254)}"
            for _ in range(10)
        ]
        self.attempts = 0
        self.successful = 0
    
    async def simulate_ssh_bruteforce(self, attempts: int = 100, rate: int = 10) -> dict:
        """Simulate SSH brute force attack."""
        print(f"[+] Starting SSH brute force on {self.target_ip}:{self.target_port}")
        print(f"    Attempts: {attempts} | Rate: {rate}/sec")
        
        for i in range(attempts):
            src_ip = random.choice(self.source_ips)
            src_port = random.randint(1024, 65535)
            username = random.choice(self.USERNAMES)
            password = random.choice(self.PASSWORDS)
            
            # Simulate SSH connection attempt
            # SYN
            syn = IP(src=self.source_ips[0], dst=self.target_ip) / \
                  TCP(sport=random.randint(1024, 65535), dport=self.target_port, flags='S')
            send(syn, verbose=0)
            
            # Small delay to simulate handshake
            await asyncio.sleep(0.01)
            
            # SSH protocol exchange (simplified)
            # In reality, this would be the SSH protocol exchange
            pkt = IP(src=self.source_ips[0], dst=self.target_ip) / \
                  TCP(sport=random.randint(1024, 65535), dport=self.target_port, flags='PA') / \
                  Raw(load=f'SSH_AUTH_REQUEST {username} {password}\r\n')
            send(pkt, verbose=0)
            
            self.attempts += 1
            
            # Simulate success (1% chance for demo)
            if random.random() < 0.01:
                success = True
                self.successful += 1
                print(f"    [!] SUCCESS: {username}:{password}")
            else:
                # Simulate failure response
                fail_pkt = IP(src=self.source_ips[0], dst=self.target_ip) / \
                          TCP(sport=random.randint(1024, 65535), dport=self.target_port, flags='R')
                send(fail_pkt, verbose=0)
                success = False
            
            # Rate limiting
            await asyncio.sleep(1.0 / rate)
            
            if self.attempts >= attempts:
                break
        
        return {
            'total_attempts': self.attempts,
            'successful': self.successful,
            'success_rate': self.successful / max(1, self.attempts)
        }
    
    async def simulate_ftp_bruteforce(self, attempts: int = 100, rate: int = 10) -> dict:
        """Simulate FTP brute force attack."""
        print(f"[+] Starting FTP brute force on {self.target_ip}:{self.target_port}")
        
        self.attempts = 0
        self.successful = 0
        
        for i in range(attempts):
            src_ip = random.choice(self.source_ips)
            src_port = random.randint(1024, 65535)
            username = random.choice(self.USERNAMES)
            password = random.choice(self.PASSWORDS)
            
            # FTP connection simulation
            # SYN
            syn = IP(src=self.source_ips[0], dst=self.target_ip) / \
                  TCP(sport=random.randint(1024, 65535), dport=self.target_port, flags='S')
            send(syn, verbose=0)
            
            await asyncio.sleep(0.01)
            
            # FTP USER command
            user_pkt = IP(src=self.source_ips[0], dst=self.target_ip) / \
                       TCP(sport=random.randint(1024, 65535), dport=self.target_port, flags='PA') / \
                       Raw(load=f'USER {username}\r\n')
            send(user_pkt, verbose=0)
            
            await asyncio.sleep(0.01)
            
            # FTP PASS command
            pass_pkt = IP(src=self.source_ips[0], dst=self.target_ip) / \
                       TCP(sport=random.randint(1024, 65535), dport=self.target_port, flags='PA') / \
                       Raw(load=f'PASS {password}\r\n')
            send(pass_pkt, verbose=0)
            
            self.attempts += 1
            
            # 1% success rate for demo
            if random.random() < 0.01:
                print(f"    [!] FTP SUCCESS: {username}:{password}")
                self.successful += 1
            else:
                # Failed login - simulate 530 response
                fail_pkt = IP(src=self.source_ips[0], dst=self.target_ip) / \
                          TCP(sport=random.randint(1024, 65535), dport=self.target_port, flags='R')
                send(fail_pkt, verbose=0)
            
            await asyncio.sleep(1.0 / rate)
        
        return {
            'total_attempts': self.attempts,
            'successful': self.successful,
            'success_rate': self.successful / max(1, self.attempts)
        }
    
    async def simulate_rdp_bruteforce(self, attempts: int = 50, rate: int = 5) -> dict:
        """Simulate RDP brute force attack."""
        print(f"[+] Starting RDP brute force on {self.target_ip}:{self.target_port}")
        
        self.attempts = 0
        self.successful = 0
        
        for i in range(attempts):
            src_ip = random.choice(self.source_ips)
            src_port = random.randint(1024, 65535)
            username = random.choice(self.USERNAMES)
            password = random.choice(self.PASSWORDS)
            
            # RDP uses TCP 3389
            # Simulate RDP connection attempt
            # SYN
            syn = IP(src=self.source_ips[0], dst=self.target_ip) / \
                  TCP(sport=random.randint(1024, 65535), dport=self.target_port, flags='S')
            send(syn, verbose=0)
            
            await asyncio.sleep(0.01)
            
            # RDP MCS Connect Initial with credentials
            # Simplified - just sending a packet that looks like RDP auth
            auth_pkt = IP(src=self.source_ips[0], dst=self.target_ip) / \
                       TCP(sport=random.randint(1024, 65535), dport=self.target_port, flags='PA') / \
                       Raw(load=f'RDP_AUTH {username} {password}\r\n')
            send(auth_pkt, verbose=0)
            
            self.attempts += 1
            
            # 0.5% success rate for RDP (harder)
            if random.random() < 0.005:
                print(f"    [!] RDP SUCCESS: {username}:{password}")
                self.successful += 1
            else:
                fail_pkt = IP(src=self.source_ips[0], dst=self.target_ip) / \
                          TCP(sport=random.randint(1024, 65535), dport=self.target_port, flags='R')
                send(fail_pkt, verbose=0)
            
            await asyncio.sleep(1.0 / rate)
        
        return {
            'total_attempts': self.attempts,
            'successful': self.successful,
            'success_rate': self.successful / max(1, self.attempts)
        }
    
    async def simulate_database_bruteforce(self, attempts: int = 100, rate: int = 10) -> dict:
        """Simulate database brute force (MySQL, PostgreSQL, etc.)."""
        print(f"[+] Starting {self.service.upper()} brute force on {self.target_ip}:{self.target_port}")
        
        self.attempts = 0
        self.successful = 0
        
        for i in range(attempts):
            src_ip = random.choice(self.source_ips)
            src_port = random.randint(1024, 65535)
            username = random.choice(self.USERNAMES)
            password = random.choice(self.PASSWORDS)
            
            # TCP connection
            syn = IP(src=self.source_ips[0], dst=self.target_ip) / \
                  TCP(sport=random.randint(1024, 65535), dport=self.target_port, flags='S')
            send(syn, verbose=0)
            
            await asyncio.sleep(0.01)
            
            # Database auth packet (simplified)
            if self.service == 'mysql':
                auth_data = f'\x00{username}\x00{password}'
            elif self.service == 'postgres':
                auth_data = f'password\x00{username}\x00{password}\x00'
            elif self.service == 'redis':
                auth_data = f'AUTH {password}\r\n'
            elif self.service == 'mongodb':
                auth_data = f'{{authenticate: 1, user: "{username}", pwd: "{password}"}}'
            else:
                auth_data = f'{username}:{password}'
            
            auth_pkt = IP(src=self.source_ips[0], dst=self.target_ip) / \
                       TCP(sport=random.randint(1024, 65535), dport=self.target_port, flags='PA') / \
                       Raw(load=auth_data)
            send(auth_pkt, verbose=0)
            
            self.attempts += 1
            
            if random.random() < 0.01:
                print(f"    [!] {self.service.upper()} SUCCESS: {username}:{password}")
                self.successful += 1
            else:
                fail_pkt = IP(src=self.source_ips[0], dst=self.target_ip) / \
                          TCP(sport=random.randint(1024, 65535), dport=self.target_port, flags='R')
                send(fail_pkt, verbose=0)
            
            await asyncio.sleep(1.0 / rate)
        
        return {
            'total_attempts': self.attempts,
            'successful': self.successful,
            'success_rate': self.successful / max(1, self.attempts)
        }


def is_admin() -> bool:
    """Check if running with admin/root privileges."""
    try:
        if sys.platform == "win32":
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin()
        else:
            return os.geteuid() == 0
    except:
        return False


async def main():
    parser = argparse.ArgumentParser(description='Brute Force Attack Simulator')
    parser.add_argument('--target', required=True, help='Target IP address')
    parser.add_argument('--service', choices=['ssh', 'ftp', 'rdp', 'mysql', 'postgres', 'redis', 'mongodb', 'all'],
                       default='ssh', help='Service to attack')
    parser.add_argument('--attempts', type=int, default=100, help='Number of login attempts')
    parser.add_argument('--rate', type=int, default=10, help='Attempts per second')
    parser.add_argument('--source-ip', help='Source IP (for spoofing)')
    
    args = parser.parse_args()
    
    if not is_admin():
        print("[!] Warning: Packet sending requires Administrator/root privileges")
        print("    On Windows: Run PowerShell as Administrator")
        print("    On Linux: Run with sudo")
        return
    
    simulator = BruteForceSimulator(args.target, args.service)
    
    print(f"[+] Target: {args.target}")
    print(f"[+] Service: {args.service}")
    print(f"[+] Attempts: {args.attempts}")
    print(f"[+] Rate: {args.rate}/sec")
    
    try:
        if args.service == 'ssh':
            result = await simulator.simulate_ssh_bruteforce(args.attempts, args.rate)
        elif args.service == 'ftp':
            result = await simulator.simulate_ftp_bruteforce(args.attempts, args.rate)
        elif args.service == 'rdp':
            result = await simulator.simulate_rdp_bruteforce(args.attempts, args.rate)
        elif args.service in ['mysql', 'postgres', 'redis', 'mongodb']:
            result = await simulator.simulate_database_bruteforce(args.attempts, args.rate)
        elif args.service == 'all':
            print("[+] Running all brute force simulations...")
            for svc in ['ssh', 'ftp', 'rdp', 'mysql']:
                simulator = BruteForceSimulator(args.target, svc)
                if svc == 'ssh':
                    result = await simulator.simulate_ssh_bruteforce(args.attempts // 4, args.rate)
                elif svc == 'ftp':
                    result = await simulator.simulate_ftp_bruteforce(args.attempts // 4, args.rate)
                elif svc == 'rdp':
                    result = await simulator.simulate_rdp_bruteforce(args.attempts // 4, args.rate)
                else:
                    result = await simulator.simulate_database_bruteforce(args.attempts // 4, args.rate)
                print(f"  {svc.upper()}: {result['total_attempts']} attempts, {result['successful']} successful")
            return
        else:
            print(f"[!] Unknown service: {args.service}")
            return
        
        print(f"\n[+] Attack completed:")
        print(f"    Total attempts: {result['total_attempts']}")
        print(f"    Successful: {result['successful']}")
        print(f"    Success rate: {result['success_rate']:.2%}")
        
    except KeyboardInterrupt:
        print("\n[!] Interrupted by user")
    except Exception as e:
        print(f"[!] Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())