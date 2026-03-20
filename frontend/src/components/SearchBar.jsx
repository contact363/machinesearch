import { useState, useEffect, useRef, useCallback } from 'react'
import { useSuggestions } from '../hooks/useSearch'

function useDebounce(value, delay) {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(t)
  }, [value, delay])
  return debounced
}

export default function SearchBar({ size = 'large', initialValue = '', onSubmit }) {
  const [value, setValue] = useState(initialValue)
  const [open, setOpen] = useState(false)
  const [highlighted, setHighlighted] = useState(-1)
  const inputRef = useRef(null)
  const containerRef = useRef(null)

  const debouncedQ = useDebounce(value, 300)
  const { data: suggestions = [], isFetching } = useSuggestions(debouncedQ)

  // Close on outside click
  useEffect(() => {
    const handler = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  // Sync initialValue if it changes (e.g. URL changes)
  useEffect(() => { setValue(initialValue) }, [initialValue])

  const handleChange = (e) => {
    setValue(e.target.value)
    setHighlighted(-1)
    setOpen(true)
  }

  const submit = useCallback((q) => {
    const term = (q ?? value).trim()
    setOpen(false)
    onSubmit(term)
  }, [value, onSubmit])

  const handleKeyDown = (e) => {
    if (!open || suggestions.length === 0) {
      if (e.key === 'Enter') submit()
      return
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setHighlighted(h => Math.min(h + 1, suggestions.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setHighlighted(h => Math.max(h - 1, -1))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      if (highlighted >= 0 && suggestions[highlighted]) {
        const s = suggestions[highlighted]
        setValue(s.name || s)
        submit(s.name || s)
      } else {
        submit()
      }
    } else if (e.key === 'Escape') {
      setOpen(false)
    }
  }

  const isLarge = size === 'large'
  const showDropdown = open && debouncedQ.length >= 2 && (suggestions.length > 0 || isFetching)

  return (
    <div ref={containerRef} className="relative w-full">
      <div className={`flex items-center bg-white rounded-xl shadow-sm border border-gray-200 ${isLarge ? 'h-14' : 'h-10'}`}>
        {/* Search icon */}
        <div className={`flex-shrink-0 text-gray-400 ${isLarge ? 'pl-4 pr-3' : 'pl-3 pr-2'}`}>
          <svg className={isLarge ? 'w-5 h-5' : 'w-4 h-4'} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>

        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          onFocus={() => value.length >= 2 && setOpen(true)}
          placeholder={isLarge ? 'Search excavators, lathes, CNC machines...' : 'Search machines...'}
          className={`flex-1 bg-transparent text-gray-900 placeholder-gray-400 outline-none ${isLarge ? 'text-base' : 'text-sm'}`}
        />

        {/* Clear button */}
        {value && (
          <button
            onClick={() => { setValue(''); inputRef.current?.focus() }}
            className="flex-shrink-0 text-gray-400 hover:text-gray-600 px-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}

        {/* Loading spinner */}
        {isFetching && debouncedQ.length >= 2 && (
          <div className="flex-shrink-0 px-2">
            <div className="w-4 h-4 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin" />
          </div>
        )}

        {/* Search button */}
        <button
          onClick={() => submit()}
          className={`flex-shrink-0 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-r-xl transition-colors ${isLarge ? 'px-6 h-14 text-base' : 'px-4 h-10 text-sm'}`}
        >
          Search
        </button>
      </div>

      {/* Suggestions dropdown */}
      {showDropdown && (
        <div className="absolute z-50 left-0 right-0 mt-1 bg-white rounded-xl shadow-lg border border-gray-100 overflow-hidden">
          {isFetching && suggestions.length === 0 ? (
            <div className="px-4 py-3 text-sm text-gray-500">Loading suggestions...</div>
          ) : (
            suggestions.slice(0, 8).map((s, i) => {
              const label = typeof s === 'string' ? s : s.name || s.text || JSON.stringify(s)
              return (
                <button
                  key={i}
                  onMouseDown={(e) => {
                    e.preventDefault()
                    setValue(label)
                    submit(label)
                  }}
                  onMouseEnter={() => setHighlighted(i)}
                  className={`w-full text-left px-4 py-2.5 text-sm flex items-center gap-3 transition-colors ${
                    highlighted === i ? 'bg-blue-50 text-blue-700' : 'text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  <svg className="w-4 h-4 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                  {label}
                </button>
              )
            })
          )}
        </div>
      )}
    </div>
  )
}
