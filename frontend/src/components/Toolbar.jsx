import React from 'react'
import { useStore } from '../hooks/useStore'

export default function Toolbar({ onToggleSidebar }) {
  const { connected, connecting, activeTab, setActiveTab, sidebarOpen } = useStore()
  
  const tabs = [
    { id: 'globe', label: 'Globe', icon: '🌐' },
    { id: 'flows', label: 'Flows', icon: '📊' },
    { id: 'anomalies', label: 'Anomalies', icon: '⚠️' },
    { id: 'alerts', label: 'Alerts', icon: '🚨' },
    { id: 'settings', label: 'Settings', icon: '⚙️' }
  ]
  
  return (
    <header className="h-14 border-b border-gray-800 bg-gray-900/80 backdrop-blur-sm flex items-center px-4 gap-4 z-10">
      <button
        onClick={onToggleSidebar}
        className="lg:hidden p-2 rounded hover:bg-gray-800"
        aria-label="Open sidebar"
      >
        ☰
      </button>
      
      <div className="flex-1 flex items-center gap-6 max-w-4xl mx-auto">
        <div className="flex items-center gap-2">
          <span className="text-xl">🛡️</span>
          <h1 className="font-bold text-lg bg-gradient-to-r from-cyan-400 to-purple-500 bg-clip-text text-transparent">
            Cyber Threat Visualizer
          </h1>
        </div>
        
        <nav className="flex items-center gap-1 ml-4" role="tablist">
          {tabs.map(tab => (
            <button
              key={tab.id}
              role="tab"
              aria-selected={activeTab === tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                  : 'text-gray-400 hover:text-white hover:bg-gray-800'
              }`}
            >
              <span className="flex items-center gap-1">
                <span>{tab.icon}</span>
                <span>{tab.label}</span>
              </span>
            </button>
          ))}
        </nav>
      </div>
      
      <div className="flex items-center gap-4 ml-auto">
        <ConnectionIndicator connected={connected} connecting={connecting} />
        <div className="hidden sm:flex items-center gap-2 px-3 py-1 bg-gray-800 rounded-lg text-sm font-mono text-cyan-400">
          <span className="animate-pulse">●</span>
          <span>LIVE</span>
        </div>
      </div>
    </header>
  )
}

function ConnectionIndicator({ connected, connecting }) {
  if (connecting) {
    return (
      <div className="flex items-center gap-2 text-yellow-400">
        <span className="w-2 h-2 rounded-full bg-yellow-400 animate-pulse"></span>
        <span className="text-sm">Connecting...</span>
      </div>
    )
  }
  
  return (
    <div className="flex items-center gap-2">
      <span className={`w-2 h-2 rounded-full ${connected ? 'bg-green-400' : 'bg-red-400'}`}></span>
      <span className="text-sm text-gray-400">{connected ? 'Connected' : 'Disconnected'}</span>
    </div>
  )
}