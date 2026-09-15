import { useStore } from '../../hooks/useStore'
import { cn } from '../../utils/cn'

export function SystemStatus() {
  const { stats, connected } = useStore()
  
  const metrics = [
    { label: 'PKTS/SEC', value: stats?.packets_per_sec?.toFixed(1) || '0', unit: '', color: 'cyber-primary' },
    { label: 'TOTAL PKTS', value: stats?.total_packets?.toLocaleString() || '0', unit: '', color: 'cyber-secondary' },
    { label: 'ACTIVE FLOWS', value: stats?.active_flows?.toLocaleString() || '0', unit: '', color: 'cyber-info' },
    { label: 'THREATS', value: stats?.threats_detected?.toLocaleString() || '0', unit: '', color: 'cyber-danger' },
    { label: 'ANOMALY RATE', value: `${(stats?.anomaly_rate * 100 || 0).toFixed(2)}%`, unit: '', color: 'cyber-warning' },
    { label: 'UPTIME', value: formatUptime(stats?.uptime_seconds || 0), unit: '', color: 'cyber-primary' },
  ]
  
  return (
    <div className="flex flex-wrap items-center justify-between gap-4">
      <div className="flex items-center gap-4">
        <span className={`status-indicator ${connected ? 'status-online' : 'status-danger'}`}>
          {connected ? 'SYSTEM ONLINE' : 'SYSTEM OFFLINE'}
        </span>
      </div>
      
      <div className="flex-1 flex items-center justify-center gap-6">
        {metrics.map((m, i) => (
          <div key={m.label} className="flex items-center gap-2">
            <span className="text-xs text-cyber-textDim">{m.label}</span>
            <span className={cn('font-mono text-lg font-bold', `text-${m.color}`)}>
              {m.value}
            </span>
          </div>
        ))}
      </div>
      
      <div className="flex items-center gap-4">
        <button className="btn-ghost px-3 py-1 text-xs">EXPORT LOG</button>
        <button className="btn-warning px-3 py-1 text-xs">CLEAR THREATS</button>
      </div>
    </div>
  )
}

function formatUptime(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
}