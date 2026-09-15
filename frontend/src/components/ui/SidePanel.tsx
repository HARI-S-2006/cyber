import { useStore } from '../../hooks/useStore'
import { cn } from '../../utils/cn'

export function SidePanel() {
  const { threats, selectedThreat, setSelectedThreat, packets, selectedPacket, setSelectedPacket } = useStore()
  
  return (
    <aside className="w-96 flex flex-col panel border-l border-cyber-panelBorder bg-cyber-bgSecondary">
      <div className="panel-header">
        <h2 className="panel-title">THREAT DETAILS</h2>
      </div>
      
      <div className="flex-1 overflow-auto p-4">
        {selectedThreat ? (
          <ThreatDetailPanel threat={selectedThreat} onClose={() => setSelectedThreat(null)} />
        ) : selectedPacket ? (
          <PacketDetailPanel packet={selectedPacket} onClose={() => setSelectedPacket(null)} />
        ) : (
          <ThreatList threats={threats} onSelect={setSelectedThreat} />
        )}
      </div>
    </aside>
  )
}

function ThreatDetailPanel({ threat, onClose }: { threat: any; onClose: () => void }) {
  const formatTime = (ts: number) => new Date(ts * 1000).toLocaleTimeString()
  
  return (
    <div className="space-y-4 animate-slide-up">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="font-mono text-sm font-bold text-cyber-danger">{threat.threat_type}</h3>
          <p className="text-xs text-cyber-textDim">{formatTime(threat.timestamp)}</p>
        </div>
        <button onClick={onClose} className="text-cyber-textDim hover:text-cyber-danger transition-colors">✕</button>
      </div>
      
      <div className="grid grid-cols-2 gap-3">
        <div className="panel p-3">
          <p className="text-xs text-cyber-textDim">SOURCE</p>
          <p className="font-mono text-sm text-cyber-text">{threat.src_ip}:{threat.src_port}</p>
          <p className="text-xs text-cyber-textDim">{threat.src_country}</p>
        </div>
        <div className="panel p-3">
          <p className="text-xs text-cyber-textDim">TARGET</p>
          <p className="font-mono text-sm text-cyber-text">{threat.dst_ip}:{threat.dst_port}</p>
          <p className="text-xs text-cyber-textDim">{threat.dst_country}</p>
        </div>
        <div className="panel p-3">
          <p className="text-xs text-cyber-textDim">PROTOCOL</p>
          <p className="font-mono text-sm text-cyber-primary">{threat.protocol}</p>
        </div>
        <div className="panel p-3">
          <p className="text-xs text-cyber-textDim">THREAT SCORE</p>
          <p className="font-mono text-xl font-bold text-cyber-danger">{(threat.threat_score * 100).toFixed(1)}%</p>
        </div>
      </div>
      
      <div className="panel p-3">
        <p className="text-xs text-cyber-textDim mb-2">THREAT DETAILS</p>
        <pre className="font-mono text-xs text-cyber-textDim overflow-auto max-h-40">
          {JSON.stringify(threat.details, null, 2)}
        </pre>
      </div>
      
      <div className="flex gap-2">
        <button className="btn-danger flex-1" onClick={() => {}}>BLOCK SOURCE</button>
        <button className="btn-warning flex-1" onClick={() => {}}>INVESTIGATE</button>
      </div>
      
      <button className="btn-ghost w-full mt-2" onClick={onClose}>CLOSE DETAILS</button>
    </div>
  )
}

function PacketDetailPanel({ packet, onClose }: { packet: any; onClose: () => void }) {
  return (
    <div className="space-y-4 animate-slide-up">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="font-mono text-sm font-bold text-cyber-primary">PACKET DETAILS</h3>
          <p className="text-xs text-cyber-textDim">{packet.protocol} • {packet.packet_count} packets</p>
        </div>
        <button onClick={onClose} className="text-cyber-textDim hover:text-cyber-danger">✕</button>
      </div>
      
      <div className="grid grid-cols-2 gap-3">
        <div className="panel p-3"><p className="text-xs text-cyber-textDim">SRC</p><p className="font-mono text-sm">{packet.src_ip}:{packet.src_port}</p></div>
        <div className="panel p-3"><p className="text-xs text-cyber-textDim">DST</p><p className="font-mono text-sm">{packet.dst_ip}:{packet.dst_port}</p></div>
        <div className="panel p-3"><p className="text-xs text-cyber-textDim">PACKETS</p><p className="font-mono text-sm">{packet.packet_count}</p></div>
        <div className="panel p-3"><p className="text-xs text-cyber-textDim">BYTES</p><p className="font-mono text-sm">{formatBytes(packet.byte_count)}</p></div>
        <div className="panel p-3"><p className="text-xs text-cyber-textDim">DURATION</p><p className="font-mono text-sm">{packet.duration.toFixed(2)}s</p></div>
        <div className="panel p-3"><p className="text-xs text-cyber-textDim">AVG SIZE</p><p className="font-mono text-sm">{packet.avg_packet_size.toFixed(0)}B</p></div>
      </div>
      
      <button className="btn-ghost w-full" onClick={onClose}>CLOSE</button>
    </div>
  )
}

function ThreatList({ threats, onSelect }: { threats: any[]; onSelect: (t: any) => void }) {
  if (threats.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-cyber-textDim">
        <div className="text-6xl mb-4">🛡️</div>
        <p className="font-mono text-sm">NO THREATS DETECTED</p>
        <p className="text-xs mt-2">Monitoring network traffic...</p>
      </div>
    )
  }
  
  return (
    <div className="space-y-2 max-h-full overflow-auto">
      {threats.slice(0, 50).map((threat) => (
        <button
          key={threat.id}
          onClick={() => onSelect(threat)}
          className={cn(
            'panel p-3 text-left transition-all duration-150 hover:border-cyber-primary/50',
            threat.threat_score > 0.7 && 'border-l-4 border-l-cyber-danger bg-cyber-danger/5'
          )}
        >
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className={`badge ${threat.threat_score > 0.7 ? 'badge-danger' : 'badge-warning'}`}>
                  {threat.threat_type}
                </span>
                <span className="font-mono text-xs text-cyber-textDim">
                  {(threat.threat_score * 100).toFixed(0)}%
                </span>
              </div>
              <p className="font-mono text-sm text-cyber-text truncate">
                {threat.src_ip}:{threat.src_port} → {threat.dst_ip}:{threat.dst_port}
              </p>
              <p className="text-xs text-cyber-textDim">{threat.src_country} → {threat.dst_country}</p>
            </div>
            <div className="text-right">
              <p className="font-mono text-xs text-cyber-danger font-bold">
                {(threat.threat_score * 100).toFixed(1)}%
              </p>
            </div>
          </div>
        </button>
      ))}
    </div>
  )
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}