import { useStore } from '../../hooks/useStore'

export function ThreatMatrix() {
  const { threats } = useStore()
  
  const threatTypes = threats.reduce((acc: Record<string, number>, t: any) => {
    const type = t.threat_type || 'UNKNOWN'
    acc[type] = (acc[type] || 0) + 1
    return acc
  }, {})
  
  const sortedTypes = Object.entries(threatTypes)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
  
  return (
    <div className="border-t border-cyber-panelBorder p-4">
      <h3 className="panel-title mb-3">THREAT MATRIX</h3>
      <div className="space-y-2">
        {sortedTypes.length === 0 ? (
          <div className="text-center text-cyber-textDim py-4 text-xs">
            NO THREATS CLASSIFIED
          </div>
        ) : (
          sortedTypes.map(([type, count]) => (
            <div key={type} className="group">
              <div className="flex items-center justify-between mb-1">
                <span className="font-mono text-xs text-cyber-textDim">{type}</span>
                <span className="font-mono text-xs text-cyber-primary">{count}</span>
              </div>
              <div className="h-2 bg-cyber-bgSecondary rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-cyber-primary to-cyber-danger rounded-full transition-all duration-500"
                  style={{ width: `${(count / sortedTypes[0][1]) * 100}%` }}
                />
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}