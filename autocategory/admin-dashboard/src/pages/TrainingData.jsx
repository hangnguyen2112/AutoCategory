import { useEffect, useState } from 'react'
import { trainingAPI } from '../services/api'
import {
  Database,
  Plus,
  Eye,
  Trash2,
  CheckCircle,
  Search,
  RefreshCw,
  Download,
  Filter,
  XCircle,
  Upload,
} from 'lucide-react'
import toast from 'react-hot-toast'
import CategorySelect from '../components/CategorySelect'

// View Sample Modal
function ViewSampleModal({ sample, onClose, onValidate, onDelete }) {
  const [validating, setValidating] = useState(false)
  const [deleting, setDeleting] = useState(false)

  const handleValidate = async () => {
    setValidating(true)
    try {
      await trainingAPI.update(sample.id, { is_validated: true })
      toast.success('Sample validated!')
      onValidate()
      onClose()
    } catch (error) {
      toast.error('Failed to validate!')
    } finally {
      setValidating(false)
    }
  }

  const handleDelete = async () => {
    setDeleting(true)
    try {
      await trainingAPI.delete(sample.id)
      toast.success('Sample deleted!')
      onDelete()
      onClose()
    } catch (error) {
      toast.error('Failed to delete!')
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 overflow-y-auto">
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-2xl m-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">Training Sample</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
            ✕
          </button>
        </div>

        <div className="space-y-4 mb-6">
          <div>
            <label className="text-sm font-medium text-gray-600 dark:text-gray-400">Title:</label>
            <p className="text-gray-900 dark:text-white mt-1">{sample.title}</p>
          </div>

          {sample.description && (
            <div>
              <label className="text-sm font-medium text-gray-600 dark:text-gray-400">
                Description:
              </label>
              <p className="text-gray-900 dark:text-white mt-1">{sample.description}</p>
            </div>
          )}

          {sample.price && (
            <div>
              <label className="text-sm font-medium text-gray-600 dark:text-gray-400">Price:</label>
              <p className="text-gray-900 dark:text-white mt-1">
                {sample.price.toLocaleString()} VNĐ
              </p>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-gray-600 dark:text-gray-400">
                Actual Category ID:
              </label>
              <p className="text-gray-900 dark:text-white mt-1 font-mono">
                {sample.actual_category_id}
              </p>
            </div>

            {sample.predicted_category_id && (
              <div>
                <label className="text-sm font-medium text-gray-600 dark:text-gray-400">
                  Predicted Category ID:
                </label>
                <p className="text-gray-900 dark:text-white mt-1 font-mono">
                  {sample.predicted_category_id}
                </p>
              </div>
            )}
          </div>

          {sample.predicted_confidence && (
            <div>
              <label className="text-sm font-medium text-gray-600 dark:text-gray-400">
                Confidence:
              </label>
              <p className="text-gray-900 dark:text-white mt-1">
                {(sample.predicted_confidence * 100).toFixed(1)}%
              </p>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-gray-600 dark:text-gray-400">Source:</label>
              <span className="badge badge-info mt-1 inline-block">{sample.source}</span>
            </div>

            <div>
              <label className="text-sm font-medium text-gray-600 dark:text-gray-400">Status:</label>
              {sample.is_validated ? (
                <span className="badge badge-success mt-1 inline-block">Validated</span>
              ) : (
                <span className="badge badge-warning mt-1 inline-block">Pending</span>
              )}
            </div>
          </div>

          <div>
            <label className="text-sm font-medium text-gray-600 dark:text-gray-400">Created:</label>
            <p className="text-gray-900 dark:text-white mt-1">
              {new Date(sample.created_at).toLocaleString()}
            </p>
          </div>
        </div>

        <div className="flex gap-2 justify-end pt-4 border-t border-gray-200 dark:border-gray-700">
          {!sample.is_validated && (
            <button
              onClick={handleValidate}
              disabled={validating}
              className="btn btn-primary flex items-center gap-2"
            >
              <CheckCircle className="h-4 w-4" />
              {validating ? 'Validating...' : 'Validate'}
            </button>
          )}
          <button
            onClick={handleDelete}
            disabled={deleting}
            className="btn btn-danger flex items-center gap-2"
          >
            <Trash2 className="h-4 w-4" />
            {deleting ? 'Deleting...' : 'Delete'}
          </button>
          <button onClick={onClose} className="btn btn-secondary">
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

// Create Sample Modal
function CreateSampleModal({ onClose, onCreated }) {
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    price: '',
    actual_category_id: '',
    source: 'manual',
  })
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)

    try {
      const data = {
        ...formData,
        price: formData.price ? parseFloat(formData.price) : null,
        actual_category_id: parseInt(formData.actual_category_id),
      }
      
      await trainingAPI.create(data)
      toast.success('Training sample created!')
      onCreated()
      onClose()
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create sample!')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 overflow-y-auto">
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-md m-4">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
          Create Training Sample
        </h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Title *
            </label>
            <input
              type="text"
              required
              className="input w-full"
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Description
            </label>
            <textarea
              rows="3"
              className="input w-full"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Price (VNĐ)
            </label>
            <input
              type="number"
              className="input w-full"
              value={formData.price}
              onChange={(e) => setFormData({ ...formData, price: e.target.value })}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Category *
            </label>
            <CategorySelect
              value={formData.actual_category_id}
              onChange={(e) => setFormData({ ...formData, actual_category_id: e.target.value })}
              required
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Select the correct category for this product
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Source
            </label>
            <select
              className="input w-full"
              value={formData.source}
              onChange={(e) => setFormData({ ...formData, source: e.target.value })}
            >
              <option value="manual">Manual Entry</option>
              <option value="feedback">User Feedback</option>
              <option value="import">Imported</option>
            </select>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              "User Feedback" = data from classification corrections
            </p>
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

// Import Training Data Modal
function ImportModal({ onClose, onImported }) {
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [preview, setPreview] = useState(null)

  const handleFileChange = async (e) => {
    const selectedFile = e.target.files[0]
    if (!selectedFile) return

    setFile(selectedFile)

    // Preview file content
    try {
      const text = await selectedFile.text()
      let data

      if (selectedFile.name.endsWith('.json')) {
        data = JSON.parse(text)
      } else if (selectedFile.name.endsWith('.csv')) {
        // Simple CSV parser (title, description, price, actual_category_id)
        const lines = text.split('\n').filter(l => l.trim())
        const headers = lines[0].split(',').map(h => h.trim())
        data = lines.slice(1).map(line => {
          const values = line.split(',').map(v => v.trim())
          const obj = {}
          headers.forEach((h, i) => {
            obj[h] = values[i]
          })
          return obj
        })
      }

      setPreview({
        count: Array.isArray(data) ? data.length : 1,
        sample: Array.isArray(data) ? data[0] : data
      })
    } catch (error) {
      toast.error('Failed to parse file: ' + error.message)
      setFile(null)
    }
  }

  const handleImport = async () => {
    if (!file) return

    setLoading(true)
    try {
      const text = await file.text()
      let data

      if (file.name.endsWith('.json')) {
        data = JSON.parse(text)
      } else if (file.name.endsWith('.csv')) {
        const lines = text.split('\n').filter(l => l.trim())
        const headers = lines[0].split(',').map(h => h.trim())
        data = lines.slice(1).map(line => {
          const values = line.split(',').map(v => v.trim())
          const obj = {}
          headers.forEach((h, i) => {
            obj[h] = values[i]
          })
          return obj
        })
      }

      // Ensure data is an array
      if (!Array.isArray(data)) {
        data = [data]
      }

      // Import each sample
      let successCount = 0
      let failCount = 0

      for (const item of data) {
        try {
          await trainingAPI.create({
            title: item.title,
            description: item.description || '',
            price: item.price ? parseFloat(item.price) : null,
            actual_category_id: parseInt(item.actual_category_id),
            source: 'import'
          })
          successCount++
        } catch (error) {
          console.error('Failed to import item:', item, error)
          failCount++
        }
      }

      if (successCount > 0) {
        toast.success(`Imported ${successCount} samples successfully!`)
        onImported()
        onClose()
      }

      if (failCount > 0) {
        toast.error(`Failed to import ${failCount} samples`)
      }
    } catch (error) {
      toast.error('Import failed: ' + error.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 overflow-y-auto">
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-lg m-4">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
          Import Training Data
        </h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Upload File (JSON or CSV)
            </label>
            <input
              type="file"
              accept=".json,.csv"
              onChange={handleFileChange}
              className="input w-full"
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
              CSV format: title, description, price, actual_category_id
            </p>
          </div>

          {preview && (
            <div className="bg-gray-50 dark:bg-gray-700/50 p-4 rounded border border-gray-200 dark:border-gray-600">
              <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Preview: {preview.count} sample(s)
              </div>
              <pre className="text-xs text-gray-600 dark:text-gray-400 overflow-x-auto">
                {JSON.stringify(preview.sample, null, 2)}
              </pre>
            </div>
          )}

          <div className="flex gap-2 justify-end pt-4 border-t border-gray-200 dark:border-gray-700">
            <button onClick={onClose} className="btn btn-secondary">
              Cancel
            </button>
            <button
              onClick={handleImport}
              disabled={!file || loading}
              className="btn btn-primary flex items-center gap-2"
            >
              <Upload className="h-4 w-4" />
              {loading ? 'Importing...' : 'Import'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function TrainingData() {
  const [samples, setSamples] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [sourceFilter, setSourceFilter] = useState('all')
  const [validatedFilter, setValidatedFilter] = useState('all')
  const [selectedSample, setSelectedSample] = useState(null)
  const [showViewModal, setShowViewModal] = useState(false)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showImportModal, setShowImportModal] = useState(false)
  const [page, setPage] = useState(1)
  const itemsPerPage = 20

  const fetchData = async () => {
    try {
      setLoading(true)
      const [samplesRes, statsRes] = await Promise.all([
        trainingAPI.list({ skip: (page - 1) * itemsPerPage, limit: itemsPerPage }),
        trainingAPI.stats(),
      ])

      setSamples(samplesRes.data)
      setStats(statsRes.data)
    } catch (error) {
      toast.error('Failed to load training data!')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [page])

  const filteredSamples = samples.filter((sample) => {
    const matchesSearch =
      sample.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (sample.description && sample.description.toLowerCase().includes(searchTerm.toLowerCase()))

    const matchesSource = sourceFilter === 'all' || sample.source === sourceFilter

    const matchesValidated =
      validatedFilter === 'all' ||
      (validatedFilter === 'validated' && sample.is_validated) ||
      (validatedFilter === 'pending' && !sample.is_validated)

    return matchesSearch && matchesSource && matchesValidated
  })

  const handleExport = async () => {
    try {
      toast.loading('Exporting...', { id: 'export' })
      const response = await trainingAPI.list({ limit: 1000 })
      
      const blob = new Blob([JSON.stringify(response.data, null, 2)], {
        type: 'application/json',
      })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `training_data_${new Date().toISOString().split('T')[0]}.json`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      
      toast.success('Exported successfully!', { id: 'export' })
    } catch (error) {
      toast.error('Export failed!', { id: 'export' })
    }
  }

  const handleBulkValidate = async () => {
    try {
      const unvalidatedIds = filteredSamples
        .filter((s) => !s.is_validated)
        .map((s) => s.id)
        .slice(0, 50) // Limit to 50 at a time

      if (unvalidatedIds.length === 0) {
        toast.error('No samples to validate!')
        return
      }

      toast.loading(`Validating ${unvalidatedIds.length} samples...`, { id: 'bulk' })
      await trainingAPI.bulkValidate({ sample_ids: unvalidatedIds })
      toast.success('Bulk validation completed!', { id: 'bulk' })
      fetchData()
    } catch (error) {
      toast.error('Bulk validation failed!', { id: 'bulk' })
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Database className="h-8 w-8" />
            Training Data
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Manage and annotate training samples for model improvement
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={fetchData} className="btn btn-secondary flex items-center gap-2">
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
          <button onClick={handleExport} className="btn btn-secondary flex items-center gap-2">
            <Download className="h-4 w-4" />
            Export
          </button>
          <button
            onClick={() => setShowImportModal(true)}
            className="btn btn-secondary flex items-center gap-2"
          >
            <Upload className="h-4 w-4" />
            Import
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="btn btn-primary flex items-center gap-2"
          >
            <Plus className="h-4 w-4" />
            Add Sample
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="card">
          <div className="text-sm text-gray-600 dark:text-gray-400">Total Samples</div>
          <div className="text-2xl font-bold text-gray-900 dark:text-white">
            {stats?.total_samples?.toLocaleString() || '0'}
          </div>
        </div>
        <div className="card">
          <div className="text-sm text-gray-600 dark:text-gray-400">Validated</div>
          <div className="text-2xl font-bold text-green-600">
            {stats?.validated_samples?.toLocaleString() || '0'}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            {stats?.validation_rate?.toFixed(1) || '0'}%
          </div>
        </div>
        <div className="card">
          <div className="text-sm text-gray-600 dark:text-gray-400">From Feedback</div>
          <div className="text-2xl font-bold text-blue-600">
            {stats?.feedback_samples?.toLocaleString() || '0'}
          </div>
        </div>
        <div className="card">
          <div className="text-sm text-gray-600 dark:text-gray-400">Avg Quality</div>
          <div className="text-2xl font-bold text-purple-600">
            {stats?.avg_quality?.toFixed(1) || '0'}/10
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
              placeholder="Search title or description..."
              className="input w-full pl-10"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <select
            className="input sm:w-40"
            value={sourceFilter}
            onChange={(e) => setSourceFilter(e.target.value)}
          >
            <option value="all">All Sources</option>
            <option value="feedback">Feedback</option>
            <option value="manual">Manual</option>
            <option value="import">Import</option>
          </select>
          <select
            className="input sm:w-40"
            value={validatedFilter}
            onChange={(e) => setValidatedFilter(e.target.value)}
          >
            <option value="all">All Status</option>
            <option value="validated">Validated</option>
            <option value="pending">Pending</option>
          </select>
          <button onClick={handleBulkValidate} className="btn btn-primary whitespace-nowrap">
            Bulk Validate
          </button>
        </div>
      </div>

      {/* Samples Table */}
      <div className="card overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <RefreshCw className="h-8 w-8 animate-spin text-primary-600" />
          </div>
        ) : filteredSamples.length === 0 ? (
          <div className="text-center py-12">
            <Database className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-500 dark:text-gray-400">No training samples found</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-700">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                    Title
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                    Category ID
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                    Source
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                    Created
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                {filteredSamples.map((sample) => (
                  <tr key={sample.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-900 dark:text-white max-w-md truncate">
                        {sample.title}
                      </div>
                      {sample.description && (
                        <div className="text-xs text-gray-500 dark:text-gray-400 max-w-md truncate">
                          {sample.description}
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <code className="text-sm font-mono bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded text-gray-900 dark:text-white">
                        {sample.actual_category_id}
                      </code>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="badge badge-info">{sample.source}</span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {sample.is_validated ? (
                        <span className="badge badge-success flex items-center gap-1 w-fit">
                          <CheckCircle className="h-3 w-3" />
                          Validated
                        </span>
                      ) : (
                        <span className="badge badge-warning">Pending</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                      {new Date(sample.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <button
                        onClick={() => {
                          setSelectedSample(sample)
                          setShowViewModal(true)
                        }}
                        className="text-blue-600 hover:text-blue-900 dark:text-blue-400"
                        title="View"
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
      {samples.length >= itemsPerPage && (
        <div className="flex justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="btn btn-secondary"
          >
            Previous
          </button>
          <span className="flex items-center px-4 text-gray-700 dark:text-gray-300">
            Page {page}
          </span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={samples.length < itemsPerPage}
            className="btn btn-secondary"
          >
            Next
          </button>
        </div>
      )}

      {/* Modals */}
      {showViewModal && selectedSample && (
        <ViewSampleModal
          sample={selectedSample}
          onClose={() => {
            setShowViewModal(false)
            setSelectedSample(null)
          }}
          onValidate={fetchData}
          onDelete={fetchData}
        />
      )}

      {showCreateModal && (
        <CreateSampleModal
          onClose={() => setShowCreateModal(false)}
          onCreated={fetchData}
        />
      )}

      {showImportModal && (
        <ImportModal
          onClose={() => setShowImportModal(false)}
          onImported={fetchData}
        />
      )}
    </div>
  )
}
