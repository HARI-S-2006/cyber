import { useStore } from '../../hooks/useStore'
import { cn } from '../../utils/cn'

export function TerminalLog() {
  const { packets } = useStore()
  
  const logEntries = packets.slice(0, 20).map((p, i) => ({
    id: i,
    timestamp: p.start_time,
    src: `${p.src_ip}:${p.src_port}`,
    dst: `${p.dst_ip}:${p.dst_port}`,
    protocol: p.protocol,
    size: p.length,
    anomaly: p.anomaly,
    threat_type: p.threat_type,
  }))
  
  const formatTime = (ts: number) => new Date(ts * 1000).toLocaleTimeString()
  
  return (
    <div className="flex-1 overflow-hidden flex flex-col">
      <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar">
        <div className="space-y-1 p-2">
          {logEntries.length === 0 ? (
            <div className="text-cyber-textDim text-center py-8 text-xs">
              WAITING FOR TRAFFIC...
            </div>
          ) : (
            logEntries.map((entry) => (
              <div
                key={entry.id}
                className={cn(
                  'log-entry font-mono text-xs',
                  entry.anomaly && 'threat',
                  entry.threat_type && entry.threat_type !== 'UNKNOWN' && 'threat'
                )}
              >
                <span className="text-cyber-primary">[{formatTime(entry.timestamp)}]</span>
                <span className="text-cyber-textDim mx-1">|</span>
                <span className="text-cyber-primary">{entry.src}</span>
                <span className="text-cyber-textDim">→</span>
                <span className="text-cyber-secondary">{entry.dst}</span>
                <span className="text-cyber-textDim mx-1">|</span>
                <span className={cn(
                  'badge badge-xs',
                  entry.protocol === 'TCP' && 'badge-primary',
                  entry.protocol === 'UDP' && 'badge-warning',
                  entry.protocol === 'ICMP' && 'badge-info'
                )}>
                  {entry.protocol}
                </span>
                <span className="text-cyber-textDim mx-1">|</span>
                <span className="text-cyber-textDim">{entry.size}B</span>
                {entry.anomaly && (
                  <>
                    <span className="text-cyber-textDim mx-1">|</span>
                    <span className="badge badge-danger">{entry.threat_type || 'ANOMALY'}</span>
                  </>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}

function formatTime(ts: number): string {
  return new Date(ts * 1000).toLocaleTimeString()
}