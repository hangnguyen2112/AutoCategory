import { useState, useEffect } from 'react'
import { Search } from 'lucide-react'
import axios from 'axios'

/**
 * CategorySelect component - Dropdown with search for selecting category
 * Fetches categories from API and displays in tree-like format
 */
export default function CategorySelect({ value, onChange, required = false }) {
  const [categories, setCategories] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [isOpen, setIsOpen] = useState(false)

  useEffect(() => {
    fetchCategories()
  }, [])

  const fetchCategories = async () => {
    try {
      const response = await axios.get('/api/categories')
      setCategories(response.data.categories || [])
    } catch (error) {
      console.error('Failed to fetch categories:', error)
    } finally {
      setLoading(false)
    }
  }

  const filteredCategories = categories.filter((cat) =>
    cat.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (cat.path && cat.path.toLowerCase().includes(searchTerm.toLowerCase())) ||
    cat.category_id.toString().includes(searchTerm)
  )

  const selectedCategory = categories.find((c) => c.category_id === parseInt(value))

  return (
    <div className="relative">
      {/* Display selected or trigger dropdown */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="input w-full text-left flex items-center justify-between"
      >
        <span className="text-gray-900 dark:text-white">
          {selectedCategory ? (
            <>
              <span className="font-mono text-xs text-gray-500 dark:text-gray-400">
                ID {selectedCategory.category_id}
              </span>
              {' · '}
              <span>{selectedCategory.name}</span>
              {selectedCategory.path && (
                <span className="text-xs text-gray-500 dark:text-gray-400 ml-2">
                  ({selectedCategory.path})
                </span>
              )}
            </>
          ) : (
            <span className="text-gray-400">Select category...</span>
          )}
        </span>
        <svg
          className={`h-5 w-5 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Dropdown panel */}
      {isOpen && (
        <>
          {/* Backdrop */}
          <div className="fixed inset-0 z-10" onClick={() => setIsOpen(false)} />

          {/* Dropdown content */}
          <div className="absolute z-20 mt-1 w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg max-h-96 overflow-hidden">
            {/* Search */}
            <div className="p-2 border-b border-gray-200 dark:border-gray-700">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search by ID, name, or path..."
                  className="input w-full pl-9 text-sm"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  onClick={(e) => e.stopPropagation()}
                />
              </div>
            </div>

            {/* Category list */}
            <div className="overflow-y-auto max-h-80">
              {loading ? (
                <div className="p-4 text-center text-gray-500 dark:text-gray-400">Loading...</div>
              ) : filteredCategories.length === 0 ? (
                <div className="p-4 text-center text-gray-500 dark:text-gray-400">
                  No categories found
                </div>
              ) : (
                filteredCategories.map((cat) => (
                  <button
                    key={cat.category_id}
                    type="button"
                    onClick={() => {
                      onChange({ target: { value: cat.category_id.toString() } })
                      setIsOpen(false)
                      setSearchTerm('')
                    }}
                    className={`w-full text-left px-4 py-2 hover:bg-gray-100 dark:hover:bg-gray-700 ${
                      value && parseInt(value) === cat.category_id
                        ? 'bg-blue-50 dark:bg-blue-900/20'
                        : ''
                    }`}
                  >
                    <div className="flex items-start gap-2">
                      <span className="font-mono text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                        {cat.category_id}
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-gray-900 dark:text-white">
                          {cat.name}
                        </div>
                        {cat.path && (
                          <div className="text-xs text-gray-500 dark:text-gray-400 truncate">
                            {cat.path}
                          </div>
                        )}
                      </div>
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
