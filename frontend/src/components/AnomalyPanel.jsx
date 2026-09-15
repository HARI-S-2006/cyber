import React, { useMemo } from 'react'
import { useStore } from '../hooks/useStore'

const LEVEL_CONFIG = {
  CRITICAL: { color: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/20', icon: '🔴' },
  HIGH: { color: 'text-orange-400', bg: 'bg-orange-500/10', border: 'border-orange-500/20', icon: '🟠' },
  MEDIUM: { color: 'text-yellow-400', bg: 'bg-yellow-500/10', border: 'border-yellow-500/20', icon: '🟡' },
  LOW: { color: 'text-green-400', bg: 'bg-green-500/10', border: 'border-green-500/20', icon: '🟢' },
  INFO: { color: 'text-cyan-400', bg: 'bg-cyan-500/10', border: 'border-cyan-500/20', icon: '🔵' }
}

export default function AnomalyPanel({ anomalies }) {
  const { selectedAnomaly, selectAnomaly } = useStore()
  
  const groupedAnomalies = useMemo(() => {
    const groups = {}
    anomalies.forEach(a => {
      if (!groups[a.threat_level]) groups[a.threat_level] = []
      groups[a.threat_level].push(a)
    })
    return groups
  }, [anomalies])
  
  const levelOrder = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO']
  
  return (
    <div className="flex-1 overflow-auto p-4 space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">Detected Anomalies</h2>
        <span className="badge badge-info">{anomalies.length} total</span>
      </div>
      
      {anomalies.length === 0 ? (
        <div className="text-center py-16 text-gray-500">
          <div className="text-6xl mb-4">🛡️</div>
          <p className="text-lg">No anomalies detected</p>
          <p className="text-sm">Traffic appears normal</p>
        </div>
      ) : (
        <div className="space-y-4">
          {levelOrder.map(level => {
            const levelAnomalies = groupedAnomalies[level]
            if (!levelAnomalies?.length) return null
            const config = LEVEL_CONFIG[level]
            
            return (
              <section key={level} className={`${config.bg} ${config.border} border rounded-xl overflow-hidden`}>
                <div className="px-4 py-3 bg-gray-900/50 border-b border-gray-800 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-xl">{config.icon}</span>
                    <div>
                      <h3 className="font-semibold">{level}</h3>
                      <span className="text-sm text-gray-400">{levelAnomalies.length} anomalies</span>
                    </div>
                  </div>
                  <span className={`badge ${config.color.replace('text-', 'badge-')}`}>
                    {levelAnomalies.reduce((max, a) => Math.max(max, a.anomaly_score), 0).toFixed(2)}
                  </span>
                </div>
                
                <div className="divide-y divide-gray-800">
                  {levelAnomalies.slice(0, 20).map(anomaly => (
                    <AnomalyRow
                      key={anomaly.flow_id}
                      anomaly={anomaly}
                      config={config}
                      selected={selectedAnomaly?.flow_id === anomaly.flow_id}
                      onClick={() => selectAnomaly(anomaly)}
                    />
                  ))}
                  {levelAnomalies.length > 20 && (
                    <div className="px-4 py-3 text-center text-gray-500 text-sm">
                      +{levelAnomalies.length - 20} more anomalies of this level
                    </div>
                  )}
                </div>
              </section>
            )
          })}
        </div>
      )}
      
      {selectedAnomaly && (
        <AnomalyDetailModal anomaly={selectedAnomaly} onClose={() => selectAnomaly(null)} />
      )}
    </div>
  )
}

function AnomalyRow({ anomaly, config, selected, onClick }) {
  return (
    <div
      className={`px-4 py-3 hover:bg-gray-800/50 transition-colors cursor-pointer ${selected ? 'bg-cyan-500/10 border-l-2 border-cyan-500' : ''}`}
      onClick={onClick}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-lg">{config.icon}</span>
          <div>
            <div className="font-mono text-sm font-medium">{anomaly.flow_id}</div>
            <div className="text-xs text-gray-400">
              {new Date(anomaly.timestamp).toLocaleString()}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="w-24 h-2 bg-gray-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-green-400 via-yellow-400 to-red-400"
              style={{ width: `${anomaly.anomaly_score * 100}%` }}
            ></div>
          </div>
          <span className={`font-mono ${config.color}`}>
            {(anomaly.anomaly_score * 100).toFixed(1)}%
          </span>
        </div>
      </div>
    </div>
  )
}

function AnomalyDetailModal({ anomaly, onClose }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="glass-panel w-full max-w-2xl max-h-[90vh] overflow-auto rounded-xl">
        <div className="flex items-center justify-between p-4 border-b border-gray-800">
          <h3 className="font-semibold">Anomaly Details</h3>
          <button onClick={onClose} className="p-2 hover:bg-gray-800 rounded">✕</button>
        </div>
        
        <div className="p-4 space-y-4">
          <div className="flex items-center gap-4 p-4 bg-gray-800/50 rounded-lg">
            <span className="text-4xl">
              {LEVEL_CONFIG[anomaly.threat_level]?.icon || '⚠️'}
            </span>
            <div>
              <div className="font-mono text-lg">{anomaly.flow_id}</div>
              <div className="text-sm text-gray-400">
                {new Date(anomaly.timestamp).toLocaleString()}
              </div>
            </div>
            <div className="ml-auto text-right">
              <div className="text-2xl font-bold" style={{ color: LEVEL_CONFIG[anomaly.threat_level]?.color }}>
                {(anomaly.anomaly_score * 100).toFixed(1)}%
              </div>
              <div className="text-xs text-gray-400">{anomaly.threat_level}</div>
            </div>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            {Object.entries(anomaly.features).map(([key, value]) => (
              <div key={key} className="p-3 bg-gray-800/50 rounded-lg">
                <div className="text-xs text-gray-400">{key}</div>
                <div className="font-mono text-sm">{typeof value === 'object' ? JSON.stringify(value) : value}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}