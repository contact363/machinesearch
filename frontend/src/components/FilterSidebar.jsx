import { useState } from 'react'
import { getSiteName } from '../utils/format'

function Section({ title, defaultOpen = true, children }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="border-b border-gray-100 last:border-0">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between py-3 px-4 text-sm font-semibold text-gray-700 hover:text-gray-900"
      >
        {title}
        <svg
          className={`w-4 h-4 transition-transform text-gray-400 ${open ? 'rotate-180' : ''}`}
          fill="none" stroke="currentColor" viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {open && <div className="px-4 pb-4">{children}</div>}
    </div>
  )
}

function CheckGroup({ items, selected, onChange, labelFn, countFn, maxShown = 10 }) {
  const [showAll, setShowAll] = useState(false)
  const visible = showAll ? items : items.slice(0, maxShown)

  return (
    <div className="space-y-2">
      {visible.map(item => {
        const val = typeof item === 'string' ? item : item.value || item.brand || item.site || item.location
        const label = labelFn ? labelFn(item) : val
        const count = countFn ? countFn(item) : null
        const checked = selected.includes(val)
        return (
          <label key={val} className="flex items-center gap-2 cursor-pointer group">
            <input
              type="checkbox"
              checked={checked}
              onChange={() => onChange(val)}
              className="w-4 h-4 text-blue-600 rounded border-gray-300 cursor-pointer"
            />
            <span className="text-sm text-gray-700 group-hover:text-gray-900 flex-1 truncate">{label}</span>
            {count != null && <span className="text-xs text-gray-400 flex-shrink-0">{count}</span>}
          </label>
        )
      })}
      {items.length > maxShown && (
        <button
          onClick={() => setShowAll(s => !s)}
          className="text-xs text-blue-600 hover:text-blue-800 font-medium mt-1"
        >
          {showAll ? 'Show less' : `Show ${items.length - maxShown} more`}
        </button>
      )}
    </div>
  )
}

export default function FilterSidebar({ filters, params, onChange, onClear }) {
  const { sites = [], brands = [] } = filters || {}

  const selectedBrands = params.brand ? params.brand.split(',').filter(Boolean) : []
  const selectedSites = params.site_name ? params.site_name.split(',').filter(Boolean) : []

  const toggleMulti = (key, current, val) => {
    const arr = current.includes(val)
      ? current.filter(v => v !== val)
      : [...current, val]
    onChange({ [key]: arr.join(',') || undefined })
  }

  const hasFilters = params.brand || params.site_name || params.min_price || params.max_price

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
        <h2 className="text-sm font-bold text-gray-900">Filters</h2>
        {hasFilters && (
          <button onClick={onClear} className="text-xs text-blue-600 hover:text-blue-800 font-medium">
            Clear all
          </button>
        )}
      </div>

      {/* Sort */}
      <Section title="Sort By">
        <select
          value={params.sort_by || 'relevance'}
          onChange={e => onChange({ sort_by: e.target.value || undefined })}
          className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="relevance">Relevance</option>
          <option value="price_asc">Price: Low to High</option>
          <option value="price_desc">Price: High to Low</option>
          <option value="newest">Newest First</option>
        </select>
      </Section>

      {/* Price Range */}
      <Section title="Price Range">
        <div className="flex gap-2 items-center">
          <input
            type="number"
            placeholder="Min €"
            value={params.min_price || ''}
            onChange={e => onChange({ min_price: e.target.value || undefined })}
            className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <span className="text-gray-400 flex-shrink-0">–</span>
          <input
            type="number"
            placeholder="Max €"
            value={params.max_price || ''}
            onChange={e => onChange({ max_price: e.target.value || undefined })}
            className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </Section>

      {/* Brands */}
      {brands.length > 0 && (
        <Section title="Brand">
          <CheckGroup
            items={brands.slice(0, 50).map(b => ({ brand: b.brand, count: b.count }))}
            selected={selectedBrands}
            onChange={val => toggleMulti('brand', selectedBrands, val)}
            labelFn={b => b.brand}
            countFn={b => b.count}
            maxShown={10}
          />
        </Section>
      )}

      {/* Sites */}
      {sites.length > 0 && (
        <Section title="Source Site">
          <CheckGroup
            items={sites.map(s => ({ site: s.site, count: s.count }))}
            selected={selectedSites}
            onChange={val => toggleMulti('site_name', selectedSites, val)}
            labelFn={s => getSiteName(s.site)}
            countFn={s => s.count}
            maxShown={10}
          />
        </Section>
      )}
    </div>
  )
}
