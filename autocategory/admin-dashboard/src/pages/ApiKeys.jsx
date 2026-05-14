import { useEffect, useState } from 'react'
import { apiKeysAPI } from '../services/api'
import { Key, Plus, Trash2, Copy, Check, RefreshCw, AlertCircle, Eye, EyeOff } from 'lucide-react'
import toast from 'react-hot-toast'

// Create API Key Modal
function CreateApiKeyModal({ onClose, onCreated }) {
  const [formData, setFormData] = useState({
    name: '',
    rate_limit_per_minute: 60,
    rate_limit_per_day: 10000,
    can_classify: true,
    can_generate: true,
    can_admin: false,
    expires_days: 365,
  })
  const [loading, setLoading] = useState(false)
  const [createdKey, setCreatedKey] = useState(null)
  const [copied, setCopied] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)

    try {
      // Calculate expiry date
      const expiresAt = new Date()
      expiresAt.setDate(expiresAt.getDate() + formData.expires_days)

      const response = await apiKeysAPI.create({
        ...formData,
        expires_at: expiresAt.toISOString(),
      })
      
      setCreatedKey(response.data.api_key)
      toast.success('API Key created successfully!')
      onCreated()
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create API key!')
    } finally {
      setLoading(false)
    }
  }

  const copyToClipboard = () => {
    navigator.clipboard.writeText(createdKey)
    setCopied(true)
    toast.success('Copied to clipboard!')
    setTimeout(() => setCopied(false), 2000)
  }

  if (createdKey) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-lg">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <AlertCircle className="h-6 w-6 text-yellow-600" />
            Save Your API Key
          </h2>

          <div className="bg-yellow-50 dark:bg-yellow-900 border border-yellow-200 dark:border-yellow-700 rounded p-4 mb-4">
            <p className="text-sm text-yellow-800 dark:text-yellow-200 mb-2">
              <strong>⚠️ Important:</strong> This key will only be shown once! 
              Please copy and save it securely.
            </p>
          </div>

          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Your API Key
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                readOnly
                value={createdKey}
                className="input flex-1 font-mono text-sm"
              />
              <button
                onClick={copyToClipboard}
                className="btn btn-primary flex items-center gap-2"
              >
                {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                {copied ? 'Copied' : 'Copy'}
              </button>
            </div>
          </div>

          <div className="bg-gray-50 dark:bg-gray-700 rounded p-4 mb-4">
            <p className="text-sm text-gray-700 dark:text-gray-300 mb-2">
              <strong>Usage Example:</strong>
            </p>
            <pre className="text-xs bg-gray-900 text-green-400 p-3 rounded overflow-x-auto">
{`curl http://localhost:8000/api/classify \\
  -H "X-API-Key: ${createdKey}" \\
  -H "Content-Type: application/json" \\
  -d '{"title": "iPhone 15 Pro Max"}'`}
            </pre>
          </div>

          <div className="flex justify-end">
            <button onClick={onClose} className="btn btn-primary">
              I've Saved It
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-md">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
          Create New API Key
        </h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Name *
            </label>
            <input
              type="text"
              required
              placeholder="e.g., Production Key, Test Key"
              className="input w-full"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Rate Limit (per minute)
              </label>
              <input
                type="number"
                min="1"
                className="input w-full"
                value={formData.rate_limit_per_minute}
                onChange={(e) =>
                  setFormData({ ...formData, rate_limit_per_minute: parseInt(e.target.value) })
                }
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Rate Limit (per day)
              </label>
              <input
                type="number"
                min="1"
                className="input w-full"
                value={formData.rate_limit_per_day}
                onChange={(e) =>
                  setFormData({ ...formData, rate_limit_per_day: parseInt(e.target.value) })
                }
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Expires in (days)
            </label>
            <input
              type="number"
              min="1"
              className="input w-full"
              value={formData.expires_days}
              onChange={(e) =>
                setFormData({ ...formData, expires_days: parseInt(e.target.value) })
              }
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Permissions
            </label>
            <div className="space-y-2">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  className="mr-2"
                  checked={formData.can_classify}
                  onChange={(e) =>
                    setFormData({ ...formData, can_classify: e.target.checked })
                  }
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">
                  Can Classify
                </span>
              </label>
              <label className="flex items-center">
                <input
                  type="checkbox"
                  className="mr-2"
                  checked={formData.can_generate}
                  onChange={(e) =>
                    setFormData({ ...formData, can_generate: e.target.checked })
                  }
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">
                  Can Generate
                </span>
              </label>
              <label className="flex items-center">
                <input
                  type="checkbox"
                  className="mr-2"
                  checked={formData.can_admin}
                  onChange={(e) =>
                    setFormData({ ...formData, can_admin: e.target.checked })
                  }
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">
                  Admin Access
                </span>
              </label>
            </div>
          </div>

          <div className="flex gap-2 justify-end pt-4">
            <button type="button" onClick={onClose} className="btn btn-secondary">
              Cancel
            </button>
            <button type="submit" disabled={loading} className="btn btn-primary">
              {loading ? 'Creating...' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// Delete Confirmation Modal
function DeleteModal({ apiKey, onClose, onConfirm }) {
  const [loading, setLoading] = useState(false)

  const handleDelete = async () => {
    setLoading(true)
    try {
      await apiKeysAPI.delete(apiKey.id)
      toast.success('API Key deleted!')
      onConfirm()
      onClose()
    } catch (error) {
      toast.error('Failed to delete API key!')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-md">
        <h2 className="text-xl font-bold text-red-600 mb-4">Delete API Key</h2>
        <p className="text-gray-700 dark:text-gray-300 mb-6">
          Are you sure you want to delete API key <strong>{apiKey.name}</strong>?
          Any applications using this key will lose access immediately.
        </p>
        <div className="flex gap-2 justify-end">
          <button onClick={onClose} className="btn btn-secondary">
            Cancel
          </button>
          <button onClick={handleDelete} disabled={loading} className="btn btn-danger">
            {loading ? 'Deleting...' : 'Delete'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function ApiKeys() {
  const [apiKeys, setApiKeys] = useState([])
  const [loading, setLoading] = useState(true)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [selectedKey, setSelectedKey] = useState(null)
  const [visibleKeys, setVisibleKeys] = useState({})

  const fetchApiKeys = async () => {
    try {
      setLoading(true)
      const response = await apiKeysAPI.list()
      setApiKeys(response.data)
    } catch (error) {
      toast.error('Failed to load API keys!')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchApiKeys()
  }, [])

  const toggleKeyVisibility = (keyId) => {
    setVisibleKeys((prev) => ({
      ...prev,
      [keyId]: !prev[keyId],
    }))
  }

  const getStatusBadge = (apiKey) => {
    const now = new Date()
    const expiresAt = new Date(apiKey.expires_at)

    if (!apiKey.is_active) {
      return <span className="badge badge-secondary">Inactive</span>
    }
    if (expiresAt < now) {
      return <span className="badge badge-danger">Expired</span>
    }

    const daysUntilExpiry = Math.floor((expiresAt - now) / (1000 * 60 * 60 * 24))
    if (daysUntilExpiry < 30) {
      return <span className="badge badge-warning">Expires Soon</span>
    }

    return <span className="badge badge-success">Active</span>
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Key className="h-8 w-8" />
            API Keys
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Manage API keys for external integrations
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={fetchApiKeys} className="btn btn-secondary flex items-center gap-2">
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="btn btn-primary flex items-center gap-2"
          >
            <Plus className="h-4 w-4" />
            Create API Key
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="card">
          <div className="text-sm text-gray-600 dark:text-gray-400">Total Keys</div>
          <div className="text-2xl font-bold text-gray-900 dark:text-white">
            {apiKeys.length}
          </div>
        </div>
        <div className="card">
          <div className="text-sm text-gray-600 dark:text-gray-400">Active</div>
          <div className="text-2xl font-bold text-green-600">
            {apiKeys.filter((k) => k.is_active && new Date(k.expires_at) > new Date()).length}
          </div>
        </div>
        <div className="card">
          <div className="text-sm text-gray-600 dark:text-gray-400">Total Requests</div>
          <div className="text-2xl font-bold text-blue-600">
            {apiKeys.reduce((sum, k) => sum + (k.total_requests || 0), 0).toLocaleString()}
          </div>
        </div>
        <div className="card">
          <div className="text-sm text-gray-600 dark:text-gray-400">Expired</div>
          <div className="text-2xl font-bold text-red-600">
            {apiKeys.filter((k) => new Date(k.expires_at) < new Date()).length}
          </div>
        </div>
      </div>

      {/* API Keys Table */}
      <div className="card overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <RefreshCw className="h-8 w-8 animate-spin text-primary-600" />
          </div>
        ) : apiKeys.length === 0 ? (
          <div className="text-center py-12">
            <Key className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-500 dark:text-gray-400 mb-4">No API keys yet</p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="btn btn-primary"
            >
              Create Your First API Key
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-700">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Name
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Key
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Rate Limits
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Usage
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Expires
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                {apiKeys.map((apiKey) => (
                  <tr key={apiKey.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900 dark:text-white">
                        {apiKey.name}
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        ID: {apiKey.id}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <code className="text-sm font-mono bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded text-gray-900 dark:text-white">
                          {visibleKeys[apiKey.id]
                            ? apiKey.key_prefix + '...'
                            : '••••••••'}
                        </code>
                        <button
                          onClick={() => toggleKeyVisibility(apiKey.id)}
                          className="text-gray-400 hover:text-gray-600"
                        >
                          {visibleKeys[apiKey.id] ? (
                            <EyeOff className="h-4 w-4" />
                          ) : (
                            <Eye className="h-4 w-4" />
                          )}
                        </button>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                      <div>{apiKey.rate_limit_per_minute}/min</div>
                      <div>{apiKey.rate_limit_per_day?.toLocaleString()}/day</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900 dark:text-white">
                        {apiKey.total_requests?.toLocaleString() || 0} requests
                      </div>
                      {apiKey.last_used_at && (
                        <div className="text-xs text-gray-500 dark:text-gray-400">
                          Last: {new Date(apiKey.last_used_at).toLocaleDateString()}
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">{getStatusBadge(apiKey)}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                      {new Date(apiKey.expires_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <button
                        onClick={() => {
                          setSelectedKey(apiKey)
                          setShowDeleteModal(true)
                        }}
                        className="text-red-600 hover:text-red-900 dark:text-red-400"
                        title="Delete"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modals */}
      {showCreateModal && (
        <CreateApiKeyModal
          onClose={() => setShowCreateModal(false)}
          onCreated={() => {
            fetchApiKeys()
            // Keep modal open to show the key
          }}
        />
      )}

      {showDeleteModal && (
        <DeleteModal
          apiKey={selectedKey}
          onClose={() => {
            setShowDeleteModal(false)
            setSelectedKey(null)
          }}
          onConfirm={fetchApiKeys}
        />
      )}
    </div>
  )
}
