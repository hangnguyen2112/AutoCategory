import { useEffect, useState } from 'react'
import { logsAPI } from '../services/api'
import { FileText, Eye, Search, RefreshCw, Download, Trash2 } from 'lucide-react'
import toast from 'react-hot-toast'

// View Log Details Modal
function LogDetailsModal({ log, onClose }) {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 overflow-y-auto">
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-3xl m-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">Request Log Details</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
            ✕
          </button>
        </div>

        <div className="space-y-4">
          {/* Request Info */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-gray-600 dark:text-gray-400">
                Timestamp:
              </label>
              <p className="text-gray-900 dark:text-white mt-1">
                {new Date(log.created_at).toLocaleString()}
              </p>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-600 dark:text-gray-400">
                Response Time:
              </label>
              <p className="text-gray-900 dark:text-white mt-1">
                {log.response_time_ms?.toFixed(0)} ms
              </p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-gray-600 dark:text-gray-400">
                Endpoint:
              </label>
              <p className="text-gray-900 dark:text-white mt-1 font-mono text-sm">
                {log.method} {log.endpoint}
              </p>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-600 dark:text-gray-400">
                Status Code:
              </label>
              <span
                className={`badge mt-1 inline-block ${
                  log.response_status === 200
                    ? 'badge-success'
                    : log.response_status >= 400
                    ? 'badge-danger'
                    : 'badge-warning'
                }`}
              >
                {log.response_status}
              </span>
            </div>
          </div>

          {log.ip_address && (
            <div>
              <label className="text-sm font-medium text-gray-600 dark:text-gray-400">
                IP Address:
              </label>
              <p className="text-gray-900 dark:text-white mt-1 font-mono">{log.ip_address}</p>
            </div>
          )}

          {/* Classification Details */}
          {log.input_title && (
            <>
              <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
                <h3 className="font-semibold text-gray-900 dark:text-white mb-3">
                  Classification Details
                </h3>
              </div>

              <div>
                <label className="text-sm font-medium text-gray-600 dark:text-gray-400">
                  Input Title:
                </label>
                <p className="text-gray-900 dark:text-white mt-1">{log.input_title}</p>
              </div>

              {log.input_description && (
                <div>
                  <label className="text-sm font-medium text-gray-600 dark:text-gray-400">
                    Input Description:
                  </label>
                  <p className="text-gray-900 dark:text-white mt-1">{log.input_description}</p>
                </div>
              )}

              {log.predicted_category_id && (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium text-gray-600 dark:text-gray-400">
                      Predicted Category:
                    </label>
                    <p className="text-gray-900 dark:text-white mt-1">
                      ID: {log.predicted_category_id}
                    </p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-600 dark:text-gray-400">
                      Confidence:
                    </label>
                    <p className="text-gray-900 dark:text-white mt-1">
                      {(log.confidence * 100).toFixed(1)}%
                    </p>
                  </div>
                </div>
              )}

              {log.decision && (
                <div>
                  <label className="text-sm font-medium text-gray-600 dark:text-gray-400">
                    Decision:
                  </label>
                  <span className="badge badge-info mt-1 inline-block">{log.decision}</span>
                </div>
              )}

              {log.llm_reason && (
                <div>
                  <label className="text-sm font-medium text-gray-600 dark:text-gray-400">
                    LLM Reasoning:
                  </label>
                  <p className="text-gray-900 dark:text-white mt-1 bg-blue-50 dark:bg-blue-900/20 p-3 rounded border border-blue-200 dark:border-blue-800">
                    {log.llm_reason}
                  </p>
                </div>
              )}
            </>
          )}

          {/* Request Body */}
          {log.request_body && (
            <div>
              <label className="text-sm font-medium text-gray-600 dark:text-gray-400">
                Request Body:
              </label>
              <pre className="mt-1 bg-gray-100 dark:bg-gray-700 p-3 rounded text-xs overflow-x-auto text-gray-900 dark:text-white">
                {(() => { try { return JSON.stringify(JSON.parse(log.request_body), null, 2); } catch { return log.request_body; } })()}
              </pre>
            </div>
          )}

          {log.user_agent && (
            <div>
              <label className="text-sm font-medium text-gray-600 dark:text-gray-400">
                User Agent:
              </label>
              <p className="text-gray-900 dark:text-white mt-1 text-sm">{log.user_agent}</p>
            </div>
          )}
        </div>

        <div className="flex justify-end pt-4 mt-4 border-t border-gray-200 dark:border-gray-700">
          <button onClick={onClose} className="btn btn-primary">
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

export default function RequestLogs() {
  const [logs, setLogs] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [endpointFilter, setEndpointFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')
  const [selectedLog, setSelectedLog] = useState(null)
  const [showDetailsModal, setShowDetailsModal] = useState(false)
  const [page, setPage] = useState(1)
  const [totalLogs, setTotalLogs] = useState(0)
  const [totalPages, setTotalPages] = useState(0)
  const itemsPerPage = 50

  const fetchData = async () => {
    try {
      setLoading(true)

      const listParams = {
        skip: (page - 1) * itemsPerPage,
        limit: itemsPerPage,
      }

      if (searchTerm.trim()) {
        listParams.search = searchTerm.trim()
      }

      if (endpointFilter !== 'all') {
        listParams.endpoint = endpointFilter
      }

      if (statusFilter !== 'all') {
        listParams.status_group = statusFilter
      }

      const [logsRes, statsRes] = await Promise.all([
        logsAPI.list(listParams),
        logsAPI.stats(),
      ])

      setLogs(logsRes.data.items || [])
      setTotalLogs(logsRes.data.total || 0)
      setTotalPages(logsRes.data.total_pages || 0)
      setStats(statsRes.data)
    } catch (error) {
      toast.error('Failed to load logs!')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [page, searchTerm, endpointFilter, statusFilter])

  useEffect(() => {
    setPage(1)
  }, [searchTerm, endpointFilter, statusFilter])

  const handleExport = async () => {
    try {
      toast.loading('Exporting logs...', { id: 'export' })
      const response = await logsAPI.list({ limit: 1000 })

      // Convert to CSV
      const csv = [
        ['Timestamp', 'Endpoint', 'Status', 'Response Time', 'Title', 'Category', 'Confidence'].join(','),
        ...(response.data.items || []).map((log) =>
          [
            new Date(log.created_at).toISOString(),
            log.endpoint,
            log.response_status,
            log.response_time_ms,
            log.input_title || '',
            log.predicted_category_id || '',
            log.confidence || '',
          ].join(',')
        ),
      ].join('\n')

      const blob = new Blob([csv], { type: 'text/csv' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `request_logs_${new Date().toISOString().split('T')[0]}.csv`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)

      toast.success('Logs exported!', { id: 'export' })
    } catch (error) {
      toast.error('Export failed!', { id: 'export' })
    }
  }

  const handleCleanup = async () => {
    if (!confirm('Delete logs older than 30 days?')) return

    try {
      toast.loading('Cleaning up...', { id: 'cleanup' })
      await logsAPI.cleanup({ days: 30 })
      toast.success('Old logs deleted!', { id: 'cleanup' })
      fetchData()
    } catch (error) {
      toast.error('Cleanup failed!', { id: 'cleanup' })
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <FileText className="h-8 w-8" />
            Request Logs
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Monitor and analyze API requests
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={fetchData} className="btn btn-secondary flex items-center gap-2">
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
          <button onClick={handleExport} className="btn btn-secondary flex items-center gap-2">
            <Download className="h-4 w-4" />
            Export CSV
          </button>
          <button onClick={handleCleanup} className="btn btn-danger flex items-center gap-2">
            <Trash2 className="h-4 w-4" />
            Cleanup Old
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-5 gap-4">
        <div className="card">
          <div className="text-sm text-gray-600 dark:text-gray-400">Total Requests</div>
          <div className="text-2xl font-bold text-gray-900 dark:text-white">
            {stats?.total_requests?.toLocaleString() || '0'}
          </div>
        </div>
        <div className="card">
          <div className="text-sm text-gray-600 dark:text-gray-400">Success Rate</div>
          <div className="text-2xl font-bold text-green-600">
            {stats?.success_rate?.toFixed(1) || '0'}%
          </div>
        </div>
        <div className="card">
          <div className="text-sm text-gray-600 dark:text-gray-400">Avg Response</div>
          <div className="text-2xl font-bold text-blue-600">
            {stats?.avg_response_time?.toFixed(0) || '0'}ms
          </div>
        </div>
        <div className="card">
          <div className="text-sm text-gray-600 dark:text-gray-400">Errors</div>
          <div className="text-2xl font-bold text-red-600">
            {stats?.error_count?.toLocaleString() || '0'}
          </div>
        </div>
        <div className="card">
          <div className="text-sm text-gray-600 dark:text-gray-400">Today</div>
          <div className="text-2xl font-bold text-purple-600">
            {stats?.today_requests?.toLocaleString() || '0'}
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search endpoint or title..."
              className="input w-full pl-10"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <select
            className="input sm:w-48"
            value={endpointFilter}
            onChange={(e) => setEndpointFilter(e.target.value)}
          >
            <option value="all">All Endpoints</option>
            <option value="/classify">Classify</option>
            <option value="/generate">Generate</option>
            <option value="/auth">Auth</option>
            <option value="/admin">Admin</option>
          </select>
          <select
            className="input sm:w-40"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="all">All Status</option>
            <option value="2xx">2xx Success</option>
            <option value="4xx">4xx Client Error</option>
            <option value="5xx">5xx Server Error</option>
          </select>
        </div>
      </div>

      {/* Logs Table */}
      <div className="card overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <RefreshCw className="h-8 w-8 animate-spin text-primary-600" />
          </div>
        ) : logs.length === 0 ? (
          <div className="text-center py-12">
            <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-500 dark:text-gray-400">No logs found</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-700">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                    Timestamp
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                    Endpoint
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                    Time
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                    Title
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                    Category
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                {logs.map((log) => (
                  <tr key={log.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                      {new Date(log.created_at).toLocaleTimeString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <code className="text-xs font-mono text-gray-900 dark:text-white">
                        {log.method} {log.endpoint}
                      </code>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`badge ${
                          log.response_status === 200
                            ? 'badge-success'
                            : log.response_status >= 400
                            ? 'badge-danger'
                            : 'badge-warning'
                        }`}
                      >
                        {log.response_status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <span
                        className={
                          log.response_time_ms > 2000
                            ? 'text-red-600'
                            : log.response_time_ms > 1000
                            ? 'text-yellow-600'
                            : 'text-green-600'
                        }
                      >
                        {log.response_time_ms?.toFixed(0)}ms
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-900 dark:text-white max-w-xs truncate">
                        {log.input_title || '-'}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                      {log.predicted_category_id || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <button
                        onClick={() => {
                          setSelectedLog(log)
                          setShowDetailsModal(true)
                        }}
                        className="text-blue-600 hover:text-blue-900 dark:text-blue-400"
                        title="View Details"
                      >
                        <Eye className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 0 && (
        <div className="flex justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="btn btn-secondary"
          >
            Previous
          </button>
          <span className="flex items-center px-4 text-gray-700 dark:text-gray-300">
            Page {page} / {Math.max(totalPages, 1)} ({totalLogs.toLocaleString()} logs)
          </span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={page >= totalPages}
            className="btn btn-secondary"
          >
            Next
          </button>
        </div>
      )}

      {/* Details Modal */}
      {showDetailsModal && selectedLog && (
        <LogDetailsModal
          log={selectedLog}
          onClose={() => {
            setShowDetailsModal(false)
            setSelectedLog(null)
          }}
        />
      )}
    </div>
  )
}
