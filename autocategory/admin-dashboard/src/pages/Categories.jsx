import { useEffect, useState } from 'react'
import { categoriesAPI } from '../services/api'
import {
  FolderTree,
  Download,
  RefreshCw,
  ChevronRight,
  ChevronDown,
  CheckCircle,
  Clock,
  AlertCircle,
  Hammer,
  History,
  Globe,
  Zap,
  Settings2,
  Pencil,
} from 'lucide-react'
import toast from 'react-hot-toast'

// Category Tree Node Component
function CategoryNode({ category, level = 0, expandedNodes, toggleNode, onEdit }) {
  const hasChildren = category.children && category.children.length > 0
  const isExpanded = expandedNodes[category.id]

  return (
    <div>
      <div
        className={`py-2 px-3 hover:bg-gray-50 dark:hover:bg-gray-700 rounded group ${hasChildren ? 'cursor-pointer' : ''}`}
        style={{ paddingLeft: `${level * 1.5 + 0.5}rem` }}
        onClick={() => hasChildren && toggleNode(category.id)}
      >
        <div className="flex items-center gap-2">
          {hasChildren ? (
            isExpanded ? (
              <ChevronDown className="h-4 w-4 text-gray-500 flex-shrink-0" />
            ) : (
              <ChevronRight className="h-4 w-4 text-gray-500 flex-shrink-0" />
            )
          ) : (
            <div className="w-4 h-4 flex-shrink-0" />
          )}
          
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-gray-900 dark:text-white font-medium">{category.name}</span>
              <span className="text-sm text-gray-500 dark:text-gray-400">
                (ID: {category.id})
              </span>
              
              {hasChildren && (
                <span className="text-xs text-gray-400 dark:text-gray-500">
                  {category.children.length} subcategories
                </span>
              )}

              {!hasChildren && category.fields_count > 0 && (
                <span className="text-xs bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400 px-1.5 py-0.5 rounded">
                  {category.fields_count} thuộc tính
                </span>
              )}
              
              <span className="badge badge-success text-xs ml-auto">Active</span>

              <button
                onClick={(e) => { e.stopPropagation(); onEdit(category) }}
                className="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:bg-blue-100 dark:hover:bg-blue-900/40 text-blue-600 dark:text-blue-400 flex-shrink-0"
                title="Sửa tên / mô tả"
              >
                <Pencil className="h-3.5 w-3.5" />
              </button>
            </div>
            
            {category.description && (
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1 line-clamp-2">
                {category.description}
              </p>
            )}
          </div>
        </div>
      </div>

      {isExpanded && hasChildren && (
        <div>
          {category.children.map((child) => (
            <CategoryNode
              key={child.id}
              category={child}
              level={level + 1}
              expandedNodes={expandedNodes}
              toggleNode={toggleNode}
              onEdit={onEdit}
            />
          ))}
        </div>
      )}
    </div>
  )
}

// Edit Category Modal
function EditCategoryModal({ category, onClose, onSaved }) {
  const [name, setName] = useState(category.name || '')
  const [description, setDescription] = useState(category.description || '')
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    if (!name.trim()) {
      toast.error('Tên danh mục không được để trống!')
      return
    }
    setSaving(true)
    try {
      await categoriesAPI.updateCategory(category.id, {
        name: name.trim(),
        description: description.trim() || null,
      })
      toast.success(`Đã cập nhật danh mục "${name.trim()}"`)
      onSaved({ ...category, name: name.trim(), description: description.trim() || null })
      onClose()
    } catch (error) {
      toast.error('Lỗi cập nhật: ' + (error.response?.data?.detail || error.message))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-lg shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Pencil className="h-5 w-5 text-blue-500" />
            Sửa danh mục #{category.id}
          </h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 text-xl leading-none">✕</button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Tên danh mục <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="Tên danh mục..."
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Mô tả
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={5}
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500 resize-y"
              placeholder="Mô tả danh mục (dùng cho vector search)..."
            />
            <p className="text-xs text-gray-400 mt-1">
              Mô tả chi tiết, đầy đủ từ khóa sẽ giúp phân loại chính xác hơn.
            </p>
          </div>
        </div>

        <div className="flex gap-2 justify-end mt-6">
          <button onClick={onClose} className="btn btn-secondary">Hủy</button>
          <button onClick={handleSave} disabled={saving} className="btn btn-primary flex items-center gap-2">
            {saving ? <RefreshCw className="h-4 w-4 animate-spin" /> : <CheckCircle className="h-4 w-4" />}
            {saving ? 'Đang lưu...' : 'Lưu thay đổi'}
          </button>
        </div>
      </div>
    </div>
  )
}

// Sync History Modal
function SyncHistoryModal({ onClose }) {
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const response = await categoriesAPI.syncHistory()
        setHistory(response.data)
      } catch (error) {
        toast.error('Failed to load sync history!')
      } finally {
        setLoading(false)
      }
    }
    fetchHistory()
  }, [])

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-4xl max-h-[80vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">
            Sync History
          </h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
            ✕
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <RefreshCw className="h-8 w-8 animate-spin text-primary-600" />
          </div>
        ) : history.length === 0 ? (
          <div className="text-center py-12">
            <History className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-500 dark:text-gray-400">No sync history yet</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-700">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-300">
                    Date
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-300">
                    Source
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-300">
                    Type
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-300">
                    Changes
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-300">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                {history.map((sync) => (
                  <tr key={sync.id}>
                    <td className="px-4 py-3 text-sm text-gray-900 dark:text-white">
                      {new Date(sync.synced_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                      {sync.source || 'N/A'}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <span className="badge badge-info">{sync.sync_type}</span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                      +{sync.categories_added} / ~{sync.categories_modified} / -{sync.categories_deleted}
                    </td>
                    <td className="px-4 py-3">
                      {sync.success ? (
                        <span className="badge badge-success">Success</span>
                      ) : (
                        <span className="badge badge-danger" title={sync.error_message}>
                          Failed
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

// Rebuild Confirmation Modal
function RebuildModal({ onClose, onConfirm }) {
  const [phase, setPhase] = useState('confirm') // confirm | running | done | error
  const [result, setResult] = useState(null)
  const [errorMsg, setErrorMsg] = useState('')

  const handleRebuild = async () => {
    setPhase('running')
    try {
      await categoriesAPI.rebuildIndex()
    } catch (error) {
      setPhase('error')
      setErrorMsg(error.response?.data?.detail || error.message)
      return
    }
    // Poll until done or error
    const poll = setInterval(async () => {
      try {
        const res = await categoriesAPI.rebuildIndexStatus()
        const job = res.data
        if (job.status === 'done') {
          clearInterval(poll)
          setResult(job.result)
          setPhase('done')
          toast.success(`Rebuilt: ${job.result.categories_indexed} categories, ${job.result.attributes_indexed} attribute options (${job.result.time_taken_seconds}s)`)
          onConfirm()
        } else if (job.status === 'error') {
          clearInterval(poll)
          setPhase('error')
          setErrorMsg(job.error || 'Unknown error')
        }
      } catch (e) {
        // ignore transient poll errors
      }
    }, 3000)
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-md">
        <h2 className="text-xl font-bold text-red-600 mb-4">Rebuild Qdrant Index</h2>

        {phase === 'confirm' && (
          <>
            <p className="text-gray-700 dark:text-gray-300 mb-4">
              This will rebuild the entire Qdrant vector index. This may take several minutes and will temporarily affect classification performance.
            </p>
            <p className="text-gray-700 dark:text-gray-300 mb-6">
              <strong>Are you sure you want to continue?</strong>
            </p>
            <div className="flex gap-2 justify-end">
              <button onClick={onClose} className="btn btn-secondary">Cancel</button>
              <button onClick={handleRebuild} className="btn btn-danger">Rebuild Index</button>
            </div>
          </>
        )}

        {phase === 'running' && (
          <div className="text-center py-6">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-red-600 mx-auto mb-4"></div>
            <p className="text-gray-700 dark:text-gray-300">Rebuilding index in background…</p>
            <p className="text-sm text-gray-500 mt-2">This may take several minutes. You can close this dialog and the rebuild will continue.</p>
            <button onClick={onClose} className="btn btn-secondary mt-4">Close</button>
          </div>
        )}

        {phase === 'done' && (
          <div className="text-center py-4">
            <p className="text-green-600 font-semibold text-lg mb-2">✓ Rebuild complete</p>
            {result && (
              <p className="text-gray-700 dark:text-gray-300 text-sm">
                {result.categories_indexed} categories · {result.attributes_indexed} attribute options · {result.time_taken_seconds}s
              </p>
            )}
            <button onClick={onClose} className="btn btn-primary mt-4">Close</button>
          </div>
        )}

        {phase === 'error' && (
          <div className="py-4">
            <p className="text-red-600 font-semibold mb-2">✗ Rebuild failed</p>
            <pre className="text-xs bg-gray-100 dark:bg-gray-900 p-2 rounded overflow-auto max-h-40">{errorMsg}</pre>
            <div className="flex gap-2 justify-end mt-4">
              <button onClick={onClose} className="btn btn-secondary">Close</button>
              <button onClick={() => { setPhase('confirm'); setErrorMsg('') }} className="btn btn-danger">Retry</button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────
// Omni Sync Panel
// ─────────────────────────────────────────────

function OmniSyncPanel({ onSynced }) {
  const [omniUrl, setOmniUrl] = useState('')
  const [syncMode, setSyncMode] = useState('manual') // 'manual' | 'auto'
  const [syncType, setSyncType] = useState('full')   // 'categories' | 'attributes' | 'full'
  const [generateDesc, setGenerateDesc] = useState(false)
  const [loading, setLoading] = useState(false)
  const [loadingDesc, setLoadingDesc] = useState(false)
  const [descProgress, setDescProgress] = useState(null)
  const [lastResult, setLastResult] = useState(null)
  const [configLoaded, setConfigLoaded] = useState(false)

  useEffect(() => {
    categoriesAPI.omniConfig()
      .then((res) => {
        setOmniUrl(res.data.omni_base_url || '')
        setSyncMode(res.data.omni_sync_mode || 'manual')
        setConfigLoaded(true)
      })
      .catch(() => setConfigLoaded(true))
  }, [])

  const handleGenerateDescriptions = async (force = false) => {
    setLoadingDesc(true)
    setDescProgress(force ? 'Đang sinh lại mô tả (toàn bộ)...' : 'Đang sinh mô tả tối ưu cho vector search...')
    try {
      const res = await categoriesAPI.generateDescriptions({ force })
      const r = res.data
      setDescProgress(null)
      toast.success(`Đã sinh mô tả cho ${r.updated} danh mục (bỏ qua ${r.skipped})`)
    } catch (e) {
      setDescProgress(null)
      toast.error('Lỗi sinh mô tả: ' + (e.response?.data?.detail || e.message))
    } finally {
      setLoadingDesc(false)
    }
  }

  const handleSync = async () => {
    if (!omniUrl.trim()) {
      toast.error('Nhập Base URL của API omni trước!')
      return
    }
    setLoading(true)
    setLastResult(null)
    try {
      const res = await categoriesAPI.syncOmni({ sync_type: syncType, base_url: omniUrl.trim() })
      setLastResult(res.data.result)
      toast.success('Đồng bộ từ omni thành công!')
      onSynced?.()

      if (generateDesc) {
        setLoading(false)
        await handleGenerateDescriptions(false)
        return
      }
    } catch (e) {
      const msg = e.response?.data?.detail || e.message
      toast.error('Lỗi đồng bộ: ' + msg)
    } finally {
      setLoading(false)
    }
  }

  if (!configLoaded) return null

  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-4">
        <Globe className="h-5 w-5 text-blue-500" />
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
          Đồng bộ từ Omni API
        </h2>
        <span className="ml-auto text-xs bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 px-2 py-0.5 rounded-full">
          {syncMode === 'auto' ? '⚡ Auto' : '🔧 Manual'}
        </span>
      </div>

      <div className="space-y-4">
        {/* Base URL */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Base URL của API
          </label>
          <input
            type="url"
            className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
            placeholder="https://your-api-server.example.com"
            value={omniUrl}
            onChange={(e) => setOmniUrl(e.target.value)}
          />
          <p className="text-xs text-gray-400 mt-1">
            API sẽ gọi: <code className="bg-gray-100 dark:bg-gray-800 px-1 rounded">{omniUrl || '<BASE_URL>'}/api/v1/app/categories</code>
          </p>
        </div>

        <div className="grid grid-cols-2 gap-4">
          {/* Sync Type */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Loại đồng bộ
            </label>
            <select
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
              value={syncType}
              onChange={(e) => setSyncType(e.target.value)}
            >
              <option value="full">Đầy đủ (danh mục + thuộc tính)</option>
              <option value="categories">Chỉ danh mục</option>
              <option value="attributes">Chỉ thuộc tính</option>
            </select>
          </div>

          {/* Sync Mode */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Chế độ
            </label>
            <select
              className="w-full border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
              value={syncMode}
              onChange={(e) => setSyncMode(e.target.value)}
            >
              <option value="manual">Manual – Đồng bộ khi nhấn nút</option>
              <option value="auto">Auto – Tự động theo lịch</option>
            </select>
          </div>
        </div>

        {syncMode === 'auto' && (
          <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3 text-sm text-blue-700 dark:text-blue-300 flex gap-2">
            <Zap className="h-4 w-4 flex-shrink-0 mt-0.5" />
            <span>
              Chế độ Auto: cần thêm <code>OMNI_BASE_URL</code> và <code>OMNI_SYNC_MODE=auto</code> vào file <code>.env</code>, sau đó restart container.
            </span>
          </div>
        )}

        {/* AI description option */}
        <label className="flex items-start gap-3 cursor-pointer bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg p-3">
          <input
            type="checkbox"
            className="mt-0.5"
            checked={generateDesc}
            onChange={(e) => setGenerateDesc(e.target.checked)}
          />
          <div>
            <div className="text-sm font-medium text-purple-800 dark:text-purple-300">
              🤖 Tự sinh mô tả đầy đủ bằng AI sau khi đồng bộ
            </div>
            <div className="text-xs text-purple-600 dark:text-purple-400 mt-0.5">
              Dùng LLM để viết lại description phong phú cho từng danh mục (API omni thường có mô tả sơ sài). Mất thêm vài phút.
            </div>
          </div>
        </label>

        {/* AI description progress */}
        {descProgress && (
          <div className="bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg p-3 text-sm text-purple-700 dark:text-purple-300 flex items-center gap-2">
            <RefreshCw className="h-4 w-4 animate-spin flex-shrink-0" />
            {descProgress}
          </div>
        )}

        {/* Last result */}
        {lastResult && (
          <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-3 text-sm">
            <div className="flex items-center gap-2 text-green-700 dark:text-green-400 font-medium mb-1">
              <CheckCircle className="h-4 w-4" />
              Đồng bộ thành công
            </div>
            {lastResult.categories_synced != null && (
              <p className="text-green-600 dark:text-green-400">
                Đã đồng bộ <strong>{lastResult.categories_synced}</strong> danh mục
              </p>
            )}
            {(lastResult.categories_with_fields != null || lastResult.categories_with_attributes != null) && (
              <p className="text-green-600 dark:text-green-400">
                Fields: <strong>{lastResult.categories_with_fields ?? lastResult.categories_with_attributes}</strong> / {lastResult.categories_checked} danh mục
              </p>
            )}
          </div>
        )}

        <div className="flex gap-2">
          <button
            onClick={handleSync}
            disabled={loading || loadingDesc}
            className={`flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg font-medium text-white transition-all
              ${(loading || loadingDesc) ? 'bg-blue-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'}`}
          >
            {loading ? (
              <RefreshCw className="h-4 w-4 animate-spin" />
            ) : (
              <Globe className="h-4 w-4" />
            )}
            {loading ? 'Đang đồng bộ...' : 'Đồng bộ ngay'}
          </button>
          <button
            onClick={() => handleGenerateDescriptions(false)}
            disabled={loading || loadingDesc}
            title="Sinh keyword-dense description cho các danh mục chưa có/còn sơ sài (phục vụ vector search)"
            className={`flex items-center gap-1 px-3 py-2 rounded-lg text-sm font-medium text-white transition-all
              ${(loading || loadingDesc) ? 'bg-purple-400 cursor-not-allowed' : 'bg-purple-600 hover:bg-purple-700'}`}
          >
            {loadingDesc ? <RefreshCw className="h-4 w-4 animate-spin" /> : '🤖'}
            {loadingDesc ? '' : 'Sinh mô tả'}
          </button>
          <button
            onClick={() => handleGenerateDescriptions(true)}
            disabled={loading || loadingDesc}
            title="Sinh lại toàn bộ — ghi đè mô tả cũ (kể cả mô tả marketing không tối ưu)"
            className={`flex items-center gap-1 px-3 py-2 rounded-lg text-sm font-medium transition-all
              ${(loading || loadingDesc) ? 'bg-gray-200 text-gray-400 cursor-not-allowed' : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'}`}
          >
            ↺ Sinh lại tất cả
          </button>
        </div>
      </div>
    </div>
  )
}

export default function Categories() {
  const [categories, setCategories] = useState([])
  const [stats, setStats] = useState(null)
  const [syncStatus, setSyncStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [expandedNodes, setExpandedNodes] = useState({})

  const [showSyncHistory, setShowSyncHistory] = useState(false)
  const [showRebuildModal, setShowRebuildModal] = useState(false)
  const [editingCategory, setEditingCategory] = useState(null)
  const [searchTerm, setSearchTerm] = useState('')

  const fetchData = async () => {
    try {
      setLoading(true)
      const [listRes, countRes] = await Promise.all([
        categoriesAPI.list(),
        categoriesAPI.count().catch(() => null),
      ])

      // Build tree from flat list
      const flatCategories = listRes.data.categories || []
      const tree = buildTree(flatCategories)
      setCategories(tree)

      // Use /count endpoint if available, otherwise calculate from list
      if (countRes?.data) {
        const c = countRes.data
        setStats({
          total: c.total_categories,
          leaf: c.leaf_categories,
          active: c.active_categories,
          indexed: c.leaf_categories,
          fields: c.fields_count,
        })
      } else {
        const total = flatCategories.length
        const leafCount = flatCategories.filter(
          cat => !flatCategories.some(c => c.parent_id === cat.category_id)
        ).length
        setStats({ total, leaf: leafCount, active: total, indexed: leafCount })
      }

      setSyncStatus(null)
    } catch (error) {
      toast.error('Failed to load categories data!')
    } finally {
      setLoading(false)
    }
  }

  const buildTree = (flatList) => {
    const map = {}
    const roots = []

    // Create map - normalize category_id to id for consistent access
    flatList.forEach(item => {
      const normalized = { 
        ...item, 
        id: item.category_id || item.id,
        children: [] 
      }
      map[normalized.id] = normalized
    })

    // Build tree
    flatList.forEach(item => {
      const id = item.category_id || item.id
      if (item.parent_id === null || item.parent_id === undefined) {
        roots.push(map[id])
      } else if (map[item.parent_id]) {
        map[item.parent_id].children.push(map[id])
      }
    })

    return roots
  }

  useEffect(() => {
    fetchData()
  }, [])

  const toggleNode = (nodeId) => {
    setExpandedNodes((prev) => ({
      ...prev,
      [nodeId]: !prev[nodeId],
    }))
  }

  const expandAll = () => {
    const allNodeIds = {}
    const collectIds = (cats) => {
      cats.forEach((cat) => {
        allNodeIds[cat.id] = true
        if (cat.children) collectIds(cat.children)
      })
    }
    collectIds(categories)
    setExpandedNodes(allNodeIds)
  }

  const collapseAll = () => {
    setExpandedNodes({})
  }

  // Update local tree after edit (avoids full reload)
  const handleCategorySaved = (updated) => {
    const updateTree = (nodes) =>
      nodes.map((n) => {
        if (n.id === updated.id) return { ...n, name: updated.name, description: updated.description }
        if (n.children?.length) return { ...n, children: updateTree(n.children) }
        return n
      })
    setCategories((prev) => updateTree(prev))
  }

  const handleExport = async () => {
    try {
      const response = await categoriesAPI.export()
      const data = response.data
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `categories_export_${new Date().toISOString().split('T')[0]}.json`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      const count = Array.isArray(data) ? data.length : Object.keys(data).length
      toast.success(`Đã xuất ${count} danh mục (bao gồm thuộc tính)!`)
    } catch (error) {
      toast.error('Export thất bại!')
    }
  }

  const handleSync = async () => {
    try {
      toast.loading('Building vector index...', { id: 'sync' })
      const result = await categoriesAPI.buildIndex()
      toast.success(`Index built: ${result.data.categories_indexed} leaf categories indexed!`, { id: 'sync' })
      fetchData()
    } catch (error) {
      toast.error('Build index failed: ' + (error.response?.data?.detail || error.message), { id: 'sync' })
    }
  }

  const getSyncStatusBadge = () => {
    if (!syncStatus) {
      return <span className="badge badge-secondary">Never Synced</span>
    }
    
    const hoursSinceSync = (Date.now() - new Date(syncStatus.synced_at)) / (1000 * 60 * 60)
    
    if (!syncStatus.success) {
      return <span className="badge badge-danger">Last Sync Failed</span>
    }
    if (hoursSinceSync > 24) {
      return <span className="badge badge-warning">Outdated</span>
    }
    return <span className="badge badge-success">Up to Date</span>
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <FolderTree className="h-8 w-8" />
            Categories Management
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Manage product categories and Qdrant index
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
          <button onClick={handleSync} className="btn btn-primary flex items-center gap-2">
            <RefreshCw className="h-4 w-4" />
            Build Index
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-5 gap-4">
        <div className="card">
          <div className="text-sm text-gray-600 dark:text-gray-400">Total Categories</div>
          <div className="text-2xl font-bold text-gray-900 dark:text-white">
            {stats?.total?.toLocaleString() || '0'}
          </div>
        </div>
        <div className="card">
          <div className="text-sm text-gray-600 dark:text-gray-400">Leaf Categories</div>
          <div className="text-2xl font-bold text-green-600">
            {stats?.leaf?.toLocaleString() || '0'}
          </div>
        </div>
        <div className="card">
          <div className="text-sm text-gray-600 dark:text-gray-400">Active</div>
          <div className="text-2xl font-bold text-blue-600">
            {stats?.active?.toLocaleString() || '0'}
          </div>
        </div>
        <div className="card">
          <div className="text-sm text-gray-600 dark:text-gray-400">Indexed</div>
          <div className="text-2xl font-bold text-purple-600">
            {stats?.indexed?.toLocaleString() || '0'}
          </div>
        </div>
        <div className="card">
          <div className="text-sm text-gray-600 dark:text-gray-400">Fields</div>
          <div className="text-2xl font-bold text-orange-600">
            {stats?.fields?.toLocaleString() || '0'}
          </div>
        </div>
      </div>

      {/* Sync Status - Hidden since no sync API */}
      {false && (
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Sync Status
          </h2>
          {getSyncStatusBadge()}
        </div>

        {syncStatus ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-gray-600 dark:text-gray-400">Last Synced:</span>
              <div className="font-medium text-gray-900 dark:text-white">
                {new Date(syncStatus.synced_at).toLocaleString()}
              </div>
            </div>
            <div>
              <span className="text-gray-600 dark:text-gray-400">Type:</span>
              <div className="font-medium text-gray-900 dark:text-white">
                {syncStatus.sync_type}
              </div>
            </div>
            <div>
              <span className="text-gray-600 dark:text-gray-400">Changes:</span>
              <div className="font-medium text-gray-900 dark:text-white">
                +{syncStatus.categories_added} / ~{syncStatus.categories_modified} / -
                {syncStatus.categories_deleted}
              </div>
            </div>
          </div>
        ) : (
          <p className="text-gray-500 dark:text-gray-400">No sync history available</p>
        )}

        <div className="mt-4 flex gap-2">
          <button onClick={() => setShowSyncHistory(true)} className="btn btn-secondary text-sm">
            <History className="h-4 w-4 mr-2" />
            View History
          </button>
        </div>
      </div>
      )}

      {/* Qdrant Index Status */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <Hammer className="h-5 w-5" />
            Qdrant Index
          </h2>
          <button
            onClick={() => setShowRebuildModal(true)}
            className="btn btn-danger text-sm flex items-center gap-2"
          >
            <RefreshCw className="h-4 w-4" />
            Rebuild Index
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-600 dark:text-gray-400">Collection Name:</span>
            <div className="font-medium text-gray-900 dark:text-white font-mono">
              categories
            </div>
          </div>
          <div>
            <span className="text-gray-600 dark:text-gray-400">Indexed Vectors:</span>
            <div className="font-medium text-gray-900 dark:text-white">
              {stats?.indexed?.toLocaleString() || '0'}
            </div>
          </div>
        </div>

        <div className="mt-4 bg-yellow-50 dark:bg-yellow-900 border border-yellow-200 dark:border-yellow-700 rounded p-3">
          <p className="text-sm text-yellow-800 dark:text-yellow-200">
            <strong>⚠️ Note:</strong> Rebuilding the index will re-embed all categories and may take several minutes. 
            Classification requests will still work but may be slower during the rebuild.
          </p>
        </div>
      </div>

      {/* Omni Sync */}
      <OmniSyncPanel onSynced={fetchData} />

      {/* Category Tree */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Category Tree
          </h2>
          <div className="flex gap-2">
            <button onClick={expandAll} className="text-sm text-blue-600 hover:text-blue-800">
              Expand All
            </button>
            <button onClick={collapseAll} className="text-sm text-blue-600 hover:text-blue-800">
              Collapse All
            </button>
          </div>
        </div>

        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="text-gray-500 dark:text-gray-400 mt-4">Loading categories...</p>
          </div>
        ) : categories.length > 0 ? (
          <div className="max-h-[600px] overflow-y-auto border border-gray-200 dark:border-gray-700 rounded">
            {categories.map((category) => (
              <CategoryNode
                key={category.id}
                category={category}
                level={0}
                expandedNodes={expandedNodes}
                toggleNode={toggleNode}
                onEdit={setEditingCategory}
              />
            ))}
          </div>
        ) : (
          <div className="text-center py-12 bg-gray-50 dark:bg-gray-700 rounded">
            <FolderTree className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-500 dark:text-gray-400 mb-2">
              No categories found
            </p>
            <p className="text-sm text-gray-400 dark:text-gray-500">
              Import categories from JSON file to get started
            </p>
          </div>
        )}
      </div>

      {/* Modals */}
      {showSyncHistory && (
        <SyncHistoryModal onClose={() => setShowSyncHistory(false)} />
      )}

      {showRebuildModal && (
        <RebuildModal
          onClose={() => setShowRebuildModal(false)}
          onConfirm={fetchData}
        />
      )}

      {editingCategory && (
        <EditCategoryModal
          category={editingCategory}
          onClose={() => setEditingCategory(null)}
          onSaved={handleCategorySaved}
        />
      )}
    </div>
  )
}
