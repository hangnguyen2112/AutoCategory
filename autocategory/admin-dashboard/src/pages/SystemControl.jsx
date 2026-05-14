import { useEffect, useState } from 'react'
import { systemAPI } from '../services/api'
import {
  Server,
  Activity,
  RefreshCw,
  Play,
  Square,
  RotateCw,
  Database,
  HardDrive,
  Trash2,
} from 'lucide-react'
import toast from 'react-hot-toast'

function ServiceCard({ name, status, onControl }) {
  const isRunning = status?.status === 'running' || status?.status === 'healthy'
  const isError = status?.status === 'error' || status?.status === 'unhealthy'
  
  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Server className="h-5 w-5 text-gray-600 dark:text-gray-400" />
          <h3 className="font-semibold text-gray-900 dark:text-white">{name}</h3>
        </div>
        <span
          className={`badge ${
            isRunning ? 'badge-success' : 
            isError ? 'badge-danger' : 
            'badge-secondary'
          }`}
        >
          {isRunning ? 'Running' : 
           isError ? 'Error' : 
           'Stopped'}
        </span>
      </div>

      {status && (
        <div className="space-y-2 mb-4 text-sm">
          {status.cpu_percent !== undefined && (
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">CPU:</span>
              <span className="font-medium text-gray-900 dark:text-white">
                {status.cpu_percent?.toFixed(1)}%
              </span>
            </div>
          )}
          {status.memory_mb !== undefined && (
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Memory:</span>
              <span className="font-medium text-gray-900 dark:text-white">
                {status.memory_mb?.toFixed(0)} MB
              </span>
            </div>
          )}
          {status.uptime && (
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Uptime:</span>
              <span className="font-medium text-gray-900 dark:text-white">{status.uptime}</span>
            </div>
          )}
          {status.error_message && (
            <div className="text-red-600 dark:text-red-400 text-xs mt-2">
              {status.error_message}
            </div>
          )}
        </div>
      )}

      <div className="flex gap-2">
        <button
          onClick={() => onControl(name.toLowerCase(), 'start')}
          disabled={isRunning}
          className="btn btn-primary btn-sm flex items-center gap-1 flex-1"
          title="Start"
        >
          <Play className="h-3 w-3" />
          Start
        </button>
        <button
          onClick={() => onControl(name.toLowerCase(), 'stop')}
          disabled={!isRunning}
          className="btn btn-danger btn-sm flex items-center gap-1 flex-1"
          title="Stop"
        >
          <Square className="h-3 w-3" />
          Stop
        </button>
        <button
          onClick={() => onControl(name.toLowerCase(), 'restart')}
          className="btn btn-secondary btn-sm flex items-center gap-1 flex-1"
          title="Restart"
        >
          <RotateCw className="h-3 w-3" />
          Restart
        </button>
      </div>
    </div>
  )
}

export default function SystemControl() {
  const [health, setHealth] = useState(null)
  const [metrics, setMetrics] = useState(null)
  const [dbStats, setDbStats] = useState(null)
  const [systemInfo, setSystemInfo] = useState(null)
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [autoRefresh, setAutoRefresh] = useState(true)

  const fetchData = async () => {
    try {
      setLoading(true)
      const [healthRes, metricsRes, dbStatsRes, infoRes] = await Promise.all([
        systemAPI.health(),
        systemAPI.metrics().catch(() => ({ data: null })),
        systemAPI.databaseStats().catch(() => ({ data: null })),
        systemAPI.info().catch(() => ({ data: null })),
      ])

      setHealth(healthRes.data)
      setMetrics(metricsRes.data)
      setDbStats(dbStatsRes.data)
      setSystemInfo(infoRes.data)
    } catch (error) {
      toast.error('Failed to load system data!')
    } finally {
      setLoading(false)
    }
  }

  const fetchLogs = async () => {
    try {
      const response = await systemAPI.logs({ lines: 50 })
      setLogs(response.data.logs || [])
    } catch (error) {
      console.error('Failed to fetch logs:', error)
    }
  }

  useEffect(() => {
    fetchData()
    fetchLogs()
  }, [])

  useEffect(() => {
    if (!autoRefresh) return

    const interval = setInterval(() => {
      fetchData()
    }, 30000) // Refresh every 30s

    return () => clearInterval(interval)
  }, [autoRefresh])

  const handleServiceControl = async (service, action) => {
    try {
      toast.loading(`${action}ing ${service}...`, { id: 'control' })
      await systemAPI.serviceControl({ service, action })
      toast.success(`${service} ${action}ed!`, { id: 'control' })
      setTimeout(fetchData, 2000) // Refresh after 2s
    } catch (error) {
      toast.error(`Failed to ${action} ${service}!`, { id: 'control' })
    }
  }

  const handleClearCache = async (cacheType) => {
    if (!confirm(`Clear ${cacheType} cache?`)) return

    try {
      toast.loading('Clearing cache...', { id: 'cache' })
      await systemAPI.clearCache({ cache_type: cacheType })
      toast.success('Cache cleared!', { id: 'cache' })
    } catch (error) {
      toast.error('Failed to clear cache!', { id: 'cache' })
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Activity className="h-8 w-8" />
            System Control
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Monitor and manage system services
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`btn ${autoRefresh ? 'btn-primary' : 'btn-secondary'} flex items-center gap-2`}
          >
            <RefreshCw className={`h-4 w-4 ${autoRefresh ? 'animate-spin' : ''}`} />
            Auto Refresh: {autoRefresh ? 'ON' : 'OFF'}
          </button>
          <button onClick={fetchData} className="btn btn-secondary flex items-center gap-2">
            <RefreshCw className="h-4 w-4" />
            Refresh Now
          </button>
        </div>
      </div>

      {loading && !health ? (
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="h-8 w-8 animate-spin text-primary-600" />
        </div>
      ) : (
        <>
          {/* Overall Status */}
          <div className="card">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                  System Status
                </h2>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Overall system health
                </p>
              </div>
              <span
                className={`badge text-lg ${
                  health?.overall_status === 'healthy' ? 'badge-success' : 'badge-danger'
                }`}
              >
                {health?.overall_status === 'healthy' ? '✓ Healthy' : '⚠ Degraded'}
              </span>
            </div>
          </div>

          {/* Services */}
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Services</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {health?.services?.map((service) => (
                <ServiceCard
                  key={service.name}
                  name={service.name.toUpperCase()}
                  status={service}
                  onControl={handleServiceControl}
                />
              ))}
            </div>
          </div>

          {/* System Metrics */}
          {metrics && (
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                System Metrics
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="card">
                  <div className="text-sm text-gray-600 dark:text-gray-400">CPU Usage</div>
                  <div className="text-2xl font-bold text-blue-600">
                    {metrics.cpu_percent?.toFixed(1)}%
                  </div>
                </div>
                <div className="card">
                  <div className="text-sm text-gray-600 dark:text-gray-400">Memory Usage</div>
                  <div className="text-2xl font-bold text-green-600">
                    {metrics.memory_percent?.toFixed(1)}%
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    {metrics.memory_used_mb?.toFixed(0)} / {metrics.memory_total_mb?.toFixed(0)} MB
                  </div>
                </div>
                <div className="card">
                  <div className="text-sm text-gray-600 dark:text-gray-400">Disk Usage</div>
                  <div className="text-2xl font-bold text-purple-600">
                    {metrics.disk_percent?.toFixed(1)}%
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    {(metrics.disk_used_gb)?.toFixed(1)} / {(metrics.disk_total_gb)?.toFixed(1)} GB
                  </div>
                </div>
                <div className="card">
                  <div className="text-sm text-gray-600 dark:text-gray-400">System Load</div>
                  <div className="text-2xl font-bold text-orange-600">
                    {metrics.load_avg?.join(', ')}
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">1m, 5m, 15m</div>
                </div>
              </div>
            </div>
          )}

          {/* Database Stats */}
          {dbStats && (
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <Database className="h-5 w-5" />
                Database Statistics
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="card">
                  <div className="text-sm text-gray-600 dark:text-gray-400">Total Connections</div>
                  <div className="text-2xl font-bold text-blue-600">{dbStats.connections}</div>
                </div>
                <div className="card">
                  <div className="text-sm text-gray-600 dark:text-gray-400">Active Queries</div>
                  <div className="text-2xl font-bold text-green-600">{dbStats.active_queries}</div>
                </div>
                <div className="card">
                  <div className="text-sm text-gray-600 dark:text-gray-400">Database Size</div>
                  <div className="text-2xl font-bold text-purple-600">
                    {dbStats.size_mb?.toFixed(0)} MB
                  </div>
                </div>
                <div className="card">
                  <div className="text-sm text-gray-600 dark:text-gray-400">Total Tables</div>
                  <div className="text-2xl font-bold text-orange-600">{dbStats.tables}</div>
                </div>
              </div>
            </div>
          )}

          {/* Cache Management */}
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
              <HardDrive className="h-5 w-5" />
              Cache Management
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="card">
                <h3 className="font-semibold text-gray-900 dark:text-white mb-2">Redis Cache</h3>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                  Clear rate limiting and session data
                </p>
                <button
                  onClick={() => handleClearCache('redis')}
                  className="btn btn-danger btn-sm flex items-center gap-2 w-full"
                >
                  <Trash2 className="h-4 w-4" />
                  Clear Redis
                </button>
              </div>
              <div className="card">
                <h3 className="font-semibold text-gray-900 dark:text-white mb-2">Vector Cache</h3>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                  Clear Qdrant embeddings cache
                </p>
                <button
                  onClick={() => handleClearCache('vector')}
                  className="btn btn-danger btn-sm flex items-center gap-2 w-full"
                >
                  <Trash2 className="h-4 w-4" />
                  Clear Vectors
                </button>
              </div>
              <div className="card">
                <h3 className="font-semibold text-gray-900 dark:text-white mb-2">All Caches</h3>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                  Clear all application caches
                </p>
                <button
                  onClick={() => handleClearCache('all')}
                  className="btn btn-danger btn-sm flex items-center gap-2 w-full"
                >
                  <Trash2 className="h-4 w-4" />
                  Clear All
                </button>
              </div>
            </div>
          </div>

          {/* System Info */}
          {systemInfo && (
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                System Information
              </h2>
              <div className="card">
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 text-sm">
                  <div>
                    <span className="text-gray-600 dark:text-gray-400">OS:</span>
                    <span className="ml-2 font-medium text-gray-900 dark:text-white">
                      {systemInfo.os}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-600 dark:text-gray-400">Python:</span>
                    <span className="ml-2 font-medium text-gray-900 dark:text-white">
                      {systemInfo.python_version}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-600 dark:text-gray-400">Hostname:</span>
                    <span className="ml-2 font-medium text-gray-900 dark:text-white">
                      {systemInfo.hostname}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-600 dark:text-gray-400">CPU Cores:</span>
                    <span className="ml-2 font-medium text-gray-900 dark:text-white">
                      {systemInfo.cpu_cores}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-600 dark:text-gray-400">Total RAM:</span>
                    <span className="ml-2 font-medium text-gray-900 dark:text-white">
                      {(systemInfo.total_memory_gb)?.toFixed(1)} GB
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-600 dark:text-gray-400">API Version:</span>
                    <span className="ml-2 font-medium text-gray-900 dark:text-white">
                      {systemInfo.api_version || '1.0.0'}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Recent Logs */}
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Recent Logs (Last 50 lines)
            </h2>
            <div className="card">
              {logs.length > 0 ? (
                <pre className="text-xs font-mono overflow-x-auto p-4 bg-gray-900 text-green-400 rounded max-h-96 overflow-y-auto">
                  {logs.join('\n')}
                </pre>
              ) : (
                <p className="text-gray-500 dark:text-gray-400 text-center py-4">
                  No logs available
                </p>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
