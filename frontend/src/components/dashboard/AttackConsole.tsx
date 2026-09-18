import React, { useState } from 'react'

export function AttackConsole() {
  const [loading, setLoading] = useState(false)
  const [activeAttack, setActiveAttack] = useState<string | null>(null)

  const handleAttack = async (type: string) => {
    setLoading(true)
    try {
      if (activeAttack === type) {
        // Stop attack
        await fetch('http://localhost:8000/api/v1/simulation/stop', { method: 'POST' })
        setActiveAttack(null)
      } else {
        // Start attack
        await fetch('http://localhost:8000/api/v1/simulation/start', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ attack_type: type, rate: 50, duration: 60, mode: 'SYNTHETIC' })
        })
        setActiveAttack(type)
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="absolute top-20 left-4 z-10 glass-panel p-4 rounded border border-cyan-500/30 w-64">
      <h3 className="text-cyan-400 font-bold mb-4 font-mono border-b border-cyan-500/30 pb-2">ATTACK CONSOLE</h3>
      <div className="flex flex-col gap-2">
        {['syn', 'udp', 'icmp', 'portscan', 'bruteforce'].map(type => (
          <button
            key={type}
            disabled={loading}
            onClick={() => handleAttack(type)}
            className={`px-3 py-2 text-sm font-mono border transition-colors ${
              activeAttack === type 
                ? 'bg-red-500/20 text-red-400 border-red-500/50' 
                : 'bg-transparent text-cyan-400 border-cyan-500/30 hover:bg-cyan-500/10'
            }`}
          >
            {activeAttack === type ? 'STOP ' : 'LAUNCH '} {type.toUpperCase()}
          </button>
        ))}
      </div>
    </div>
  )
}
