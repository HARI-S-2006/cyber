import { useStore } from '../../hooks/useStore'
import { useEffect, useState } from 'react'
import { cn } from '../../utils/cn'

export function ThreatAlert() {
  const { threats } = useStore()
  const [visibleAlert, setVisibleAlert] = useState<any>(null)
  const [show, setShow] = useState(false)
  
  useEffect(() => {
    if (threats.length > 0) {
      const latest = threats[0]
      if (latest && latest.threat_score > 0.7 && !latest.acknowledged) {
        setVisibleAlert(latest)
        setShow(true)
        const timer = setTimeout(() => setShow(false), 10000)
        return () => clearTimeout(timer)
      }
    }
  }, [threats])
  
  if (!show || !visibleAlert) return null
  
  const formatTime = (ts: number) => new Date(ts * 1000).toLocaleTimeString()
  
  return (
    <div
      className={cn(
        'fixed bottom-24 right-4 z-50 animate-slide-up max-w-md',
        'panel border-l-4 border-l-cyber-danger shadow-glow-danger'
      )}
      role="alert"
    >
      <div className="p-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-cyber-danger/20 flex items-center justify-center border border-cyber-danger/30">
              <svg className="w-6 h-6 text-cyber-danger" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <div>
              <p className="font-mono text-sm font-bold text-cyber-danger">THREAT DETECTED</p>
              <p className="text-xs text-cyber-textDim">{visibleAlert.threat_type}</p>
            </div>
          </div>
          <button
            onClick={() => setShow(false)}
            className="text-cyber-textDim hover:text-cyber-danger transition-colors"
          >
            ✕
          </button>
        </div>
        
        <div className="mt-3 space-y-2 text-xs">
          <div className="grid grid-cols-2 gap-2">
            <div className="panel p-2">
              <p className="text-xs text-cyber-textDim">SOURCE</p>
              <p className="font-mono text-sm text-cyber-text">{visibleAlert.src_ip}:{visibleAlert.src_port}</p>
            </div>
            <div className="panel p-2">
              <p className="text-xs text-cyber-textDim">TARGET</p>
              <p className="font-mono text-sm text-cyber-text">{visibleAlert.dst_ip}:{visibleAlert.dst_port}</p>
            </div>
            <div className="panel p-2">
              <p className="text-xs text-cyber-textDim">PROTOCOL</p>
              <p className="font-mono text-sm text-cyber-primary">{visibleAlert.protocol}</p>
            </div>
            <div className="panel p-2">
              <p className="text-xs text-cyber-textDim">SCORE</p>
              <p className="font-mono text-lg font-bold text-cyber-danger">{(visibleAlert.threat_score * 100).toFixed(1)}%</p>
            </div>
          </div>
          
          <div className="flex gap-2 pt-2">
            <button className="btn-danger flex-1 text-xs" onClick={() => {}}>
              BLOCK IP
            </button>
            <button className="btn-warning flex-1 text-xs" onClick={() => setShow(false)}>
              DISMISS
            </button>
            <button className="btn-primary flex-1 text-xs" onClick={() => {}}>
              INVESTIGATE
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}