import { useState } from 'react'
import {
  Camera,
  FileText,
  Layers,
  Loader2,
  CheckCircle,
  Tag,
  ChevronDown,
  ChevronRight,
  ImageIcon,
  Sparkles,
  AlertCircle,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { generateAPI } from '../services/api'

// ─────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────

function AttributeList({ attributes }) {
  if (!attributes || attributes.length === 0) return null
  return (
    <div className="mt-3">
      <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase mb-2">
        Thuộc tính danh mục
      </p>
      <div className="grid grid-cols-2 gap-2">
        {attributes.map((attr, i) => (
          <div
            key={i}
            className="text-xs bg-blue-50 dark:bg-blue-900/20 rounded px-2 py-1 border border-blue-200 dark:border-blue-800"
          >
            <span className="font-medium text-blue-700 dark:text-blue-300">{attr.name || attr.label}</span>
            {attr.type && (
              <span className="ml-1 text-blue-400">({attr.type})</span>
            )}
            {attr.options && attr.options.length > 0 && (
              <span className="block text-blue-500 truncate">
                {attr.options.slice(0, 3).join(', ')}{attr.options.length > 3 ? '…' : ''}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

function CategoryCard({ category }) {
  if (!category) return null
  return (
    <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-4 border border-green-200 dark:border-green-800">
      <div className="flex items-center gap-2 mb-2">
        <Tag className="h-4 w-4 text-green-600" />
        <span className="font-semibold text-green-700 dark:text-green-300">Danh mục đề xuất</span>
        {category.confidence != null && (
          <span className="ml-auto text-xs font-bold text-green-600">
            {Math.round(category.confidence * 100)}%
          </span>
        )}
      </div>
      <p className="text-sm font-medium text-gray-900 dark:text-white">{category.category_name}</p>
      {category.category_path && (
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{category.category_path}</p>
      )}
      {category.decision && (
        <span className={`inline-block mt-2 text-xs px-2 py-0.5 rounded-full font-medium
          ${category.decision === 'auto_assign' ? 'bg-green-200 text-green-800' :
            category.decision === 'preselect' ? 'bg-yellow-200 text-yellow-800' :
            'bg-gray-200 text-gray-700'}`}>
          {category.decision}
        </span>
      )}
      {category.llm_reason && (
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-2 italic">
          "{category.llm_reason}"
        </p>
      )}
      <AttributeList attributes={category.attributes} />
    </div>
  )
}

function ResultCard({ result, mode }) {
  const [showRaw, setShowRaw] = useState(false)

  if (!result) return null

  const generated = result.generated || result
  const category = generated.category_suggestion || result.category_suggestion
  const detectedAttrs = generated.detected_attributes

  return (
    <div className="mt-6 space-y-4">
      <div className="flex items-center gap-2 text-green-600">
        <CheckCircle className="h-5 w-5" />
        <span className="font-semibold">Kết quả phân tích</span>
      </div>

      {/* Generated title */}
      {(generated.title || result.generated_title) && (
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border dark:border-gray-700">
          <p className="text-xs text-gray-500 uppercase mb-1">Tiêu đề gợi ý</p>
          <p className="font-semibold text-gray-900 dark:text-white">
            {generated.title || result.generated_title}
          </p>
        </div>
      )}

      {/* Generated description */}
      {(generated.description || result.generated_description) && (
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border dark:border-gray-700">
          <p className="text-xs text-gray-500 uppercase mb-1">Mô tả gợi ý</p>
          <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-line">
            {generated.description || result.generated_description}
          </p>
        </div>
      )}

      {/* Price suggestion */}
      {generated.price_suggestion?.estimate && (
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border dark:border-gray-700">
          <p className="text-xs text-gray-500 uppercase mb-1">Giá gợi ý</p>
          <p className="font-bold text-orange-600 text-lg">
            {generated.price_suggestion.estimate.toLocaleString('vi-VN')} đ
          </p>
          {generated.price_suggestion.range && (
            <p className="text-xs text-gray-400 mt-1">
              Khoảng: {generated.price_suggestion.range[0].toLocaleString('vi-VN')} –{' '}
              {generated.price_suggestion.range[1].toLocaleString('vi-VN')} đ
            </p>
          )}
          {generated.price_suggestion.reasoning && (
            <p className="text-xs italic text-gray-400 mt-1">{generated.price_suggestion.reasoning}</p>
          )}
        </div>
      )}

      {/* Detected attributes from image */}
      {detectedAttrs && Object.keys(detectedAttrs).length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border dark:border-gray-700">
          <p className="text-xs text-gray-500 uppercase mb-2">Thông tin phát hiện từ ảnh</p>
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(detectedAttrs).map(([k, v]) =>
              v ? (
                <div key={k} className="text-sm">
                  <span className="text-gray-500">{k}: </span>
                  <span className="font-medium text-gray-900 dark:text-white">{v}</span>
                </div>
              ) : null
            )}
          </div>
        </div>
      )}

      {/* Category suggestion */}
      <CategoryCard category={category} />

      {/* Candidates */}
      {result.candidates && result.candidates.length > 0 && (
        <div>
          <p className="text-xs text-gray-500 uppercase mb-2">Các danh mục khác</p>
          <div className="space-y-1">
            {result.candidates.slice(0, 3).map((c, i) => (
              <div key={i} className="flex items-center gap-2 text-sm bg-gray-50 dark:bg-gray-800 rounded px-3 py-2">
                <span className="text-gray-400 w-4">{i + 1}.</span>
                <span className="text-gray-700 dark:text-gray-300">{c.name || c.category_name}</span>
                {c.similarity_score != null && (
                  <span className="ml-auto text-xs text-gray-400">{Math.round(c.similarity_score * 100)}%</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Raw JSON toggle */}
      <div>
        <button
          className="text-xs text-gray-400 hover:text-gray-600 flex items-center gap-1"
          onClick={() => setShowRaw(!showRaw)}
        >
          {showRaw ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
          Raw JSON
        </button>
        {showRaw && (
          <pre className="mt-2 text-xs bg-gray-900 text-green-400 rounded-lg p-3 overflow-auto max-h-64">
            {JSON.stringify(result, null, 2)}
          </pre>
        )}
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────
// Main Page
// ─────────────────────────────────────────────

export default function PostTester() {
  const [imageUrls, setImageUrls] = useState('')
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [price, setPrice] = useState('')
  const [loading, setLoading] = useState(null) // 'image' | 'text' | 'full'
  const [result, setResult] = useState(null)
  const [activeMode, setActiveMode] = useState(null)
  const [error, setError] = useState(null)

  const getImageList = () =>
    imageUrls
      .split('\n')
      .map((u) => u.trim())
      .filter(Boolean)

  const handleImageOnly = async () => {
    const imgs = getImageList()
    if (imgs.length === 0) {
      toast.error('Nhập ít nhất 1 URL ảnh!')
      return
    }
    setLoading('image')
    setResult(null)
    setError(null)
    setActiveMode('image')
    try {
      const res = await generateAPI.fromImages({
        image_urls: imgs,
        existing_title: title,
        existing_description: description,
        generate_category: true,
      })
      setResult(res.data)
      toast.success('Phân tích ảnh thành công!')
    } catch (e) {
      const msg = e.response?.data?.detail || e.message
      setError(msg)
      toast.error('Lỗi: ' + msg)
    } finally {
      setLoading(null)
    }
  }

  const handleTextOnly = async () => {
    if (!title.trim()) {
      toast.error('Nhập tiêu đề trước!')
      return
    }
    setLoading('text')
    setResult(null)
    setError(null)
    setActiveMode('text')
    try {
      const res = await generateAPI.fromText({
        title,
        description,
        price: price ? parseFloat(price) : null,
      })
      setResult(res.data)
      toast.success('Phân loại thành công!')
    } catch (e) {
      const msg = e.response?.data?.detail || e.message
      setError(msg)
      toast.error('Lỗi: ' + msg)
    } finally {
      setLoading(null)
    }
  }

  const handleFull = async () => {
    const imgs = getImageList()
    if (imgs.length === 0) {
      toast.error('Nhập ít nhất 1 URL ảnh!')
      return
    }
    setLoading('full')
    setResult(null)
    setError(null)
    setActiveMode('full')
    try {
      const res = await generateAPI.full({
        image_urls: imgs,
        title,
        description,
        price: price ? parseFloat(price) : null,
      })
      setResult(res.data)
      toast.success('Phân tích đầy đủ thành công!')
    } catch (e) {
      const msg = e.response?.data?.detail || e.message
      setError(msg)
      toast.error('Lỗi: ' + msg)
    } finally {
      setLoading(null)
    }
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Kiểm tra Đăng Bài</h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">
          Thử 3 chế độ AI phân tích sản phẩm
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Input Panel */}
        <div className="space-y-4">
          {/* Image URLs */}
          <div className="card bg-base-100 dark:bg-gray-800 shadow p-4 rounded-xl border dark:border-gray-700">
            <div className="flex items-center gap-2 mb-2">
              <ImageIcon className="h-4 w-4 text-blue-500" />
              <label className="font-semibold text-gray-700 dark:text-gray-300 text-sm">
                URL Ảnh <span className="text-gray-400 font-normal">(mỗi dòng 1 URL)</span>
              </label>
            </div>
            <textarea
              className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg p-3 bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              rows={4}
              placeholder="https://example.com/image1.jpg&#10;https://example.com/image2.jpg"
              value={imageUrls}
              onChange={(e) => setImageUrls(e.target.value)}
            />
          </div>

          {/* Title */}
          <div className="card bg-base-100 dark:bg-gray-800 shadow p-4 rounded-xl border dark:border-gray-700">
            <label className="font-semibold text-gray-700 dark:text-gray-300 text-sm block mb-2">
              Tiêu đề
            </label>
            <input
              type="text"
              className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg p-3 bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="VD: iPhone 15 Pro Max 256GB..."
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>

          {/* Description */}
          <div className="card bg-base-100 dark:bg-gray-800 shadow p-4 rounded-xl border dark:border-gray-700">
            <label className="font-semibold text-gray-700 dark:text-gray-300 text-sm block mb-2">
              Mô tả
            </label>
            <textarea
              className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg p-3 bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              rows={3}
              placeholder="Mô tả sản phẩm..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>

          {/* Price */}
          <div className="card bg-base-100 dark:bg-gray-800 shadow p-4 rounded-xl border dark:border-gray-700">
            <label className="font-semibold text-gray-700 dark:text-gray-300 text-sm block mb-2">
              Giá (VNĐ) <span className="text-gray-400 font-normal">- tùy chọn</span>
            </label>
            <input
              type="number"
              className="w-full text-sm border border-gray-300 dark:border-gray-600 rounded-lg p-3 bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="VD: 15000000"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
            />
          </div>

          {/* 3 Action buttons */}
          <div className="space-y-3">
            {/* Nút 1: From Images */}
            <button
              onClick={handleImageOnly}
              disabled={!!loading}
              className={`w-full flex items-center justify-center gap-3 px-4 py-3 rounded-xl font-semibold text-white transition-all
                ${loading === 'image' ? 'bg-blue-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700 active:scale-95'}`}
            >
              {loading === 'image' ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <Camera className="h-5 w-5" />
              )}
              <div className="text-left">
                <div className="text-sm font-bold">Nút 1: Phân tích từ Ảnh</div>
                <div className="text-xs opacity-80">AI đọc ảnh → tự sinh tiêu đề + danh mục + thuộc tính</div>
              </div>
            </button>

            {/* Nút 2: From Text */}
            <button
              onClick={handleTextOnly}
              disabled={!!loading}
              className={`w-full flex items-center justify-center gap-3 px-4 py-3 rounded-xl font-semibold text-white transition-all
                ${loading === 'text' ? 'bg-emerald-400 cursor-not-allowed' : 'bg-emerald-600 hover:bg-emerald-700 active:scale-95'}`}
            >
              {loading === 'text' ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <FileText className="h-5 w-5" />
              )}
              <div className="text-left">
                <div className="text-sm font-bold">Nút 2: Phân loại từ Tiêu đề / Mô tả</div>
                <div className="text-xs opacity-80">Tiêu đề + mô tả → danh mục + thuộc tính cần điền</div>
              </div>
            </button>

            {/* Nút 3: Full */}
            <button
              onClick={handleFull}
              disabled={!!loading}
              className={`w-full flex items-center justify-center gap-3 px-4 py-3 rounded-xl font-semibold text-white transition-all
                ${loading === 'full' ? 'bg-purple-400 cursor-not-allowed' : 'bg-purple-600 hover:bg-purple-700 active:scale-95'}`}
            >
              {loading === 'full' ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <Layers className="h-5 w-5" />
              )}
              <div className="text-left">
                <div className="text-sm font-bold">Nút 3: Phân tích Đầy đủ</div>
                <div className="text-xs opacity-80">Ảnh + tiêu đề + mô tả → phân tích toàn diện</div>
              </div>
            </button>
          </div>

          {/* Mode indicator */}
          {activeMode && (
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <Sparkles className="h-4 w-4" />
              <span>
                Chế độ:{' '}
                <strong>
                  {activeMode === 'image' ? 'Từ ảnh' : activeMode === 'text' ? 'Từ văn bản' : 'Đầy đủ'}
                </strong>
              </span>
            </div>
          )}
        </div>

        {/* Result Panel */}
        <div>
          {loading && (
            <div className="flex flex-col items-center justify-center h-64 text-gray-400">
              <Loader2 className="h-10 w-10 animate-spin mb-3 text-primary-500" />
              <p className="text-sm">Đang phân tích...</p>
            </div>
          )}

          {error && !loading && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-4 flex gap-3">
              <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-red-700 dark:text-red-400">Lỗi</p>
                <p className="text-sm text-red-600 dark:text-red-300 mt-1">{error}</p>
              </div>
            </div>
          )}

          {!loading && !error && !result && (
            <div className="flex flex-col items-center justify-center h-64 text-gray-300 dark:text-gray-600">
              <Sparkles className="h-12 w-12 mb-3" />
              <p className="text-sm">Nhấn một trong 3 nút để bắt đầu phân tích</p>
            </div>
          )}

          {!loading && result && <ResultCard result={result} mode={activeMode} />}
        </div>
      </div>
    </div>
  )
}
