import { create } from 'zustand'
import { subscribeWithSelector } from 'zustand/middleware'

export interface PacketData {
  timestamp: number
  src_ip: string
  dst_ip: string
  src_port: number
  dst_port: number
  protocol: string
  length: number
  tcp_flags: string
  ttl: number
}

export interface FlowFeatures {
  flow_id: string
  src_ip: string
  dst_ip: string
  src_port: number
  dst_port: number
  protocol: string
  packets_fwd: number
  packets_bwd: number
  bytes_fwd: number
  bytes_bwd: number
  duration_ms: number
  threat_score: number
  labels: string[]
  timestamp: number
  iat_fwd_mean?: number
  iat_bwd_mean?: number
  pkt_len_fwd_mean?: number
  pkt_len_bwd_mean?: number
  payload_entropy_fwd_mean?: number
  payload_entropy_bwd_mean?: number
  tls_sni?: string
  http_host?: string
  dns_queries?: string[]
}

export interface AnomalyEvent {
  flow_id: string
  timestamp: number
  is_anomaly: boolean
  anomaly_score: number
  threat_level: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO'
  features: Record<string, any>
}

export interface DashboardStats {
  timestamp: number
  active_flows: number
  flows_last_minute: number
  anomalies_last_5min: number
  anomalies_by_level: Record<string, number>
  top_talkers: Array<{ ip: string; bytes: number }>
  protocol_distribution: Record<string, number>
  anomaly_rate: number
}

export interface GlobeArc {
  src: string
  dst: string
  score: number
  level: string
  timestamp: number
}

export interface GlobeData {
  arcs: GlobeArc[]
  timestamp: number
}

export interface AlertEvent {
  id: string
  type: string
  severity: string
  message: string
  timestamp: number
  acknowledged: boolean
  flow_id?: string
}

interface AppState {
  connected: boolean
  connecting: boolean
  connectionError: string | null
  flows: Map<string, any>
  recentFlows: any[]
  anomalies: any[]
  recentAnomalies: any[]
  threats: any[]
  packets: any[]
  dashboardStats: any
  globeData: any
  stats: any
  alerts: any[]
  selectedFlow: any
  selectedAnomaly: any
  selectedThreat: any
  selectedPacket: any
  timeRange: number
  timeWindow: number
  filters: {
    protocol: string[]
    threatLevel: string[]
    minScore: number
    searchQuery: string
  }
  sidebarOpen: boolean
  activeTab: string
  globeRotation: { x: number; y: number; z: number }
  globeZoom: number
  showHeatmap: boolean
  showParticles: boolean
  showArcs: boolean
  showThreatsOnly: boolean
  autoRotate: boolean
  arcTimeWindow: number
}

const initialState: AppState = {
  connected: false,
  connecting: false,
  connectionError: null,
  flows: new Map(),
  recentFlows: [],
  anomalies: [],
  recentAnomalies: [],
  threats: [],
  packets: [],
  dashboardStats: null,
  globeData: null,
  stats: null,
  alerts: [],
  selectedFlow: null,
  selectedAnomaly: null,
  selectedThreat: null,
  selectedPacket: null,
  timeRange: 300000,
  timeWindow: 300000,
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
  showArcs: true,
  showThreatsOnly: false,
  autoRotate: true,
  arcTimeWindow: 60000
}

type StoreActions = {
  setConnected: (connected: boolean) => void
  setConnecting: (connecting: boolean) => void
  setConnectionError: (error: string | null) => void
  addFlow: (flow: any) => void
  updateFlow: (flowId: string, updates: any) => void
  removeFlow: (flowId: string) => void
  setRecentFlows: (flows: any[]) => void
  selectFlow: (flow: any | null) => void
  addAnomaly: (anomaly: any) => void
  addThreat: (threat: any) => void
  setThreats: (threats: any[]) => void
  setRecentAnomalies: (anomalies: any[]) => void
  selectAnomaly: (anomaly: any | null) => void
  selectThreat: (threat: any | null) => void
  setDashboardStats: (stats: any) => void
  setGlobeData: (data: any) => void
  setStats: (stats: any) => void
  addPacket: (packet: any) => void
  addAlert: (alert: any) => void
  acknowledgeAlert: (alertId: string) => void
  clearAlerts: () => void
  setTimeRange: (timeRange: number) => void
  setTimeWindow: (timeWindow: number) => void
  setFilters: (filters: any) => void
  setSidebarOpen: (sidebarOpen: boolean) => void
  setActiveTab: (activeTab: any) => void
  setGlobeRotation: (rotation: { x: number; y: number; z: number }) => void
  setGlobeZoom: (zoom: number) => void
  toggleHeatmap: () => void
  toggleParticles: () => void
  setShowArcs: (showArcs: boolean) => void
  setShowThreatsOnly: (showThreatsOnly: boolean) => void
  setAutoRotate: (autoRotate: boolean) => void
  setArcTimeWindow: (window: number) => void
  setSelectedThreat: (threat: any | null) => void
  setSelectedPacket: (packet: any | null) => void
  reset: () => void
}

export const useStore = create<AppState & StoreActions>()(
  subscribeWithSelector((set, get) => ({
    ...initialState,

    setConnected: (connected: boolean) => set({ connected }),
    setConnecting: (connecting: boolean) => set({ connecting }),
    setConnectionError: (error: string | null) => set({ connectionError: error }),

    addFlow: (flow: any) => set((state: AppState) => {
      const newFlows = new Map(state.flows)
      newFlows.set(flow.flow_id, flow)
      const recentFlows = [flow, ...state.recentFlows].slice(0, 1000)
      return { flows: newFlows, recentFlows }
    }),

    updateFlow: (flowId: string, updates: any) => set((state: AppState) => {
      const flow = state.flows.get(flowId)
      if (!flow) return state
      const updated = { ...flow, ...updates }
      const newFlows = new Map(state.flows)
      newFlows.set(flowId, updated)
      const recentFlows = state.recentFlows.map(f => f.flow_id === flowId ? updated : f)
      return { flows: newFlows, recentFlows }
    }),

    removeFlow: (flowId: string) => set((state: AppState) => {
      const newFlows = new Map(state.flows)
      newFlows.delete(flowId)
      const recentFlows = state.recentFlows.filter(f => f.flow_id !== flowId)
      return { flows: newFlows, recentFlows }
    }),

    setRecentFlows: (flows: any[]) => set({ recentFlows: flows }),
    selectFlow: (flow: any | null) => set({ selectedFlow: flow }),

    addAnomaly: (anomaly: any) => set((state: AppState) => {
      const anomalies = [anomaly, ...state.anomalies].slice(0, 5000)
      const recentAnomalies = [anomaly, ...state.recentAnomalies].slice(0, 100)
      const threats = [anomaly, ...state.threats].slice(0, 5000)

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
        return { anomalies, recentAnomalies, threats, alerts: [alert, ...state.alerts].slice(0, 200) }
      }
      return { anomalies, recentAnomalies, threats }
    }),

    addThreat: (threat: any) => set((state: AppState) => ({
      threats: [threat, ...state.threats].slice(0, 5000)
    })),

    setThreats: (threats: any[]) => set({ threats }),

    setRecentAnomalies: (anomalies: any[]) => set({ recentAnomalies: anomalies }),
    selectAnomaly: (anomaly: any | null) => set({ selectedAnomaly: anomaly }),
    selectThreat: (threat: any | null) => set({ selectedThreat: threat }),

    setDashboardStats: (stats: any) => set({ dashboardStats: stats }),
    setGlobeData: (data: any) => set({ globeData: data }),
    setStats: (stats: any) => set({ stats }),

    addPacket: (packet: any) => set((state: AppState) => ({
      packets: [packet, ...state.packets].slice(0, 1000)
    })),

    addAlert: (alert: any) => set((state: AppState) => ({ alerts: [alert, ...state.alerts].slice(0, 200) })),
    acknowledgeAlert: (alertId: string) => set((state: AppState) => ({
      alerts: state.alerts.map(a => a.id === alertId ? { ...a, acknowledged: true } : a)
    })),
    clearAlerts: () => set({ alerts: [] }),

    setTimeRange: (timeRange: number) => set({ timeRange }),
    setTimeWindow: (timeWindow: number) => set({ timeWindow }),
    setFilters: (filters: any) => set((state: AppState) => ({ filters: { ...state.filters, ...filters } })),
    setSidebarOpen: (sidebarOpen: boolean) => set({ sidebarOpen }),
    setActiveTab: (activeTab: any) => set({ activeTab }),

    setGlobeRotation: (rotation: { x: number; y: number; z: number }) => set({ globeRotation: rotation }),
    setGlobeZoom: (zoom: number) => set({ globeZoom: Math.max(0.5, Math.min(3, zoom)) }),
    toggleHeatmap: () => set((state: AppState) => ({ showHeatmap: !state.showHeatmap })),
    toggleParticles: () => set((state: AppState) => ({ showParticles: !state.showParticles })),
    setShowArcs: (showArcs: boolean) => set({ showArcs }),
    setShowThreatsOnly: (showThreatsOnly: boolean) => set({ showThreatsOnly }),
    setAutoRotate: (autoRotate: boolean) => set({ autoRotate }),
    setArcTimeWindow: (window: number) => set({ arcTimeWindow: window }),
    setSelectedThreat: (threat: any | null) => set({ selectedThreat: threat }),
    setSelectedPacket: (packet: any | null) => set({ selectedPacket: packet }),

    reset: () => set(initialState)
  }))
)