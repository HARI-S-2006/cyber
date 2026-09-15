import React from 'react'
import { useStore } from '../hooks/useStore'
import { useWebSocket } from '../hooks/useWebSocket'

export default function ConnectionStatus() {
  const { connected, connecting, connectionError } = useStore()
  const { reconnect } = useWebSocket()
  
  if (connected) return null
  
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className="glass-panel max-w-md w-full p-8 rounded-xl text-center">
        <div className="text-6xl mb-4">
          {connecting ? '🔄' : '🔌'}
        </div>
        <h2 className="text-xl font-bold mb-2">
          {connecting ? 'Connecting...' : 'Disconnected'}
        </h2>
        <p className="text-gray-400 mb-6">
          {connectionError || 'Waiting for connection to the threat detection backend...'}
        </p>
        {!connecting && (
          <button
            onClick={reconnect}
            className="btn btn-primary"
          >
            Retry Connection
          </button>
        )}
        {connecting && (
          <div className="flex justify-center gap-2 mt-4">
            <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" style={{ animationDelay: '0ms' }}></div>
            <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" style={{ animationDelay: '150ms' }}></div>
            <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" style={{ animationDelay: '300ms' }}></div>
          </div>
        )}
      </div>
    </div>
  )
}