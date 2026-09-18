import React from 'react'
import { useStore } from '../../hooks/useStore'

export function ThreatMatrix() {
  const { threats } = useStore()

  return (
    <div className="absolute top-20 right-4 z-10 glass-panel p-4 rounded border border-red-500/30 w-80 h-96 flex flex-col overflow-hidden bg-black/80">
      <h3 className="text-red-400 font-bold mb-2 font-mono border-b border-red-500/30 pb-2 flex justify-between">
        <span>THREAT MATRIX</span>
        <span className="text-xs self-end animate-pulse">LIVE</span>
      </h3>
      <div className="flex-1 overflow-auto flex flex-col gap-1 pr-1 font-mono text-xs">
        {threats.slice(0, 100).map((t, i) => (
          <div key={i} className="flex justify-between border-b border-red-900/30 py-1">
            <span className={t.threat_level === 'CRITICAL' ? 'text-red-500 font-bold' : 'text-orange-400'}>{t.threat_type}</span>
            <span className="text-gray-400">{t.src_ip}</span>
            <span className="text-red-400">{(t.threat_score * 100).toFixed(0)}%</span>
          </div>
        ))}
        {threats.length === 0 && (
          <div className="text-green-500 text-center mt-10">NO ACTIVE THREATS DETECTED</div>
        )}
      </div>
    </div>
  )
}
