import React from 'react'
import { useStore } from '../hooks/useStore'

const THREAT_LEVELS = [
  { key: 'CRITICAL', label: 'Critical', color: 'badge-critical' },
  { key: 'HIGH', label: 'High', color: 'badge-high' },
  { key: 'MEDIUM', label: 'Medium', color: 'badge-medium' },
  { key: 'LOW', label: 'Low', color: 'badge-low' },
  { key: 'INFO', label: 'Info', color: 'badge-info' }
]

const PROTOCOLS = ['TCP', 'UDP', 'ICMP']

export default function Sidebar() {
  const {
    timeRange,
    filters,
    setTimeRange,
    setFilters,
    activeTab,
    setActiveTab
  } = useStore()
  
  const tabs = [
    { id: 'globe', label: 'Globe', icon: '🌐' },
    { id: 'flows', label: 'Flows', icon: '📊' },
    { id: 'anomalies', label: 'Anomalies', icon: '⚠️' },
    { id: 'alerts', label: 'Alerts', icon: '🚨' },
    { id: 'settings', label: 'Settings', icon: '⚙️' }
  ]
  
  return (
    <aside className="fixed lg:static inset-y-0 right-0 w-96 lg:w-80 bg-gray-900/95 border-l border-gray-800 flex flex-col z-50 transform transition-transform duration-300">
      <div className="p-4 border-b border-gray-800 flex items-center justify-between">
        <h2 className="font-semibold text-lg">Control Panel</h2>
        <button 
          className="lg:hidden p-2 rounded hover:bg-gray-800"
          onClick={() => setSidebarOpen(false)}
          aria-label="Close sidebar"
        >
          ✕
        </button>
      </div>
      
      <nav className="p-2 flex gap-1 border-b border-gray-800 overflow-x-auto" role="tablist">
        {tabs.map(tab => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={activeTab === tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap flex items-center gap-2 ${
              activeTab === tab.id
                ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                : 'text-gray-400 hover:text-white hover:bg-gray-800'
            }`}
          >
            <span>{tab.icon}</span>
            <span>{tab.label}</span>
          </button>
        ))}
      </nav>
      
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        <section>
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Time Range</h3>
          <div className="space-y-2">
            {[
              { value: 60000, label: 'Last 1 minute' },
              { value: 300000, label: 'Last 5 minutes' },
              { value: 900000, label: 'Last 15 minutes' },
              { value: 3600000, label: 'Last 1 hour' },
              { value: 86400000, label: 'Last 24 hours' }
            ].map(option => (
              <label key={option.value} className="flex items-center gap-3 cursor-pointer">
                <input
                  type="radio"
                  name="timeRange"
                  value={option.value}
                  checked={timeRange === option.value}
                  onChange={(e) => setTimeRange(Number(e.target.value))}
                  className="accent-cyan-500"
                />
                <span className="text-sm">{option.label}</span>
              </label>
            ))}
          </div>
        </section>
        
        <section>
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Threat Level Filter</h3>
          <div className="flex flex-wrap gap-2">
            {THREAT_LEVELS.map(level => (
              <label key={level.key} className="cursor-pointer">
                <input
                  type="checkbox"
                  checked={filters.threatLevel.includes(level.key)}
                  onChange={(e) => setFilters({
                    threatLevel: e.target.checked
                      ? [...filters.threatLevel, level.key]
                      : filters.threatLevel.filter(l => l !== level.key)
                  })}
                  className="sr-only peer"
                />
                <span className={`badge ${level.color} peer-checked:ring-2 peer-checked:ring-offset-2 peer-checked:ring-offset-gray-900`}>
                  {level.label}
                </span>
              </label>
            ))}
          </div>
        </section>
        
        <section>
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Protocol Filter</h3>
          <div className="flex flex-wrap gap-2">
            {PROTOCOLS.map(proto => (
              <label key={proto} className="cursor-pointer">
                <input
                  type="checkbox"
                  checked={filters.protocol.includes(proto)}
                  onChange={(e) => setFilters({
                    protocol: e.target.checked
                      ? [...filters.protocol, proto]
                      : filters.protocol.filter(p => p !== proto)
                  })}
                  className="sr-only peer"
                />
                <span className={`badge badge-info peer-checked:ring-2 peer-checked:ring-offset-2 peer-checked:ring-offset-gray-900 peer-checked:ring-cyan-500`}>
                  {proto}
                </span>
              </label>
            ))}
          </div>
        </section>
        
        <section>
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Min Threat Score</h3>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={filters.minScore}
            onChange={(e) => setFilters({ minScore: Number(e.target.value) })}
            className="w-full accent-cyan-500"
          />
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>0.0</span>
            <span>{filters.minScore.toFixed(2)}</span>
            <span>1.0</span>
          </div>
        </section>
        
        <section>
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Search</h3>
          <input
            type="text"
            placeholder="Search flows, IPs, domains..."
            value={filters.searchQuery}
            onChange={(e) => setFilters({ searchQuery: e.target.value })}
            className="input text-sm"
          />
        </section>
      </div>
      
      <div className="p-4 border-t border-gray-800">
        <div className="flex items-center justify-between text-sm text-gray-400">
          <span>Auto-refresh</span>
          <label className="relative inline-flex items-center cursor-pointer">
            <input type="checkbox" defaultChecked className="sr-only peer" />
            <div className="w-11 h-6 bg-gray-700 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-cyan-500/20 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-cyan-500"></div>
          </label>
        </div>
      </div>
    </aside>
  )
}