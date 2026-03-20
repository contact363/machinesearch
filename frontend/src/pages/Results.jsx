import { useState, useEffect, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useSearchResults, useFilters } from '../hooks/useSearch'
import Navbar from '../components/Navbar'
import MachineCard from '../components/MachineCard'
import SkeletonCard from '../components/SkeletonCard'
import FilterSidebar from '../components/FilterSidebar'
import Pagination from '../components/Pagination'

const LIMIT = 24

function paramsToObj(sp) {
  const obj = {}
  for (const [k, v] of sp.entries()) if (v) obj[k] = v
  return obj
}

export default function Results() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [drawerOpen, setDrawerOpen] = useState(false)

  const params = paramsToObj(searchParams)
  const page = parseInt(params.page || '1', 10)

  const queryParams = {
    q: params.q || undefined,
    brand: params.brand || undefined,
    min_price: params.min_price || undefined,
    max_price: params.max_price || undefined,
    site_name: params.site_name || undefined,
    sort_by: params.sort_by || undefined,
    page,
    limit: LIMIT,
  }

  const { data, isLoading, isError, refetch } = useSearchResults(queryParams)
  const { data: filters } = useFilters()

  const total = data?.total || 0
  const machines = data?.results || []
  const totalPages = Math.ceil(total / LIMIT)

  const updateParams = useCallback((changes) => {
    setSearchParams(prev => {
      const next = new URLSearchParams(prev)
      for (const [k, v] of Object.entries(changes)) {
        if (v === undefined || v === '' || v === null) next.delete(k)
        else next.set(k, String(v))
      }
      // Reset to page 1 on filter change (unless page is the change)
      if (!('page' in changes)) next.delete('page')
      return next
    })
  }, [setSearchParams])

  const clearFilters = useCallback(() => {
    setSearchParams(prev => {
      const next = new URLSearchParams()
      if (prev.get('q')) next.set('q', prev.get('q'))
      return next
    })
  }, [setSearchParams])

  const handlePageChange = (p) => {
    updateParams({ page: p === 1 ? undefined : p })
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const hasFilters = params.brand || params.site_name || params.min_price || params.max_price

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar showSearch />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
        {/* Mobile filter toggle */}
        <div className="md:hidden mb-4">
          <button
            onClick={() => setDrawerOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-white rounded-xl border border-gray-200 shadow-sm text-sm font-medium text-gray-700"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2a1 1 0 01-.293.707L13 13.414V19a1 1 0 01-.553.894l-4 2A1 1 0 017 21v-7.586L3.293 6.707A1 1 0 013 6V4z" />
            </svg>
            Filters {hasFilters && <span className="bg-blue-600 text-white rounded-full text-xs px-1.5 py-0.5">!</span>}
          </button>
        </div>

        <div className="flex gap-6">
          {/* Sidebar — desktop */}
          <aside className="hidden md:block w-64 flex-shrink-0">
            <FilterSidebar
              filters={filters}
              params={params}
              onChange={updateParams}
              onClear={clearFilters}
            />
          </aside>

          {/* Mobile drawer */}
          {drawerOpen && (
            <div className="md:hidden fixed inset-0 z-50 flex">
              <div className="w-72 bg-white shadow-xl overflow-y-auto">
                <div className="flex items-center justify-between px-4 py-3 border-b">
                  <h2 className="font-semibold text-gray-900">Filters</h2>
                  <button onClick={() => setDrawerOpen(false)} className="text-gray-500 hover:text-gray-700">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
                <FilterSidebar
                  filters={filters}
                  params={params}
                  onChange={(c) => { updateParams(c); setDrawerOpen(false) }}
                  onClear={() => { clearFilters(); setDrawerOpen(false) }}
                />
              </div>
              <div className="flex-1 bg-black/40" onClick={() => setDrawerOpen(false)} />
            </div>
          )}

          {/* Main content */}
          <div className="flex-1 min-w-0">
            {/* Result count */}
            <div className="mb-4">
              {isLoading ? (
                <div className="h-5 w-48 bg-gray-200 rounded animate-pulse" />
              ) : isError ? null : (
                <p className="text-sm text-gray-600">
                  {params.q
                    ? <><span className="font-semibold">{total.toLocaleString()} results</span> for "{params.q}"</>
                    : <><span className="font-semibold">{total.toLocaleString()} machines</span> found</>
                  }
                </p>
              )}
            </div>

            {/* Grid */}
            {isError ? (
              <div className="text-center py-20">
                <p className="text-gray-500 mb-4">Failed to load results.</p>
                <button onClick={() => refetch()} className="px-6 py-2 bg-blue-600 text-white rounded-xl text-sm font-medium hover:bg-blue-700">
                  Retry
                </button>
              </div>
            ) : isLoading ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {Array.from({ length: LIMIT }).map((_, i) => <SkeletonCard key={i} />)}
              </div>
            ) : machines.length === 0 ? (
              <div className="text-center py-20">
                <div className="text-5xl mb-4">🔍</div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">No machines found</h3>
                <p className="text-gray-500 mb-6">Try different keywords or remove some filters.</p>
                {hasFilters && (
                  <button onClick={clearFilters} className="px-6 py-2 bg-blue-600 text-white rounded-xl text-sm font-medium hover:bg-blue-700">
                    Clear Filters
                  </button>
                )}
              </div>
            ) : (
              <>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {machines.map(m => <MachineCard key={m.id} machine={m} />)}
                </div>
                <Pagination currentPage={page} totalPages={totalPages} onPageChange={handlePageChange} />
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
