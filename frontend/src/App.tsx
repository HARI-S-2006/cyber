import { Canvas } from '@react-three/fiber'
import { GlobeScene } from './components/globe/GlobeScene'
import { TerminalLog } from './components/hud/TerminalLog'
import { ThreatMatrix } from './components/hud/ThreatMatrix'
import { SystemStatus } from './components/hud/SystemStatus'
import { ThreatAlert } from './components/hud/ThreatAlert'
import { TopBar } from './components/ui/TopBar'
import { SidePanel } from './components/ui/SidePanel'
import { useWebSocket } from './hooks/useWebSocket'
import { useStore } from './hooks/useStore'
import { useEffect } from 'react'

function App() {
  const { connected, threats, stats, setThreats, setStats, setConnected } = useStore()
  const { connect, disconnect } = useWebSocket()

  useEffect(() => {
    connect()
    return () => disconnect()
  }, [connect, disconnect])

  // Handle incoming WebSocket messages
  useEffect(() => {
    // This would be handled by the WebSocket hook
  }, [])

  return (
    <div className="h-screen w-screen bg-cyber-bg overflow-hidden">
      {/* CRT Scanlines */}
      <div className="fixed inset-0 pointer-events-none z-50" style={{
        background: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(57, 255, 20, 0.03) 2px, rgba(57, 255, 20, 0.03) 4px)',
        animation: 'scanline 8s linear infinite',
        opacity: 0.5,
      }} />

      {/* Main Layout */}
      <div className="relative h-full w-full flex">
        {/* Left Panel - Terminal Log & Threat Matrix */}
        <aside className="w-96 flex flex-col panel border-r border-cyber-panelBorder">
          <div className="panel-header">
            <h2 className="panel-title">INTERCEPT LOG</h2>
            <div className="flex items-center gap-2">
              <span className={`status-indicator status-${connected ? 'online' : 'danger'}`}>
                {connected ? 'LIVE' : 'OFFLINE'}
              </span>
            </div>
          </div>
          <TerminalLog />
          <div className="border-t border-cyber-panelBorder" />
          <ThreatMatrix />
        </aside>

        {/* Center - 3D Globe */}
        <main className="flex-1 relative">
          <div className="absolute inset-0 z-0">
            <Canvas
              camera={{ position: [0, 0, 200], fov: 50 }}
              gl={{ antialias: true, alpha: true, preserveDrawingBuffer: false }}
              style={{ width: '100%', height: '100%' }}
            >
              <color attach="background" args={['#000000']} />
              <fog attach="fog" args={['#000000', 100, 500]} />
              
              <ambientLight intensity={0.3} color="#39FF14" />
              <directionalLight position={[200, 200, 200]} intensity={1.5} color="#ffffff" castShadow />
              <pointLight position={[0, 0, 0]} color="#39FF14" intensity={0.5} distance={300} decay={2} />
              
              <GlobeScene />
            </Canvas>
          </div>

          {/* Top Bar */}
          <TopBar />

          {/* Bottom Status Bar */}
          <div className="absolute bottom-0 left-0 right-0 panel border-t border-cyber-panelBorder px-4 py-2">
            <SystemStatus />
          </div>
        </main>

        {/* Right Panel - Threat Details & Charts */}
        <aside className="w-96 flex flex-col panel border-l border-cyber-panelBorder">
          <div className="panel-header">
            <h2 className="panel-title">THREAT INTELLIGENCE</h2>
          </div>
          <div className="flex-1 overflow-auto p-4 space-y-4">
            {/* Threat details would go here */}
            <div className="panel p-4">
              <h3 className="panel-title mb-3">ACTIVE THREATS</h3>
              <div className="space-y-2 text-xs">
                <p className="text-cyber-textDim">No active threats detected</p>
              </div>
            </div>
          </div>
        </aside>
      </div>

      {/* Global Threat Alert */}
      <ThreatAlert />
    </div>
  )
}

export default App