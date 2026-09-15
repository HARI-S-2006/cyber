import { useStore } from '../../hooks/useStore'

export function TopBar() {
  const { connected, connecting, timeWindow, setTimeWindow, showThreatsOnly, setShowThreatsOnly, showArcs, setShowArcs, autoRotate, setAutoRotate } = useStore()
  
  const timeWindows = [
    { value: '1m', label: '1 MIN', ms: 60000 },
    { value: '5m', label: '5 MIN', ms: 300000 },
    { value: '15m', label: '15 MIN', ms: 900000 },
    { value: '1h', label: '1 HOUR', ms: 3600000 },
    { value: '24h', label: '24 HOUR', ms: 86400000 },
  ]
  
  const timeWindowToString = (ms: number): string => {
    const tw = timeWindows.find(tw => tw.ms === ms)
    return tw ? tw.value : '5m'
  }
  
  const currentTimeWindowStr = timeWindowToString(timeWindow)
  
  return (
    <header className="fixed top-0 left-0 right-0 z-40 panel border-b border-cyber-panelBorder px-4 py-2">
      <div className="flex items-center justify-between">
        {/* Left - Title & Time Windows */}
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded flex items-center justify-center bg-cyber-primary/20 border border-cyber-primary/30">
              <svg className="w-5 h-5 text-cyber-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <div>
              <h1 className="font-mono text-lg font-bold text-cyber-primary tracking-wider">CYBER THREAT VISUALIZER</h1>
              <p className="text-xs text-cyber-textDim">COMMAND CENTER v1.0.0</p>
            </div>
          </div>
          
          <div className="hidden md:flex items-center gap-1 bg-cyber-bgSecondary rounded p-1 border border-cyber-panelBorder">
            {timeWindows.map((tw) => (
              <button
                key={tw.value}
                onClick={() => setTimeWindow(tw.ms)}
                className={`px-3 py-1.5 text-xs font-mono font-medium rounded transition-all duration-200 ${
                  currentTimeWindowStr === tw.value
                    ? 'bg-cyber-primary text-cyber-bg shadow-glow-primary'
                    : 'text-cyber-textDim hover:text-cyber-text hover:bg-cyber-panelBorder'
                }`}
              >
                {tw.label}
              </button>
            ))}
          </div>
        </div>
        
        {/* Center - Connection Status */}
        <div className="flex items-center gap-4">
          <div className={`status-indicator ${connected ? 'status-online' : connecting ? 'status-warning' : 'status-danger'}`}>
            <span className="font-mono text-xs">
              {connected ? '● CONNECTED' : connecting ? '◐ CONNECTING...' : '● DISCONNECTED'}
            </span>
          </div>
          
          <div className="hidden lg:flex items-center gap-4 px-3 py-1 bg-cyber-bgSecondary rounded border border-cyber-panelBorder">
            <span className="text-xs text-cyber-textDim">PACKETS/SEC</span>
            <span className="font-mono text-lg font-bold text-cyber-primary tabular-nums">0</span>
          </div>
        </div>
        
        {/* Right - Controls */}
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={showArcs}
              onChange={(e) => setShowArcs(e.target.checked)}
              className="w-4 h-4 accent-cyber-primary rounded border-cyber-panelBorder"
            />
            <span className="text-xs text-cyber-textDim">ARCS</span>
          </label>
          
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={autoRotate}
              onChange={(e) => setAutoRotate(e.target.checked)}
              className="w-4 h-4 accent-cyber-primary rounded border-cyber-panelBorder"
            />
            <span className="text-xs text-cyber-textDim">AUTO-ROTATE</span>
          </label>
          
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={false}
              onChange={(e) => {}}
              className="w-4 h-4 accent-cyber-primary rounded border-cyber-panelBorder"
            />
            <span className="text-xs text-cyber-textDim">THREATS ONLY</span>
          </label>
        </div>
      </div>
    </header>
  )
}