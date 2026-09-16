import { Component, ErrorInfo, ReactNode } from 'react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null
  }

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo)
  }

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }
      return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-cyber-bg">
          <div className="panel max-w-2xl mx-4 p-8 text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-cyber-danger/20 flex items-center justify-center border border-cyber-danger/30">
              <svg className="w-10 h-10 text-cyber-danger" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <h2 className="font-mono text-xl font-bold text-cyber-danger mb-2">APPLICATION ERROR</h2>
            <p className="text-cyber-textDim mb-4">The dashboard encountered an unexpected error.</p>
            <div className="panel p-4 mb-4 text-left max-h-60 overflow-auto">
              <p className="font-mono text-xs text-cyber-danger mb-2">Error:</p>
              <pre className="font-mono text-xs text-cyber-textDim overflow-auto whitespace-pre-wrap">
                {this.state.error?.message}
              </pre>
              <p className="font-mono text-xs text-cyber-danger mt-4 mb-2">Stack Trace:</p>
              <pre className="font-mono text-xs text-cyber-textDim overflow-auto whitespace-pre-wrap max-h-40">
                {this.state.error?.stack}
              </pre>
            </div>
            <div className="flex gap-2 justify-center">
              <button 
                onClick={() => window.location.reload()}
                className="btn-primary"
              >
                RELOAD APPLICATION
              </button>
              <button 
                onClick={() => this.setState({ hasError: false, error: null })}
                className="btn-ghost"
              >
                DISMISS
              </button>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}