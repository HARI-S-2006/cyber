import sys
import time
import json
import random
import uuid
import argparse
import redis

def generate_random_ip():
    return f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}"

def generate_coordinates():
    # Random lat/lon
    return random.uniform(-90, 90), random.uniform(-180, 180)

def main():
    parser = argparse.ArgumentParser(description="Mock DDoS Traffic Generator for Cyber Threat Visualizer UI")
    parser.add_argument("--redis", default="redis://localhost:6379/0", help="Redis URL")
    parser.add_argument("--rate", type=int, default=10, help="Events per second")
    parser.add_argument("--duration", type=int, default=30, help="Duration in seconds")
    parser.add_argument("--type", choices=["syn", "udp", "http"], default="syn", help="Attack type")
    
    args = parser.parse_args()
    
    print(f"Connecting to Redis at {args.redis}...")
    try:
        r = redis.from_url(args.redis, protocol=2)
        r.ping()
        print("Connected to Redis successfully.")
    except Exception as e:
        print(f"Failed to connect to Redis: {e}")
        sys.exit(1)
        
    print(f"Starting {args.type.upper()} flood simulation for {args.duration} seconds at {args.rate} msgs/sec...")
    
    end_time = time.time() + args.duration
    target_ip = "192.168.1.100"
    target_lat, target_lon = 40.7128, -74.0060 # NYC
    
    msg_count = 0
    delay = 1.0 / args.rate
    
    try:
        while time.time() < end_time:
            now = time.time()
            src_ip = generate_random_ip()
            src_lat, src_lon = generate_coordinates()
            
            # Generate Flow Feature
            flow = {
                "flow_id": str(uuid.uuid4()),
                "src_ip": src_ip,
                "dst_ip": target_ip,
                "src_port": random.randint(1024, 65535),
                "dst_port": 80 if args.type == "http" else 443,
                "protocol": "TCP" if args.type in ["syn", "http"] else "UDP",
                "bytes_total": random.randint(40, 1500),
                "start_time": now,
                "length": random.randint(40, 1500)
            }
            r.publish("network:features", json.dumps(flow))
            
            # Generate Threat
            if random.random() > 0.3: # 70% of traffic is flagged as anomalous
                threat = {
                    "anomaly": True,
                    "threat_type": f"{args.type.upper()}_FLOOD",
                    "threat_score": random.uniform(0.7, 0.99),
                    "threat_level": "HIGH" if random.random() > 0.1 else "CRITICAL",
                    "src_ip": src_ip,
                    "dst_ip": target_ip,
                    "src_lat": src_lat,
                    "src_lon": src_lon,
                    "dst_lat": target_lat,
                    "dst_lon": target_lon,
                    "timestamp": now,
                    "features": flow
                }
                r.publish("network:threats", json.dumps(threat))
            
            # Generate Stats update occasionally
            if msg_count % 10 == 0:
                stats = {
                    "packets_per_sec": args.rate,
                    "bytes_per_sec": args.rate * 500,
                    "active_flows": random.randint(100, 500),
                    "timestamp": now
                }
                r.publish("network:stats", json.dumps(stats))
                
            msg_count += 1
            time.sleep(delay)
            
    except KeyboardInterrupt:
        print("\nSimulation stopped by user.")
        
    print(f"\nSimulation complete. Sent {msg_count} events.")

if __name__ == "__main__":
    main()
