import { create } from 'zustand'
import { subscribeWithSelector } from 'zustand/middleware'

/**
 * @typedef {Object} FlowData
 * @property {string} flow_id
 * @property {string} src_ip
 * @property {string} dst_ip
 * @property {number} src_port
 * @property {number} dst_port
 * @property {string} protocol
 * @property {number} packets_fwd
 * @property {number} packets_bwd
 * @property {number} bytes_fwd
 * @property {number} bytes_bwd
 * @property {number} duration_ms
 * @property {number} threat_score
 * @property {string[]} labels
 * @property {number} timestamp
 * @property {number} [iat_fwd_mean]
 * @property {number} [iat_bwd_mean]
 * @property {number} [pkt_len_fwd_mean]
 * @property {number} [pkt_len_bwd_mean]
 * @property {number} [payload_entropy_fwd_mean]
 * @property {number} [payload_entropy_bwd_mean]
 * @property {string} [tls_sni]
 * @property {string} [http_host]
 * @property {string[]} [dns_queries]
 */

/**
 * @typedef {Object} AnomalyEvent
 * @property {string} flow_id
 * @property {number} timestamp
 * @property {boolean} is_anomaly
 * @property {number} anomaly_score
 * @property {'CRITICAL'|'HIGH'|'MEDIUM'|'LOW'|'INFO'} threat_level
 * @property {Record<string, any>} features
 */

/**
 * @typedef {Object} DashboardStats
 * @property {number} timestamp
 * @property {number} active_flows
 * @property {number} flows_last_minute
 * @property {number} anomalies_last_5min
 * @property {Record<string, number>} anomalies_by_level
 * @property {Array<{ip: string, bytes: number}>} top_talkers
 * @property {Record<string, number>} protocol_distribution
 * @property {number} anomaly_rate
 */

/**
 * @typedef {Object} GlobeArc
 * @property {string} src
 * @property {string} dst
 * @property {number} score
 * @property {string} level
 * @property {number} timestamp
 */

/**
 * @typedef {Object} GlobeData
 * @property {GlobeArc[]} arcs
 * @property {number} timestamp
 */

/**
 * @typedef {Object} AlertEvent
 * @property {string} id
 * @property {string} type
 * @property {string} severity
 * @property {string} message
 * @property {number} timestamp
 * @property {boolean} acknowledged
 * @property {string} [flow_id]
 */

/**
 * @typedef {Object} AppState
 * @property {boolean} connected
 * @property {boolean} connecting
 * @property {string|null} connectionError
 * @property {Map<string, FlowData>} flows
 * @property {FlowData[]} recentFlows
 * @property {AnomalyEvent[]} anomalies
 * @property {AnomalyEvent[]} recentAnomalies
 * @property {DashboardStats|null} dashboardStats
 * @property {GlobeData|null} globeData
 * @property {AlertEvent[]} alerts
 * @property {FlowData|null} selectedFlow
 * @property {AnomalyEvent|null} selectedAnomaly
 * @property {number} timeRange
 * @property {{protocol: string[], threatLevel: string[], minScore: number, searchQuery: string}} filters
 * @property {boolean} sidebarOpen
 * @property {'globe'|'flows'|'anomalies'|'alerts'|'settings'} activeTab
 * @property {{x: number, y: number, z: number}} globeRotation
 * @property {number} globeZoom
 * @property {boolean} showHeatmap
 * @property {boolean} showParticles
 * @property {number} arcTimeWindow
 * @property {(connected: boolean) => void} setConnected
 * @property {(connecting: boolean) => void} setConnecting
 * @property {(error: string|null) => void} setConnectionError
 * @property {(flow: FlowData) => void} addFlow
 * @property {(flowId: string, updates: Partial<FlowData>) => void} updateFlow
 * @property {(flowId: string) => void} removeFlow
 * @property {(flows: FlowData[]) => void} setRecentFlows
 * @property {(flow: FlowData|null) => void} selectFlow
 * @property {(anomaly: AnomalyEvent) => void} addAnomaly
 * @property {(anomalies: AnomalyEvent[]) => void} setRecentAnomalies
 * @property {(anomaly: AnomalyEvent|null) => void} selectAnomaly
 * @property {(stats: DashboardStats) => void} setDashboardStats
 * @property {(data: GlobeData) => void} setGlobeData
 * @property {(alert: AlertEvent) => void} addAlert
 * @property {(alertId: string) => void} acknowledgeAlert
 * @property {() => void} clearAlerts
 * @property {(range: number) => void} setTimeRange
 * @property {(filters: Partial<AppState['filters']>) => void} setFilters
 * @property {(open: boolean) => void} setSidebarOpen
 * @property {(tab: AppState['activeTab']) => void} setActiveTab
 * @property {(rotation: {x: number, y: number, z: number}) => void} setGlobeRotation
 * @property {(zoom: number) => void} setGlobeZoom
 * @property {() => void} toggleHeatmap
 * @property {() => void} toggleParticles
 * @property {(window: number) => void} setArcTimeWindow
 * @property {() => void} reset
 */

const initialState = {
  connected: false,
  connecting: false,
  connectionError: null,
  flows: new Map(),
  recentFlows: [],
  anomalies: [],
  recentAnomalies: [],
  dashboardStats: null,
  globeData: null,
  alerts: [],
  selectedFlow: null,
  selectedAnomaly: null,
  timeRange: 300000,
  filters: {
    protocol: [],
    threatLevel: [],
    minScore: 0,
    searchQuery: ''
  },
  sidebarOpen: true,
  activeTab: 'globe',
  globeRotation: { x: 0, y: 0, z: 0 },
  globeZoom: 1,
  showHeatmap: false,
  showParticles: true,
  arcTimeWindow: 60000
}

export const useStore = create(
  subscribeWithSelector((set, get) => ({
    ...initialState,
    
    setConnected: (connected) => set({ connected }),
    setConnecting: (connecting) => set({ connecting }),
    setConnectionError: (error) => set({ connectionError: error }),
    
    addFlow: (flow) => set((state) => {
      const newFlows = new Map(state.flows)
      newFlows.set(flow.flow_id, flow)
      const recentFlows = [flow, ...state.recentFlows].slice(0, 1000)
      return { flows: newFlows, recentFlows }
    }),
    
    updateFlow: (flowId, updates) => set((state) => {
      const flow = state.flows.get(flowId)
      if (!flow) return state
      const updated = { ...flow, ...updates }
      const newFlows = new Map(state.flows)
      newFlows.set(flowId, updated)
      const recentFlows = state.recentFlows.map(f => f.flow_id === flowId ? updated : f)
      return { flows: newFlows, recentFlows }
    }),
    
    removeFlow: (flowId) => set((state) => {
      const newFlows = new Map(state.flows)
      newFlows.delete(flowId)
      const recentFlows = state.recentFlows.filter(f => f.flow_id !== flowId)
      return { flows: newFlows, recentFlows }
    }),
    
    setRecentFlows: (flows) => set({ recentFlows: flows }),
    selectFlow: (flow) => set({ selectedFlow: flow }),
    
    addAnomaly: (anomaly) => set((state) => {
      const anomalies = [anomaly, ...state.anomalies].slice(0, 5000)
      const recentAnomalies = [anomaly, ...state.recentAnomalies].slice(0, 100)
      
      if (anomaly.threat_level === 'CRITICAL' || anomaly.threat_level === 'HIGH') {
        const alert = {
          id: `alert-${Date.now()}-${Math.random().toString(36).slice(2)}`,
          type: 'ANOMALY_DETECTED',
          severity: anomaly.threat_level,
          message: `Anomaly detected: ${anomaly.flow_id} (score: ${anomaly.anomaly_score.toFixed(3)})`,
          timestamp: anomaly.timestamp,
          acknowledged: false,
          flow_id: anomaly.flow_id
        }
        return { anomalies, recentAnomalies, alerts: [alert, ...state.alerts].slice(0, 200) }
      }
      return { anomalies, recentAnomalies }
    }),
    
    setRecentAnomalies: (anomalies) => set({ recentAnomalies: anomalies }),
    selectAnomaly: (anomaly) => set({ selectedAnomaly: anomaly }),
    
    setDashboardStats: (stats) => set({ dashboardStats: stats }),
    setGlobeData: (data) => set({ globeData: data }),
    
    addAlert: (alert) => set((state) => ({ alerts: [alert, ...state.alerts].slice(0, 200) })),
    acknowledgeAlert: (alertId) => set((state) => ({
      alerts: state.alerts.map(a => a.id === alertId ? { ...a, acknowledged: true } : a)
    })),
    clearAlerts: () => set({ alerts: [] }),
    
    setTimeRange: (timeRange) => set({ timeRange }),
    setFilters: (filters) => set((state) => ({ filters: { ...state.filters, ...filters } })),
    setSidebarOpen: (sidebarOpen) => set({ sidebarOpen }),
    setActiveTab: (activeTab) => set({ activeTab }),
    
    setGlobeRotation: (rotation) => set({ globeRotation: rotation }),
    setGlobeZoom: (zoom) => set({ globeZoom: Math.max(0.5, Math.min(3, zoom)) }),
    toggleHeatmap: () => set((state) => ({ showHeatmap: !state.showHeatmap })),
    toggleParticles: () => set((state) => ({ showParticles: !state.showParticles })),
    setArcTimeWindow: (window) => set({ arcTimeWindow: window }),
    
    reset: () => set(initialState)
  }))
)

export const useFilteredFlows = () => {
  const { flows, filters } = useStore()
  return Array.from(flows.values()).filter(flow => {
    if (filters.protocol.length && !filters.protocol.includes(flow.protocol)) return false
    if (filters.minScore && flow.threat_score < filters.minScore) return false
    if (filters.searchQuery) {
      const query = filters.searchQuery.toLowerCase()
      const searchable = `${flow.src_ip} ${flow.dst_ip} ${flow.flow_id} ${flow.tls_sni || ''} ${flow.http_host || ''}`.toLowerCase()
      if (!searchable.includes(query)) return false
    }
    return true
  })
}

export const useFilteredAnomalies = () => {
  const { anomalies, filters } = useStore()
  return anomalies.filter(anomaly => {
    if (filters.threatLevel.length && !filters.threatLevel.includes(anomaly.threat_level)) return false
    if (filters.minScore && anomaly.anomaly_score < filters.minScore) return false
    if (filters.searchQuery) {
      const query = filters.searchQuery.toLowerCase()
      if (!anomaly.flow_id.toLowerCase().includes(query)) return false
    }
    return true
  })
}