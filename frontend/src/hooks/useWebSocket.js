import { useEffect, useRef, useCallback } from 'react'
import { useStore } from './useStore'

const WS_URL = (import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws') + '/'
const RECONNECT_DELAY = 3000
const MAX_RECONNECT_ATTEMPTS = 10

export function useWebSocket(clientId = `client-${Date.now()}`) {
  const wsRef = useRef(null)
  const reconnectAttempts = useRef(0)
  const reconnectTimeoutRef = useRef(null)
  const messageHandlers = useRef(new Map())
  
  const {
    setConnected,
    setConnecting,
    setConnectionError,
    addFlow,
    addAnomaly,
    setDashboardStats,
    setGlobeData,
    addAlert
  } = useStore()

  const registerHandler = useCallback((type, handler) => {
    messageHandlers.current.set(type, handler)
  }, [])

  const sendMessage = useCallback((message) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message))
    }
  }, [])

  const subscribe = useCallback((topics) => {
    sendMessage({ type: 'subscribe', topics })
  }, [sendMessage])

  const unsubscribe = useCallback((topics) => {
    sendMessage({ type: 'unsubscribe', topics })
  }, [sendMessage])

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return
    
    setConnecting(true)
    setConnectionError(null)
    
    const ws = new WebSocket(`${WS_URL}${clientId}`)
    wsRef.current = ws

    ws.onopen = () => {
      console.log('[WS] Connected')
      setConnected(true)
      setConnecting(false)
      reconnectAttempts.current = 0
      
      subscribe(['flows', 'anomalies', 'alerts', 'stats', 'globe'])
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        const handler = messageHandlers.current.get(data.type)
        if (handler) {
          handler(data.payload)
        } else {
          switch (data.type) {
            case 'FLOW_UPDATE':
              addFlow(data.payload)
              break
            case 'ANOMALY':
              addAnomaly(data.payload)
              break
            case 'STATS':
              setDashboardStats(data.payload)
              break
            case 'GLOBE_SYNC':
              setGlobeData(data.payload)
              break
            case 'ALERT':
              addAlert(data.payload)
              break
            case 'pong':
              break
            default:
              console.log('[WS] Unknown message type:', data.type)
          }
        }
      } catch (e) {
        console.error('[WS] Message parse error:', e)
      }
    }

    ws.onclose = (event) => {
      console.log('[WS] Disconnected:', event.code, event.reason)
      setConnected(false)
      setConnecting(false)
      
      if (reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS) {
        reconnectAttempts.current++
        const delay = Math.min(RECONNECT_DELAY * Math.pow(1.5, reconnectAttempts.current - 1), 30000)
        console.log(`[WS] Reconnecting in ${delay}ms (attempt ${reconnectAttempts.current})`)
        reconnectTimeoutRef.current = setTimeout(connect, delay)
      } else {
        setConnectionError('Max reconnection attempts reached')
      }
    }

    ws.onerror = (error) => {
      console.error('[WS] Error:', error)
      setConnectionError('Connection error')
    }
  }, [clientId, setConnected, setConnecting, setConnectionError, subscribe, addFlow, addAnomaly, setDashboardStats, setGlobeData, addAlert])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    if (wsRef.current) {
      wsRef.current.close(1000, 'Client disconnect')
      wsRef.current = null
    }
    setConnected(false)
    setConnecting(false)
  }, [setConnected, setConnecting])

  useEffect(() => {
    connect()
    return () => disconnect()
  }, [connect, disconnect])

  return {
    connected: useStore(state => state.connected),
    connecting: useStore(state => state.connecting),
    connectionError: useStore(state => state.connectionError),
    sendMessage,
    subscribe,
    unsubscribe,
    registerHandler,
    reconnect: connect
  }
}

export function useWebSocketMessage(type, handler, deps = []) {
  const { registerHandler } = useWebSocket()
  
  useEffect(() => {
    registerHandler(type, handler)
    return () => {
      const handlers = registerHandler.handlers || new Map()
      handlers.delete(type)
    }
  }, [type, handler, registerHandler, ...deps])
}