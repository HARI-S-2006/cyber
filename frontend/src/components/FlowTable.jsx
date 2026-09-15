import React, { useMemo, useState } from 'react'
import { useStore } from '../hooks/useStore'

const COLUMNS = [
  { key: 'flow_id', label: 'Flow ID', width: '200px' },
  { key: 'src_ip', label: 'Source IP', width: '130px' },
  { key: 'src_port', label: 'SPort', width: '70px' },
  { key: 'dst_ip', label: 'Dest IP', width: '130px' },
  { key: 'dst_port', label: 'DPort', width: '70px' },
  { key: 'protocol', label: 'Proto', width: '70px' },
  { key: 'packets_total', label: 'Packets', width: '80px' },
  { key: 'bytes_total', label: 'Bytes', width: '100px' },
  { key: 'duration_ms', label: 'Duration', width: '90px' },
  { key: 'threat_score', label: 'Threat', width: '90px' },
  { key: 'labels', label: 'Labels', width: '150px' }
]

export default function FlowTable({ flows }) {
  const { selectedFlow, selectFlow } = useStore()
  const [sortConfig, setSortConfig] = useState({ key: 'last_time', direction: 'desc' })
  
  const sortedFlows = useMemo(() => {
    return [...flows].sort((a, b) => {
      const aVal = a[sortConfig.key]
      const bVal = b[sortConfig.key]
      if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1
      if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1
      return 0
    })
  }, [flows, sortConfig])
  
  const handleSort = (key) => {
    setSortConfig(prev => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc'
    }))
  }
  
  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
  }
  
  const formatDuration = (ms) => {
    if (ms < 1000) return `${ms.toFixed(0)}ms`
    if (ms < 60000) return `${(ms/1000).toFixed(1)}s`
    return `${(ms/60000).toFixed(1)}m`
  }
  
  const getThreatColor = (score) => {
    if (score > 0.8) return 'text-red-400'
    if (score > 0.6) return 'text-orange-400'
    if (score > 0.4) return 'text-yellow-400'
    if (score > 0.2) return 'text-green-400'
    return 'text-gray-400'
  }
  
  return (
    <div className="flex-1 overflow-auto">
      <div className="table-container">
        <table>
          <thead>
            <tr>
              {COLUMNS.map(col => (
                <th
                  key={col.key}
                  style={{ width: col.width }}
                  onClick={() => handleSort(col.key)}
                  className="cursor-pointer select-none"
                >
                  <div className="flex items-center gap-1">
                    {col.label}
                    {sortConfig.key === col.key && (
                      <span>{sortConfig.direction === 'asc' ? '↑' : '↓'}</span>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sortedFlows.slice(0, 500).map(flow => (
              <tr
                key={flow.flow_id}
                onClick={() => selectFlow(flow)}
                className={`cursor-pointer transition-colors ${
                  selectedFlow?.flow_id === flow.flow_id 
                    ? 'bg-cyan-500/10' 
                    : 'hover:bg-gray-800/50'
                }`}
              >
                <td className="truncate font-mono text-xs" title={flow.flow_id}>
                  {flow.flow_id}
                </td>
                <td className="font-mono text-sm">{flow.src_ip}</td>
                <td className="font-mono text-sm">{flow.src_port}</td>
                <td className="font-mono text-sm">{flow.dst_ip}</td>
                <td className="font-mono text-sm">{flow.dst_port}</td>
                <td>
                  <span className={`badge badge-info text-xs`}>{flow.protocol}</span>
                </td>
                <td className="font-mono text-sm">
                  {(flow.packets_fwd + flow.packets_bwd).toLocaleString()}
                </td>
                <td className="font-mono text-sm">
                  {formatBytes(flow.bytes_fwd + flow.bytes_bwd)}
                </td>
                <td className="font-mono text-sm">
                  {formatDuration(flow.duration_ms)}
                </td>
                <td>
                  <div className="flex items-center gap-2">
                    <div className="w-20 h-2 bg-gray-700 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-green-400 via-yellow-400 to-red-400 transition-all"
                        style={{ width: `${flow.threat_score * 100}%` }}
                      ></div>
                    </div>
                    <span className={`font-mono text-xs ${getThreatColor(flow.threat_score)}`}>
                      {(flow.threat_score * 100).toFixed(0)}%
                    </span>
                  </div>
                </td>
                <td>
                  <div className="flex flex-wrap gap-1">
                    {flow.labels?.slice(0, 3).map(label => (
                      <span key={label} className="badge badge-info text-xs">
                        {label}
                      </span>
                    ))}
                    {flow.labels && flow.labels.length > 3 && (
                      <span className="badge badge-info text-xs">
                        +{flow.labels.length - 3}
                      </span>
                    )}
                  </div>
                </td>
              </tr>
            ))}
            {sortedFlows.length === 0 && (
              <tr>
                <td colSpan={COLUMNS.length} className="text-center py-12 text-gray-500">
                  No flows match current filters
                </td>
              </tr>
            )}
            {sortedFlows.length > 500 && (
              <tr>
                <td colSpan={COLUMNS.length} className="text-center py-4 text-gray-500">
                  Showing 500 of {sortedFlows.length} flows
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      
      {selectedFlow && <FlowDetailPanel flow={selectedFlow} onClose={() => selectFlow(null)} />}
    </div>
  )
}

function FlowDetailPanel({ flow, onClose }) {
  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }
  
  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/50 p-4">
      <div className="glass-panel w-full max-w-2xl max-h-[90vh] overflow-auto sm:rounded-xl">
        <div className="flex items-center justify-between p-4 border-b border-gray-800">
          <h3 className="font-semibold">Flow Details</h3>
          <button onClick={onClose} className="p-2 hover:bg-gray-800 rounded">✕</button>
        </div>
        
        <div className="p-4 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <DetailRow label="Flow ID" value={flow.flow_id} />
            <DetailRow label="Threat Score" value={`${(flow.threat_score * 100).toFixed(1)}%`} />
            <DetailRow label="Source" value={`${flow.src_ip}:${flow.src_port}`} />
            <DetailRow label="Destination" value={`${flow.dst_ip}:${flow.dst_port}`} />
            <DetailRow label="Protocol" value={flow.protocol} />
            <DetailRow label="Duration" value={`${(flow.duration_ms / 1000).toFixed(2)}s`} />
          </div>
          
          <div className="border-t border-gray-800 pt-4 grid grid-cols-2 gap-4">
            <DetailRow label="Packets Fwd/Bwd" value={`${flow.packets_fwd} / ${flow.packets_bwd}`} />
            <DetailRow label="Bytes Fwd/Bwd" value={`${formatBytes(flow.bytes_fwd)} / ${formatBytes(flow.bytes_bwd)}`} />
            <DetailRow label="IAT Fwd Mean" value={`${flow.iat_fwd_mean?.toFixed(1) || 0}ms`} />
            <DetailRow label="IAT Bwd Mean" value={`${flow.iat_bwd_mean?.toFixed(1) || 0}ms`} />
            <DetailRow label="Pkt Len Fwd Avg" value={`${flow.pkt_len_fwd_mean?.toFixed(0) || 0}B`} />
            <DetailRow label="Pkt Len Bwd Avg" value={`${flow.pkt_len_bwd_mean?.toFixed(0) || 0}B`} />
            <DetailRow label="Entropy Fwd" value={flow.payload_entropy_fwd_mean?.toFixed(2) || 'N/A'} />
            <DetailRow label="Entropy Bwd" value={flow.payload_entropy_bwd_mean?.toFixed(2) || 'N/A'} />
          </div>
          
          {(flow.tls_sni || flow.http_host || flow.dns_queries?.length) && (
            <div className="border-t border-gray-800 pt-4 space-y-2">
              <h4 className="font-medium">Application Layer</h4>
              {flow.tls_sni && <DetailRow label="TLS SNI" value={flow.tls_sni} />}
              {flow.http_host && <DetailRow label="HTTP Host" value={flow.http_host} />}
              {flow.dns_queries?.length && (
                <DetailRow label="DNS Queries" value={flow.dns_queries.join(', ')} />
              )}
            </div>
          )}
          
          {flow.labels?.length && (
            <div className="border-t border-gray-800 pt-4">
              <h4 className="font-medium mb-2">Threat Labels</h4>
              <div className="flex flex-wrap gap-2">
                {flow.labels.map(label => (
                  <span key={label} className="badge badge-critical">{label}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function DetailRow({ label, value }) {
  return (
    <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
      <span className="text-xs text-gray-400">{label}</span>
      <span className="font-mono text-sm text-gray-200 truncate max-w-[200px]">{value}</span>
    </div>
  )
}