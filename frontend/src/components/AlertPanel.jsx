import React from 'react'
import { useStore } from '../hooks/useStore'

const SEVERITY_CONFIG = {
  CRITICAL: { color: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/20', icon: '🔴' },
  HIGH: { color: 'text-orange-400', bg: 'bg-orange-500/10', border: 'border-orange-500/20', icon: '🟠' },
  MEDIUM: { color: 'text-yellow-400', bg: 'bg-yellow-500/10', border: 'border-yellow-500/20', icon: '🟡' },
  LOW: { color: 'text-green-400', bg: 'bg-green-500/10', border: 'border-green-500/20', icon: '🟢' }
}

export default function AlertPanel() {
  const { alerts, acknowledgeAlert, clearAlerts } = useStore()
  
  const unacknowledged = alerts.filter(a => !a.acknowledged).length
  
  return (
    <div className="flex-1 flex flex-col">
      <div className="p-4 border-b border-gray-800 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h2 className="text-xl font-bold">Security Alerts</h2>
          {unacknowledged > 0 && (
            <span className="badge badge-critical animate-pulse">{unacknowledged} unread</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={clearAlerts}
            disabled={alerts.length === 0}
            className="btn btn-secondary text-sm"
          >
            Clear All
          </button>
        </div>
      </div>
      
      <div className="flex-1 overflow-auto">
        {alerts.length === 0 ? (
          <div className="flex-1 flex items-center justify-center text-gray-500">
            <div className="text-center">
              <div className="text-6xl mb-4">🔔</div>
              <p className="text-lg">No alerts</p>
              <p className="text-sm">All systems nominal</p>
            </div>
          </div>
        ) : (
          <div className="divide-y divide-gray-800">
            {alerts.map(alert => (
              <AlertRow key={alert.id} alert={alert} onAcknowledge={acknowledgeAlert} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function AlertRow({ alert, onAcknowledge }) {
  const config = SEVERITY_CONFIG[alert.severity] || SEVERITY_CONFIG.MEDIUM
  const timeAgo = formatTimeAgo(alert.timestamp)
  
  return (
    <div className={`p-4 ${alert.acknowledged ? 'opacity-60' : ''} hover:bg-gray-800/50 transition-colors ${config.bg} ${config.border} border-y`}>
      <div className="flex items-start gap-3">
        <span className="text-xl mt-0.5">{config.icon}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3">
            <span className="font-medium">{alert.message}</span>
            <span className={`badge ${config.color.replace('text-', 'badge-')} text-xs`}>
              {alert.severity}
            </span>
            <span className="text-xs text-gray-500">{timeAgo}</span>
            {alert.flow_id && (
              <span className="font-mono text-xs text-cyan-400">{alert.flow_id}</span>
            )}
          </div>
          <div className="text-xs text-gray-500 mt-1 flex items-center gap-2">
            <span>{alert.type}</span>
            <span>•</span>
            <span>ID: {alert.id.slice(0, 12)}...</span>
          </div>
        </div>
        {!alert.acknowledged && (
          <button
            onClick={() => onAcknowledge(alert.id)}
            className="btn btn-primary text-sm shrink-0"
          >
            Acknowledge
          </button>
        )}
      </div>
    </div>
  )
}

function formatTimeAgo(timestamp) {
  const diff = Date.now() - timestamp
  if (diff < 60000) return `${Math.floor(diff / 1000)}s ago`
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`
  return new Date(timestamp).toLocaleDateString()
}