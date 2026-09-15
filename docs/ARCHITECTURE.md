# Live Cyber-Threat Visualizer & Packet Sniffer - Architecture

## System Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌────────────────────┐     ┌─────────────────────┐
│  Network NIC    │────▶│  eBPF / libpcap  │────▶│  Feature Extraction │────▶│  Anomaly Detection  │
│  (Promiscuous)  │     │  Kernel Filter   │     │  Engine (Python)   │     │  (Lightweight ML)   │
└─────────────────┘     └──────────────────┘     └────────────────────┘     └──────────┬──────────┘
                                                                                       │
                                                                                       ▼
┌─────────────────┐     ┌──────────────────┐     ┌────────────────────┐     ┌─────────────────────┐
│  Three.js 3D    │◀────│  WebSocket /     │◀────│  Redis Streams /   │◀────│  Aggregation &      │
│  Globe Visual   │     │  Server-Sent     │     │  Kafka (Optional)  │     │  Enrichment Layer   │
└─────────────────┘     └──────────────────┘     └────────────────────┘     └─────────────────────┘
```

## Component Details

### 1. Packet Capture Layer (C/Python + eBPF)
- **eBPF XDP/TC programs** for kernel-level filtering (Linux)
- **libpcap/WinPcap** fallback for cross-platform support
- Captures: Ethernet, IP, TCP/UDP/ICMP headers + payload (first N bytes)
- Outputs: Raw packets → Ring buffer / shared memory → Python consumer

### 2. Feature Extraction Engine (Python)
- **Flow-based features** (per 5-tuple): duration, packet count, byte count, flags, IAT statistics
- **Packet-level features**: header fields, payload entropy, TLS SNI, DNS queries, HTTP host
- **Behavioral features**: connection frequency, port scan detection, beaconing patterns
- Output: Structured feature vectors (NumPy arrays / Protocol Buffers)

### 3. Anomaly Detection Model
- **Isolation Forest** (unsupervised) for zero-day detection
- **LightGBM/XGBoost** (supervised) for known attack classification
- **Autoencoder** (deep) for payload anomaly detection
- Model served via **ONNX Runtime** for fast inference (<1ms)
- Retraining pipeline: weekly batch + online updates

### 4. Streaming & Aggregation Layer
- **Redis Streams** (primary): Low-latency, consumer groups, persistence
- **Apache Kafka** (optional): High-throughput, replay, multi-consumer
- **Aggregation windows**: Tumbling (1s, 5s, 30s), Session-based
- **Enrichment**: GeoIP, ASN, threat intel (AlienVault OTX, AbuseIPDB)

### 5. API & Real-time Transport
- **FastAPI** (Python): REST + WebSocket endpoints
- **WebSocket**: Live anomaly feed, flow updates, globe sync
- **Server-Sent Events (SSE)**: Fallback for simple dashboards
- **Authentication**: JWT, API keys for multi-tenant

### 6. 3D Visualization Frontend (Three.js + React/Vite)
- **Globe**: WebGL shader-based earth with traffic arcs
- **Layers**: 
  - Connection arcs (source→dest, colored by threat score)
  - Heatmap overlay (attack density)
  - Particle systems (DDoS volume)
  - Cluster markers (botnet C2)
- **Controls**: Time scrubber, filter panel, detail drill-down
- **Performance**: Instanced rendering, LOD, frustum culling

## Data Flow Specifications

### Packet → Feature Vector
```python
# Per-flow feature vector (example)
{
    "flow_id": "src_ip:src_port-dst_ip:dst_port-proto",
    "timestamp": 1699900000.123,
    "duration_ms": 1250,
    "packets_fwd": 45,
    "packets_bwd": 38,
    "bytes_fwd": 52400,
    "bytes_bwd": 48200,
    "iat_mean": 12.4,
    "iat_std": 8.7,
    "tcp_flags": {"SYN": 1, "ACK": 42, "FIN": 1, "RST": 0},
    "payload_entropy": 7.2,
    "tls_sni": "api.example.com",
    "dns_queries": ["cdn.example.com"],
    "http_host": "api.example.com",
    "threat_score": 0.87,
    "labels": ["C2_BEACONING", "DATA_EXFILTRATION"]
}
```

### WebSocket Message Types
```typescript
type WSMessage =
  | { type: "ANOMALY"; payload: AnomalyEvent }
  | { type: "FLOW_UPDATE"; payload: FlowSummary }
  | { type: "GLOBE_SYNC"; payload: GlobeState }
  | { type: "STATS"; payload: DashboardStats }
  | { type: "ALERT"; payload: AlertEvent };
```

## Technology Choices & Justification

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Capture | eBPF (Linux) / libpcap | Kernel-level, zero-copy, programmable |
| Features | Python + Scapy/pyshark | Rich protocol parsing, fast prototyping |
| ML | scikit-learn + ONNX | Model portability, fast inference |
| Streaming | Redis Streams | Sub-ms latency, built-in consumer groups |
| API | FastAPI | Async, auto-docs, WebSocket native |
| Frontend | Three.js + Vite + React | GPU-accelerated, hot reload, ecosystem |
| Deployment | Docker Compose / K8s | Reproducible, scalable |

## Deployment Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Sensor     │     │  Sensor     │     │  Sensor     │
│  (Edge)     │     │  (Edge)     │     │  (Edge)     │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           ▼
              ┌────────────────────────┐
              │  Load Balancer (NGINX) │
              └───────────┬────────────┘
                          ▼
         ┌────────────────┼────────────────┐
         ▼                ▼                ▼
   ┌──────────┐    ┌──────────┐    ┌──────────┐
   │ API Pod  │    │ API Pod  │    │ API Pod  │
   └────┬─────┘    └────┬─────┘    └────┬─────┘
        │               │               │
        └───────────────┼───────────────┘
                        ▼
              ┌─────────────────┐
              │  Redis Cluster  │
              └────────┬────────┘
                       ▼
              ┌─────────────────┐
              │  Frontend CDN   │
              └─────────────────┘
```

## Security Considerations
- **Packet capture**: Requires root/CAP_NET_RAW; run in dedicated namespace
- **Data privacy**: Hash IPs (prefix-preserving), strip payloads after feature extraction
- **Model integrity**: Sign ONNX models, verify checksums at load
- **API**: Rate limiting, input validation, CORS policy
- **Frontend**: CSP headers, no inline scripts, sanitize WebSocket data

## Scalability Targets
- **Packets/sec**: 100K+ per sensor (eBPF), 1M+ aggregated
- **Flows tracked**: 500K concurrent
- **Latency**: Packet→Alert < 500ms (p99)
- **Visualization**: 60 FPS with 10K concurrent arcs