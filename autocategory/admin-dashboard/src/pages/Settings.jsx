import { useState, useEffect } from 'react'
import { apiKeysAPI } from '../services/api'
import { Key, Plus, Trash2, Copy, Check } from 'lucide-react'

export default function Settings() {
  const [apiKeys, setApiKeys] = useState([])
  const [loading, setLoading] = useState(true)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newKey, setNewKey] = useState({
    name: '',
    environment: 'production',
    rate_limit_per_minute: 60,
    rate_limit_per_day: 10000,
    can_classify: true,
    can_generate: false,
    can_admin: false,
  })
  const [createdKey, setCreatedKey] = useState(null)
  const [copiedKey, setCopiedKey] = useState(false)

  useEffect(() => {
    fetchApiKeys()
  }, [])

  const fetchApiKeys = async () => {
    try {
      setLoading(true)
      const response = await apiKeysAPI.list()
      setApiKeys(response.data)
    } catch (error) {
      console.error('Failed to fetch API keys:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateKey = async () => {
    try {
      const response = await apiKeysAPI.create(newKey)
      setCreatedKey(response.data.api_key)
      setNewKey({
        name: '',
        environment: 'production',
        rate_limit_per_minute: 60,
        rate_limit_per_day: 10000,
        can_classify: true,
        can_generate: false,
        can_admin: false,
      })
      fetchApiKeys()
    } catch (error) {
      console.error('Failed to create API key:', error)
      alert('Failed to create API key: ' + (error.response?.data?.detail || error.message))
    }
  }

  const handleRevokeKey = async (keyId, keyName) => {
    if (!confirm(`Revoke API key "${keyName}"?`)) return
    
    try {
      await apiKeysAPI.delete(keyId)
      fetchApiKeys()
    } catch (error) {
      console.error('Failed to revoke API key:', error)
      alert('Failed to revoke API key')
    }
  }

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text)
    setCopiedKey(true)
    setTimeout(() => setCopiedKey(false), 2000)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Settings</h1>
        <p className="text-gray-600 dark:text-gray-400 mt-1">Manage API keys</p>
      </div>

      {/* API Keys Section */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-2">
              <Key className="w-5 h-5 text-blue-600" />
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">API Keys</h2>
            </div>
            <button
              onClick={() => setShowCreateModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              <Plus className="w-4 h-4" />
              Create New Key
            </button>
          </div>
        </div>

        <div className="p-6">
          {loading ? (
            <div className="text-center py-8 text-gray-500">Loading...</div>
          ) : apiKeys.length === 0 ? (
            <div className="text-center py-8 text-gray-500">No API keys created yet</div>
          ) : (
            <div className="space-y-3">
              {apiKeys.map((key) => (
                <div
                  key={key.id}
                  className="flex items-center justify-between p-4 border border-gray-200 dark:border-gray-700 rounded-lg"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-sm text-gray-900 dark:text-white">
                        {key.key_prefix}
                      </span>
                      {key.is_active ? (
                        <span className="px-2 py-1 text-xs bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 rounded">
                          Active
                        </span>
                      ) : (
                        <span className="px-2 py-1 text-xs bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200 rounded">
                          Revoked
                        </span>
                      )}
                    </div>
                    <div className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                      <span className="font-medium">{key.name}</span> · {key.environment} · 
                      Created {new Date(key.created_at).toLocaleDateString()}
                    </div>
                    <div className="mt-1 text-xs text-gray-500">
                      Usage: {key.total_requests || 0} requests
                    </div>
                  </div>
                  {key.is_active && (
                    <button
                      onClick={() => handleRevokeKey(key.id, key.name)}
                      className="flex items-center gap-2 px-3 py-1.5 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
                    >
                      <Trash2 className="w-4 h-4" />
                      Revoke
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Create Key Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full mx-4">
            {createdKey ? (
              <>
                <div className="p-6 border-b border-gray-200 dark:border-gray-700">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                    API Key Created
                  </h3>
                </div>
                <div className="p-6 space-y-4">
                  <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
                    <p className="text-sm text-yellow-800 dark:text-yellow-200 font-medium mb-2">
                      ⚠️ Save this API key now!
                    </p>
                    <p className="text-xs text-yellow-700 dark:text-yellow-300">
                      You won't be able to see it again. Store it securely.
                    </p>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Your API Key
                    </label>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={createdKey}
                        readOnly
                        className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700 text-gray-900 dark:text-white font-mono text-sm"
                      />
                      <button
                        onClick={() => copyToClipboard(createdKey)}
                        className="px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                      >
                        {copiedKey ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>
                </div>
                <div className="p-6 border-t border-gray-200 dark:border-gray-700 flex justify-end">
                  <button
                    onClick={() => {
                      setShowCreateModal(false)
                      setCreatedKey(null)
                    }}
                    className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600"
                  >
                    Done
                  </button>
                </div>
              </>
            ) : (
              <>
                <div className="p-6 border-b border-gray-200 dark:border-gray-700">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                    Create New API Key
                  </h3>
                </div>
                <div className="p-6 space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Key Name
                    </label>
                    <input
                      type="text"
                      value={newKey.name}
                      onChange={(e) => setNewKey({ ...newKey, name: e.target.value })}
                      placeholder="My API Key"
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700 text-gray-900 dark:text-white"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Environment
                    </label>
                    <select
                      value={newKey.environment}
                      onChange={(e) => setNewKey({ ...newKey, environment: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700 text-gray-900 dark:text-white"
                    >
                      <option value="production">Production</option>
                      <option value="development">Development</option>
                      <option value="test">Test</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Rate Limits
                    </label>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <input
                          type="number"
                          value={newKey.rate_limit_per_minute}
                          onChange={(e) => setNewKey({ ...newKey, rate_limit_per_minute: parseInt(e.target.value) })}
                          placeholder="Per minute"
                          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700 text-gray-900 dark:text-white"
                        />
                        <p className="text-xs text-gray-500 mt-1">Per minute</p>
                      </div>
                      <div>
                        <input
                          type="number"
                          value={newKey.rate_limit_per_day}
                          onChange={(e) => setNewKey({ ...newKey, rate_limit_per_day: parseInt(e.target.value) })}
                          placeholder="Per day"
                          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700 text-gray-900 dark:text-white"
                        />
                        <p className="text-xs text-gray-500 mt-1">Per day</p>
                      </div>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Permissions
                    </label>
                    <div className="space-y-2">
                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          checked={newKey.can_classify}
                          onChange={(e) => setNewKey({ ...newKey, can_classify: e.target.checked })}
                          className="mr-2"
                        />
                        <span className="text-sm text-gray-700 dark:text-gray-300">Can Classify</span>
                      </label>
                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          checked={newKey.can_generate}
                          onChange={(e) => setNewKey({ ...newKey, can_generate: e.target.checked })}
                          className="mr-2"
                        />
                        <span className="text-sm text-gray-700 dark:text-gray-300">Can Generate</span>
                      </label>
                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          checked={newKey.can_admin}
                          onChange={(e) => setNewKey({ ...newKey, can_admin: e.target.checked })}
                          className="mr-2"
                        />
                        <span className="text-sm text-gray-700 dark:text-gray-300">Can Admin</span>
                      </label>
                    </div>
                  </div>
                </div>
                <div className="p-6 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-2">
                  <button
                    onClick={() => setShowCreateModal(false)}
                    className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleCreateKey}
                    disabled={!newKey.name}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                  >
                    Create Key
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
