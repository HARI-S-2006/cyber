import { useEffect, useRef, useCallback, useState } from 'react'
import { useStore } from './useStore'

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const reconnectAttempts = useRef(0)
  const [connected, setConnected] = useState(false)
  const [connecting, setConnecting] = useState(false)
  
  const { setConnected: setStoreConnected, setConnecting: setStoreConnecting, addPacket, addThreat, setStats, setConnectionError } = useStore()
  
  const WS_URL = `ws://localhost:8000/ws/live`
  const MAX_RECONNECT_ATTEMPTS = 10
  const RECONNECT_DELAY = 3000
  
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return
    
    setConnecting(true)
    setStoreConnecting(true)
    setConnectionError(null)
    
    try {
      const ws = new WebSocket('ws://localhost:8000/ws/live')
      wsRef.current = ws
      
      ws.onopen = () => {
        console.log('WebSocket connected')
        setConnected(true)
        setStoreConnected(true)
        setConnecting(false)
        setStoreConnecting(false)
        reconnectAttempts.current = 0
        
        // Subscribe to channels
        ws.send(JSON.stringify({ type: 'subscribe', channel: 'packets' }))
        ws.send(JSON.stringify({ type: 'subscribe', channel: 'threats' }))
        ws.send(JSON.stringify({ type: 'subscribe', channel: 'stats' }))
      }
      
      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          handleMessage(message)
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e)
        }
      }
      
      ws.onclose = () => {
        console.log('WebSocket disconnected')
        setConnected(false)
        setStoreConnected(false)
        setConnecting(false)
        setStoreConnecting(false)
        
        if (reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttempts.current++
          const delay = RECONNECT_DELAY * Math.min(reconnectAttempts.current, 5)
          console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttempts.current})`)
          reconnectTimeoutRef.current = setTimeout(connect, delay)
        } else {
          setConnectionError('Max reconnection attempts reached')
        }
      }
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        setConnectionError('Connection error')
      }
    } catch (error) {
      console.error('Failed to create WebSocket:', error)
      setConnecting(false)
      setStoreConnecting(false)
      setConnectionError('Failed to connect')
    }
  }, [])
  
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    
    if (wsRef.current) {
      wsRef.current.close(1000, 'Client disconnect')
      wsRef.current = null
    }
    
    setConnected(false)
    setStoreConnected(false)
    setConnecting(false)
    setStoreConnecting(false)
    reconnectAttempts.current = 0
  }, [])
  
  const handleMessage = useCallback((message: any) => {
    switch (message.type) {
      case 'packet':
        useStore.getState().addPacket(message.data)
        break
      case 'threat':
        useStore.getState().addThreat(message.data)
        break
      case 'stats':
        useStore.getState().setStats(message.data)
        break
      case 'welcome':
        console.log('Welcome:', message.data)
        break
      case 'pong':
        break
      case 'error':
        console.error('Server error:', message.data)
        setConnectionError(message.data?.message || 'Server error')
        break
      default:
        console.log('Unknown message type:', message.type)
    }
  }, [])
  
  const send = useCallback((message: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message))
    }
  }, [])
  
  const subscribe = useCallback((channel: string) => {
    send({ type: 'subscribe', channel })
  }, [])
  
  const unsubscribe = useCallback((channel: string) => {
    send({ type: 'unsubscribe', channel })
  }, [])
  
  const ping = useCallback(() => {
    send({ type: 'ping' })
  }, [])
  
  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmount')
      }
    }
  }, [])
  
  return {
    connected,
    connecting,
    connect,
    disconnect,
    send,
    subscribe,
    unsubscribe,
    ping,
  }
}