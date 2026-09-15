import React from 'react'

const STATS = [
  { key: 'active_flows', label: 'Active Flows', icon: '📡', color: 'text-cyan-400' },
  { key: 'flows_last_minute', label: 'Flows/min', icon: '📈', color: 'text-green-400' },
  { key: 'anomalies_last_5min', label: 'Anomalies (5m)', icon: '⚠️', color: 'text-yellow-400' },
  { key: 'anomaly_rate', label: 'Anomaly Rate', icon: '📊', color: 'text-red-400' }
]

export default function StatsPanel({ stats }) {
  if (!stats) return null
  
  return (
    <div className="flex gap-2 flex-wrap">
      {STATS.map(({ key, label, icon, color }) => (
        <div key={key} className="glass-panel p-3 rounded-lg border min-w-[140px]">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-lg">{icon}</span>
            <span className="text-xs text-gray-400">{label}</span>
          </div>
          <div className={`font-mono text-xl font-bold ${color}`}>
            {key === 'anomaly_rate' 
              ? stats[key].toFixed(1) + '/min'
              : stats[key].toLocaleString()}
          </div>
        </div>
      ))}
    </div>
  )
}

export function DetailedStatsPanel({ stats }) {
  if (!stats) return <div className="text-gray-500 text-center py-8">Loading stats...</div>
  
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <StatCard
        value={stats.active_flows.toLocaleString()}
        label="Active Flows"
        trend={{ value: stats.flows_last_minute, up: true }}
        icon="📡"
      />
      <StatCard
        value={stats.anomalies_last_5min.toLocaleString()}
        label="Anomalies (5m)"
        trend={{ value: stats.anomaly_rate.toFixed(1), up: stats.anomaly_rate > 10 }}
        icon="⚠️"
      />
      <StatCard
        value={Object.values(stats.anomalies_by_level).reduce((a, b) => a + b, 0).toLocaleString()}
        label="Total Anomalies"
        icon="🚨"
      />
      <StatCard
        value={stats.top_talkers[0]?.bytes ? formatBytes(stats.top_talkers[0].bytes) : '0 B'}
        label="Top Talker Volume"
        icon="📊"
      />
    </div>
  )
}

function StatCard({ value, label, trend, icon }) {
  return (
    <div className="stat-card">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-3xl font-bold">{value}</div>
          <div className="stat-label">{label}</div>
        </div>
        <span className="text-2xl">{icon}</span>
      </div>
      {trend && (
        <div className={`stat-trend ${trend.up ? 'up' : 'down'}`}>
          <span>{trend.up ? '↑' : '↓'}</span>
          <span>{trend.value}/min</span>
        </div>
      )}
    </div>
  )
}

function formatBytes(bytes) {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}