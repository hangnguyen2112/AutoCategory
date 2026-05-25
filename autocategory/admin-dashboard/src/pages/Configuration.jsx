import { useEffect, useState } from 'react'
import { configAPI } from '../services/api'
import { Settings, Plus, Edit2, Trash2, Search, RefreshCw, Eye, EyeOff, Save } from 'lucide-react'
import toast from 'react-hot-toast'

// Create/Edit Config Modal
function ConfigModal({ config, onClose, onSaved }) {
  const isEdit = !!config
  const [formData, setFormData] = useState(
    config || {
      key: '',
      value: '',
      value_type: 'string',
      category: 'general',
      description: '',
      is_secret: false,
    }
  )
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)

    try {
      if (isEdit) {
        await configAPI.update(config.key, formData)
        toast.success('Configuration updated!')
      } else {
        await configAPI.create(formData)
        toast.success('Configuration created!')
      }
      onSaved()
      onClose()
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save configuration!')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 overflow-y-auto">
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-md m-4">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
          {isEdit ? 'Edit Configuration' : 'Create Configuration'}
        </h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Key *
            </label>
            <input
              type="text"
              required
              disabled={isEdit}
              className="input w-full"
              value={formData.key}
              onChange={(e) => setFormData({ ...formData, key: e.target.value })}
              placeholder="e.g., llm_model_name"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Value *
            </label>
            <input
              type={formData.is_secret ? 'password' : 'text'}
              required
              className="input w-full"
              value={formData.value}
              onChange={(e) => setFormData({ ...formData, value: e.target.value })}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Type *
              </label>
              <select
                className="input w-full"
                value={formData.value_type}
                onChange={(e) => setFormData({ ...formData, value_type: e.target.value })}
              >
                <option value="string">String</option>
                <option value="int">Integer</option>
                <option value="float">Float</option>
                <option value="bool">Boolean</option>
                <option value="json">JSON</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Category *
              </label>
              <select
                className="input w-full"
                value={formData.category}
                onChange={(e) => setFormData({ ...formData, category: e.target.value })}
              >
                <option value="general">General</option>
                <option value="llm">LLM Settings</option>
                <option value="qdrant">Qdrant Settings</option>
                <option value="api">API Settings</option>
                <option value="auth">Auth Settings</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Description
            </label>
            <textarea
              rows="2"
              className="input w-full"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Optional description"
            />
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="is_secret"
              checked={formData.is_secret}
              onChange={(e) => setFormData({ ...formData, is_secret: e.target.checked })}
              className="h-4 w-4 text-primary-600 rounded"
            />
            <label htmlFor="is_secret" className="text-sm text-gray-700 dark:text-gray-300">
              Mark as secret (sensitive value)
            </label>
          </div>

          <div className="flex gap-2 justify-end pt-4">
            <button type="button" onClick={onClose} className="btn btn-secondary">
              Cancel
            </button>
            <button type="submit" disabled={loading} className="btn btn-primary">
              {loading ? 'Saving...' : 'Save'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// Delete Config Modal
function DeleteModal({ config, onClose, onDeleted }) {
  const [loading, setLoading] = useState(false)

  const handleDelete = async () => {
    setLoading(true)
    try {
      await configAPI.delete(config.key)
      toast.success('Configuration deleted!')
      onDeleted()
      onClose()
    } catch (error) {
      toast.error('Failed to delete configuration!')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-md m-4">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">Delete Configuration</h2>
        <p className="text-gray-600 dark:text-gray-400 mb-6">
          Are you sure you want to delete the configuration <strong>{config.key}</strong>?
          This action cannot be undone.
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

// Bulk Update Modal
function BulkUpdateModal({ selectedConfigs, onClose, onUpdated }) {
  const [updates, setUpdates] = useState(
    selectedConfigs.reduce((acc, config) => {
      acc[config.key] = config.value
      return acc
    }, {})
  )
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)

    try {
      const updateData = Object.entries(updates).map(([key, value]) => ({
        key,
        value,
      }))
      
      await configAPI.bulkUpdate({ configs: updateData })
      toast.success(`Updated ${updateData.length} configurations!`)
      onUpdated()
      onClose()
    } catch (error) {
      toast.error('Bulk update failed!')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 overflow-y-auto">
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-2xl m-4">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
          Bulk Update ({selectedConfigs.length} items)
        </h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          {selectedConfigs.map((config) => (
            <div key={config.id}>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {config.key}
              </label>
              <input
                type="text"
                className="input w-full"
                value={updates[config.key]}
                onChange={(e) =>
                  setUpdates({ ...updates, [config.key]: e.target.value })
                }
              />
            </div>
          ))}

          <div className="flex gap-2 justify-end pt-4">
            <button type="button" onClick={onClose} className="btn btn-secondary">
              Cancel
            </button>
            <button type="submit" disabled={loading} className="btn btn-primary">
              {loading ? 'Updating...' : 'Update All'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function Configuration() {
  const [configs, setConfigs] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('all')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [showBulkModal, setShowBulkModal] = useState(false)
  const [selectedConfig, setSelectedConfig] = useState(null)
  const [selectedConfigs, setSelectedConfigs] = useState([])
  const [showSecrets, setShowSecrets] = useState({})

  const fetchData = async () => {
    try {
      setLoading(true)
      const response = await configAPI.list()
      setConfigs(response.data)
    } catch (error) {
      toast.error('Failed to load configurations!')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const filteredConfigs = configs.filter((config) => {
    const matchesSearch =
      config.key.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (config.description && config.description.toLowerCase().includes(searchTerm.toLowerCase()))

    const matchesCategory = categoryFilter === 'all' || config.category === categoryFilter

    return matchesSearch && matchesCategory
  })

  const toggleSelectConfig = (config) => {
    setSelectedConfigs((prev) =>
      prev.some((c) => c.id === config.id)
        ? prev.filter((c) => c.id !== config.id)
        : [...prev, config]
    )
  }

  const toggleShowSecret = (configId) => {
    setShowSecrets((prev) => ({ ...prev, [configId]: !prev[configId] }))
  }

  const categories = [...new Set(configs.map((c) => c.category))]
  const secretCount = configs.filter((c) => c.is_secret).length
  const recentlyUpdated = configs.filter(
    (c) => new Date(c.updated_at) > new Date(Date.now() - 24 * 60 * 60 * 1000)
  ).length

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Settings className="h-8 w-8" />
            Configuration
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Manage system configuration settings
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={fetchData} className="btn btn-secondary flex items-center gap-2">
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
          {selectedConfigs.length > 0 && (
            <button
              onClick={() => setShowBulkModal(true)}
              className="btn btn-primary flex items-center gap-2"
            >
              <Save className="h-4 w-4" />
              Bulk Update ({selectedConfigs.length})
            </button>
          )}
          <button
            onClick={() => setShowCreateModal(true)}
            className="btn btn-primary flex items-center gap-2"
          >
            <Plus className="h-4 w-4" />
            Add Config
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="card">
          <div className="text-sm text-gray-600 dark:text-gray-400">Total Configs</div>
          <div className="text-2xl font-bold text-gray-900 dark:text-white">
            {configs.length}
          </div>
        </div>
        <div className="card">
          <div className="text-sm text-gray-600 dark:text-gray-400">Secret Values</div>
          <div className="text-2xl font-bold text-red-600">{secretCount}</div>
        </div>
        <div className="card">
          <div className="text-sm text-gray-600 dark:text-gray-400">Updated Today</div>
          <div className="text-2xl font-bold text-green-600">{recentlyUpdated}</div>
        </div>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search key or description..."
              className="input w-full pl-10"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <select
            className="input sm:w-48"
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
          >
            <option value="all">All Categories</option>
            {categories.map((cat) => (
              <option key={cat} value={cat}>
                {cat.charAt(0).toUpperCase() + cat.slice(1)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Configs Table */}
      <div className="card overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <RefreshCw className="h-8 w-8 animate-spin text-primary-600" />
          </div>
        ) : filteredConfigs.length === 0 ? (
          <div className="text-center py-12">
            <Settings className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-500 dark:text-gray-400">No configurations found</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-700">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                    <input
                      type="checkbox"
                      checked={selectedConfigs.length === filteredConfigs.length}
                      onChange={(e) =>
                        setSelectedConfigs(e.target.checked ? filteredConfigs : [])
                      }
                      className="h-4 w-4 text-primary-600 rounded"
                    />
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                    Key
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                    Value
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                    Type
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                    Category
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                    Updated
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                {filteredConfigs.map((config) => (
                  <tr key={config.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                    <td className="px-6 py-4">
                      <input
                        type="checkbox"
                        checked={selectedConfigs.some((c) => c.id === config.id)}
                        onChange={() => toggleSelectConfig(config)}
                        className="h-4 w-4 text-primary-600 rounded"
                      />
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm font-medium text-gray-900 dark:text-white">
                        {config.key}
                      </div>
                      {config.description && (
                        <div className="text-xs text-gray-500 dark:text-gray-400 max-w-xs truncate">
                          {config.description}
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        {config.is_secret ? (
                          <>
                            <code className="text-sm font-mono bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded text-gray-900 dark:text-white">
                              {showSecrets[config.id] ? config.value : '••••••••'}
                            </code>
                            <button
                              onClick={() => toggleShowSecret(config.id)}
                              className="text-gray-500 hover:text-gray-700"
                              title={showSecrets[config.id] ? 'Hide' : 'Show'}
                            >
                              {showSecrets[config.id] ? (
                                <EyeOff className="h-4 w-4" />
                              ) : (
                                <Eye className="h-4 w-4" />
                              )}
                            </button>
                          </>
                        ) : (
                          <code className="text-sm font-mono bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded max-w-xs truncate text-gray-900 dark:text-white">
                            {config.value}
                          </code>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="badge badge-secondary">{config.value_type}</span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="badge badge-info">{config.category}</span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                      {new Date(config.updated_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => {
                            setSelectedConfig(config)
                            setShowEditModal(true)
                          }}
                          className="text-blue-600 hover:text-blue-900 dark:text-blue-400"
                          title="Edit"
                        >
                          <Edit2 className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => {
                            setSelectedConfig(config)
                            setShowDeleteModal(true)
                          }}
                          className="text-red-600 hover:text-red-900 dark:text-red-400"
                          title="Delete"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
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
        <ConfigModal onClose={() => setShowCreateModal(false)} onSaved={fetchData} />
      )}

      {showEditModal && selectedConfig && (
        <ConfigModal
          config={selectedConfig}
          onClose={() => {
            setShowEditModal(false)
            setSelectedConfig(null)
          }}
          onSaved={fetchData}
        />
      )}

      {showDeleteModal && selectedConfig && (
        <DeleteModal
          config={selectedConfig}
          onClose={() => {
            setShowDeleteModal(false)
            setSelectedConfig(null)
          }}
          onDeleted={fetchData}
        />
      )}

      {showBulkModal && selectedConfigs.length > 0 && (
        <BulkUpdateModal
          selectedConfigs={selectedConfigs}
          onClose={() => setShowBulkModal(false)}
          onUpdated={() => {
            fetchData()
            setSelectedConfigs([])
          }}
        />
      )}
    </div>
  )
}
