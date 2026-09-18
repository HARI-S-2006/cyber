import React, { useEffect } from 'react'
import { Canvas } from '@react-three/fiber'
import { useStore, useFilteredFlows, useFilteredAnomalies } from '../hooks/useStore'
import { useWebSocket } from '../hooks/useWebSocket'
import { GlobeScene } from './globe/GlobeScene'
import StatsPanel from './StatsPanel'
import FlowTable from './FlowTable'
import AnomalyPanel from './AnomalyPanel'
import AlertPanel from './AlertPanel'
import Sidebar from './Sidebar'
import Toolbar from './Toolbar'
import ConnectionStatus from './ConnectionStatus'
import { ErrorBoundary } from './ErrorBoundary'

export default function Dashboard() {
  const { connected, connecting, activeTab, sidebarOpen, setActiveTab, setSidebarOpen } = useStore()
  const { connect, disconnect } = useWebSocket()
  
  useEffect(() => {
    connect()
    return () => disconnect()
  }, [connect, disconnect])
  
  return (
    <div className="flex h-full w-full relative">
      <div className={`flex-1 flex flex-col ${sidebarOpen ? '' : 'lg:pl-0'}`}>
        <Toolbar onToggleSidebar={setSidebarOpen} />
        
        <div className="flex-1 flex relative overflow-hidden">
          <main className="flex-1 flex flex-col relative">
            {activeTab === 'globe' && <GlobeView />}
            {activeTab === 'flows' && <FlowsView />}
            {activeTab === 'anomalies' && <AnomaliesView />}
            {activeTab === 'alerts' && <AlertsView />}
            {activeTab === 'settings' && <SettingsView />}
          </main>
          
          {sidebarOpen && <Sidebar />}
        </div>
      </div>
      
      <ConnectionStatus />
    </div>
  )
}

function GlobeView() {
  const { dashboardStats, globeData } = useStore()
  
  return (
    <div className="relative h-full w-full">
      <ErrorBoundary>
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
      </ErrorBoundary>
      
      <div className="absolute top-4 right-4 z-10 flex gap-2">
        <StatsPanel stats={dashboardStats} />
      </div>
      
      <div className="absolute bottom-4 left-4 z-10 flex gap-2 flex-wrap max-w-[400px]">
        {globeData?.arcs?.slice(0, 5).map((arc, i) => (
          <ArcInfoCard key={i} arc={arc} />
        ))}
      </div>
    </div>
  )
}

function FlowsView() {
  const flows = useFilteredFlows()
  return <FlowTable flows={flows} />
}

function AnomaliesView() {
  const anomalies = useFilteredAnomalies()
  return <AnomalyPanel anomalies={anomalies} />
}

function AlertsView() {
  return <AlertPanel />
}

function SettingsView() {
  return (
    <div className="flex-1 p-8 overflow-auto">
      <h2 className="text-2xl font-bold mb-8">Settings</h2>
      <div className="max-w-2xl space-y-6">
        <SettingSection title="Visualization" />
        <SettingSection title="Detection" />
        <SettingSection title="Data Retention" />
        <SettingSection title="Notifications" />
      </div>
    </div>
  )
}

function SettingSection({ title }) {
  return (
    <div className="card">
      <h3 className="font-semibold mb-4">{title}</h3>
      <div className="space-y-4 text-sm text-gray-400">
        <p>Settings for {title.toLowerCase()} will be implemented here.</p>
      </div>
    </div>
  )
}

function ArcInfoCard({ arc }) {
  const getLevelColor = (level) => {
    switch (level) {
      case 'CRITICAL': return 'bg-red-500/20 border-red-500/30 text-red-400'
      case 'HIGH': return 'bg-orange-500/20 border-orange-500/30 text-orange-400'
      case 'MEDIUM': return 'bg-yellow-500/20 border-yellow-500/30 text-yellow-400'
      default: return 'bg-cyan-500/20 border-cyan-500/30 text-cyan-400'
    }
  }
  
  return (
    <div className={`glass-panel p-3 rounded-lg border min-w-[180px] ${getLevelColor(arc.level)}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="font-mono text-xs text-gray-400">{arc.src}</span>
        <span className="badge badge-info text-xs">Score: {arc.score.toFixed(2)}</span>
      </div>
      <div className="flex items-center gap-1 text-xs text-gray-300">
        <span>→</span>
        <span className="font-mono">{arc.dst}</span>
      </div>
      <div className="text-xs text-gray-500 mt-1">
        {new Date(arc.timestamp).toLocaleTimeString()}
      </div>
    </div>
  )
}