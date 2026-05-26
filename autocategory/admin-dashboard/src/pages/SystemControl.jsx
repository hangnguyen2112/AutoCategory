import { useEffect, useState } from 'react'
import { systemAPI, llmAPI } from '../services/api'
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
  Cpu,
  CheckCircle,
  XCircle,
  Eye,
  EyeOff,
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

  // LLM Provider state
  const [llmConfig, setLlmConfig] = useState(null)
  const [llmForm, setLlmForm] = useState({
    provider: 'lm_studio',
    lm_studio_base_url: '',
    lm_studio_model: '',
    gemini_web_secure_1psid: '',
    gemini_web_secure_1psidts: '',
    deepseek_api_key: '',
    deepseek_model: 'deepseek-chat',
  })
  const [llmSaving, setLlmSaving] = useState(false)
  const [llmTesting, setLlmTesting] = useState(false)
  const [llmTestResult, setLlmTestResult] = useState(null)
  const [showPsid, setShowPsid] = useState(false)
  const [showPsidts, setShowPsidts] = useState(false)
  const [showDeepseekKey, setShowDeepseekKey] = useState(false)

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

  const fetchLlmConfig = async () => {
    try {
      const res = await llmAPI.getConfig()
      setLlmConfig(res.data)
      setLlmForm({
        provider: res.data.provider,
        lm_studio_base_url: res.data.lm_studio_base_url || '',
        lm_studio_model: res.data.lm_studio_model || '',
        gemini_web_secure_1psid: res.data.gemini_web_secure_1psid || '',
        gemini_web_secure_1psidts: res.data.gemini_web_secure_1psidts || '',
        deepseek_api_key: res.data.deepseek_api_key || '',
        deepseek_model: res.data.deepseek_model || 'deepseek-chat',
      })
    } catch (err) {
      console.error('Failed to load LLM config', err)
    }
  }

  const handleLlmSave = async () => {
    setLlmSaving(true)
    setLlmTestResult(null)
    try {
      const payload = { provider: llmForm.provider }
      if (llmForm.provider === 'lm_studio') {
        payload.lm_studio_base_url = llmForm.lm_studio_base_url
        payload.lm_studio_model = llmForm.lm_studio_model
      } else if (llmForm.provider === 'gemini_web') {
        payload.gemini_web_secure_1psid = llmForm.gemini_web_secure_1psid
        payload.gemini_web_secure_1psidts = llmForm.gemini_web_secure_1psidts
      } else if (llmForm.provider === 'deepseek') {
        payload.deepseek_api_key = llmForm.deepseek_api_key
        payload.deepseek_model = llmForm.deepseek_model
      }
      const res = await llmAPI.switchProvider(payload)
      setLlmConfig(res.data)
      toast.success('LLM provider cập nhật thành công!')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Lưu thất bại')
    } finally {
      setLlmSaving(false)
    }
  }

  const handleLlmTest = async () => {
    setLlmTesting(true)
    setLlmTestResult(null)
    try {
      const res = await llmAPI.test()
      setLlmTestResult(res.data)
    } catch (err) {
      setLlmTestResult({ success: false, error: err.response?.data?.detail || String(err) })
    } finally {
      setLlmTesting(false)
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
    fetchLlmConfig()
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

          {/* LLM Provider */}
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
              <Cpu className="h-5 w-5" />
              LLM Provider
            </h2>
            <div className="card space-y-5">
              {/* Provider selector */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Provider
                </label>
                <div className="flex flex-wrap gap-3">
                  {[
                    { id: 'lm_studio', label: 'LM Studio', desc: 'Local (host)' },
                    { id: 'llama',     label: 'Llama.cpp',  desc: 'Docker service' },
                    { id: 'gemini_web', label: '✨ Gemini Web', desc: 'Cookie-based, free' },
                    { id: 'deepseek', label: '🤖 DeepSeek', desc: 'API key' },
                  ].map((p) => (
                    <label
                      key={p.id}
                      className={`flex items-center gap-2 px-4 py-2 rounded-lg border-2 cursor-pointer transition-colors ${
                        llmForm.provider === p.id
                          ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/30'
                          : 'border-gray-200 dark:border-gray-600 hover:border-gray-300'
                      }`}
                    >
                      <input
                        type="radio"
                        name="llm_provider"
                        value={p.id}
                        checked={llmForm.provider === p.id}
                        onChange={(e) => setLlmForm((f) => ({ ...f, provider: e.target.value }))}
                        className="hidden"
                      />
                      <div>
                        <div className="font-medium text-sm text-gray-900 dark:text-white">{p.label}</div>
                        <div className="text-xs text-gray-500 dark:text-gray-400">{p.desc}</div>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              {/* LM Studio fields */}
              {llmForm.provider === 'lm_studio' && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Base URL</label>
                    <input
                      type="text"
                      value={llmForm.lm_studio_base_url}
                      onChange={(e) => setLlmForm((f) => ({ ...f, lm_studio_base_url: e.target.value }))}
                      placeholder="http://host.docker.internal:11434"
                      className="input w-full"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Model name</label>
                    <input
                      type="text"
                      value={llmForm.lm_studio_model}
                      onChange={(e) => setLlmForm((f) => ({ ...f, lm_studio_model: e.target.value }))}
                      placeholder="google/gemma-4-e4b"
                      className="input w-full"
                    />
                  </div>
                </div>
              )}

              {/* Gemini Web fields */}
              {llmForm.provider === 'gemini_web' && (
                <div className="space-y-4">
                  <div className="p-3 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 text-sm text-amber-800 dark:text-amber-200">
                    Cookie lấy từ <strong>gemini.google.com</strong>: F12 → Network → Any request → Headers → Copy <code>__Secure-1PSID</code> và <code>__Secure-1PSIDTS</code>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">__Secure-1PSID</label>
                    <div className="relative">
                      <input
                        type={showPsid ? 'text' : 'password'}
                        value={llmForm.gemini_web_secure_1psid}
                        onChange={(e) => setLlmForm((f) => ({ ...f, gemini_web_secure_1psid: e.target.value }))}
                        placeholder="Paste cookie value..."
                        className="input w-full pr-10"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPsid((v) => !v)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                      >
                        {showPsid ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">__Secure-1PSIDTS <span className="text-gray-400">(optional)</span></label>
                    <div className="relative">
                      <input
                        type={showPsidts ? 'text' : 'password'}
                        value={llmForm.gemini_web_secure_1psidts}
                        onChange={(e) => setLlmForm((f) => ({ ...f, gemini_web_secure_1psidts: e.target.value }))}
                        placeholder="Paste cookie value..."
                        className="input w-full pr-10"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPsidts((v) => !v)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                      >
                        {showPsidts ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* DeepSeek fields */}
              {llmForm.provider === 'deepseek' && (
                <div className="space-y-4">
                  <div className="p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 text-sm text-blue-800 dark:text-blue-200">
                    Lấy API key tại <strong>platform.deepseek.com</strong> → API Keys
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">API Key</label>
                    <div className="relative">
                      <input
                        type={showDeepseekKey ? 'text' : 'password'}
                        value={llmForm.deepseek_api_key}
                        onChange={(e) => setLlmForm((f) => ({ ...f, deepseek_api_key: e.target.value }))}
                        placeholder="sk-..."
                        className="input w-full pr-10"
                      />
                      <button
                        type="button"
                        onClick={() => setShowDeepseekKey((v) => !v)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                      >
                        {showDeepseekKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Model</label>
                    <input
                      type="text"
                      value={llmForm.deepseek_model}
                      onChange={(e) => setLlmForm((f) => ({ ...f, deepseek_model: e.target.value }))}
                      placeholder="deepseek-chat"
                      className="input w-full"
                    />
                  </div>
                </div>
              )}

              {/* Buttons + status */}
              <div className="flex flex-wrap items-center gap-3 pt-1">
                <button
                  onClick={handleLlmSave}
                  disabled={llmSaving}
                  className="btn btn-primary flex items-center gap-2"
                >
                  {llmSaving ? <RefreshCw className="h-4 w-4 animate-spin" /> : null}
                  {llmSaving ? 'Đang lưu...' : 'Lưu & Áp dụng'}
                </button>
                <button
                  onClick={handleLlmTest}
                  disabled={llmTesting || llmSaving}
                  className="btn btn-secondary flex items-center gap-2"
                >
                  {llmTesting ? <RefreshCw className="h-4 w-4 animate-spin" /> : null}
                  {llmTesting ? 'Đang test...' : 'Test kết nối'}
                </button>
                {llmConfig && (
                  <span className="text-sm text-gray-500 dark:text-gray-400">
                    Đang dùng: <strong className="text-gray-800 dark:text-gray-200">{llmConfig.provider}</strong>
                    {llmConfig.provider !== 'gemini_web' && (
                      <> — {llmConfig.active_model}</>
                    )}
                  </span>
                )}
              </div>

              {/* Test result */}
              {llmTestResult && (
                <div
                  className={`flex items-start gap-3 p-3 rounded-lg ${
                    llmTestResult.success
                      ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700'
                      : 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700'
                  }`}
                >
                  {llmTestResult.success
                    ? <CheckCircle className="h-5 w-5 text-green-600 mt-0.5 shrink-0" />
                    : <XCircle className="h-5 w-5 text-red-600 mt-0.5 shrink-0" />}
                  <div className="text-sm">
                    {llmTestResult.success ? (
                      <>
                        <span className="font-medium text-green-800 dark:text-green-200">Kết nối thành công</span>
                        {llmTestResult.latency_ms && (
                          <span className="text-green-600 dark:text-green-400 ml-2">{llmTestResult.latency_ms}ms</span>
                        )}
                        {llmTestResult.response_preview && (
                          <div className="text-green-700 dark:text-green-300 mt-1 font-mono text-xs">
                            &quot;{llmTestResult.response_preview}&quot;
                          </div>
                        )}
                      </>
                    ) : (
                      <>
                        <span className="font-medium text-red-800 dark:text-red-200">Kết nối thất bại</span>
                        <div className="text-red-700 dark:text-red-300 mt-1 text-xs">{llmTestResult.error}</div>
                      </>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>

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
