import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getMachines, deleteMachine, deleteBySite,
  getSiteConfigs, toggleFeatured,
} from '../api/adminClient'
import AdminLayout from '../components/AdminLayout'
import ConfirmModal from '../components/ConfirmModal'
import { useToast } from '../components/Toast'

const PAGE_SIZE = 50

function MachineImage({ url, name }) {
  const [err, setErr] = useState(false)
  const initial = (name || '?')[0].toUpperCase()
  if (!url || err) {
    return (
      <div className="w-9 h-9 rounded-lg bg-gray-100 border border-gray-200 flex items-center justify-center text-gray-400 text-xs font-bold flex-shrink-0">
        {initial}
      </div>
    )
  }
  return (
    <img
      src={url} alt=""
      className="w-9 h-9 object-cover rounded-lg border border-gray-200 flex-shrink-0"
      onError={() => setErr(true)}
    />
  )
}

function StarButton({ active, onClick, loading }) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      title={active ? 'Remove featured' : 'Mark as featured'}
      className={`w-7 h-7 flex items-center justify-center rounded-lg transition-all ${
        active
          ? 'text-amber-500 bg-amber-50 border border-amber-200 hover:bg-amber-100'
          : 'text-gray-300 border border-gray-200 hover:text-amber-400 hover:border-amber-200 hover:bg-amber-50'
      } ${loading ? 'opacity-50 cursor-wait' : ''}`}
    >
      <svg className="w-3.5 h-3.5" fill={active ? 'currentColor' : 'none'} stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
      </svg>
    </button>
  )
}

export default function Machines() {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [siteFilter, setSiteFilter] = useState('')
  const [brandFilter, setBrandFilter] = useState('')
  const [selectedIds, setSelectedIds] = useState([])
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [showBulkConfirm, setShowBulkConfirm] = useState(false)
  const [togglingId, setTogglingId] = useState(null)

  const qc = useQueryClient()
  const toast = useToast()

  useEffect(() => {
    const t = setTimeout(() => { setDebouncedSearch(search); setPage(1) }, 400)
    return () => clearTimeout(t)
  }, [search])

  const { data, isLoading, isFetching, refetch } = useQuery({
    queryKey: ['machines', page, debouncedSearch, siteFilter, brandFilter],
    queryFn: () => getMachines({
      page,
      limit: PAGE_SIZE,
      search: debouncedSearch || undefined,
      site_name: siteFilter || undefined,
      brand: brandFilter || undefined,
    }),
    staleTime: 0,
  })

  const { data: configsData } = useQuery({
    queryKey: ['configs'],
    queryFn: getSiteConfigs,
  })

  const delOne = useMutation({
    mutationFn: deleteMachine,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['machines'] })
      toast('Machine deleted', 'success')
    },
    onError: e => toast(e.response?.data?.detail || 'Delete failed', 'error'),
  })

  const delBySite = useMutation({
    mutationFn: deleteBySite,
    onSuccess: d => {
      qc.invalidateQueries({ queryKey: ['machines'] })
      toast(`Deleted ${d.deleted} machines`, 'success')
    },
    onError: e => toast(e.response?.data?.detail || 'Bulk delete failed', 'error'),
  })

  const machines = data?.machines || []
  const total = data?.total || 0
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const sites = configsData?.configs?.map(c => c.name) || []
  const brands = [...new Set(machines.map(m => m.brand).filter(Boolean))].sort()

  const allSelected = machines.length > 0 && machines.every(m => selectedIds.includes(m.id))
  const toggleAll = () => setSelectedIds(allSelected ? [] : machines.map(m => m.id))
  const toggleOne = id => setSelectedIds(prev =>
    prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
  )

  const handleToggleFeatured = async (id, current) => {
    setTogglingId(id)
    try {
      const res = await toggleFeatured(id)
      qc.setQueryData(['machines', page, debouncedSearch, siteFilter, brandFilter], old => {
        if (!old) return old
        return {
          ...old,
          machines: old.machines.map(m =>
            m.id === id ? { ...m, is_featured: res.is_featured } : m
          ),
        }
      })
      toast(res.is_featured ? 'Marked as featured' : 'Removed from featured', 'success')
    } catch {
      toast('Failed to update featured status', 'error')
    } finally {
      setTogglingId(null)
    }
  }

  const formatPrice = m => {
    if (!m.price) return '—'
    const sym = m.currency === 'USD' ? '$' : m.currency === 'EUR' ? '€' : (m.currency || '')
    return `${sym}${Number(m.price).toLocaleString()}`
  }

  const handleClear = () => {
    setSearch(''); setSiteFilter(''); setBrandFilter(''); setPage(1); setSelectedIds([])
  }

  const pageButtons = () => {
    const pages = []
    const start = Math.max(1, Math.min(page - 3, totalPages - 6))
    const end = Math.min(totalPages, start + 6)
    for (let i = start; i <= end; i++) pages.push(i)
    return pages
  }

  return (
    <AdminLayout>
      <div className="space-y-4">

        {/* Toolbar */}
        <div className="bg-white rounded-xl border border-gray-200 px-4 py-3">
          <div className="flex flex-wrap items-center gap-2">
            {/* Search */}
            <div className="relative">
              <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <input
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Search machines..."
                className="pl-8 pr-3 py-2 text-xs border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent w-48"
              />
            </div>

            {/* Site filter */}
            <select
              value={siteFilter}
              onChange={e => { setSiteFilter(e.target.value); setPage(1) }}
              className="text-xs border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-600"
            >
              <option value="">All Sites</option>
              {sites.map(s => <option key={s} value={s}>{s}</option>)}
            </select>

            {/* Brand filter */}
            <select
              value={brandFilter}
              onChange={e => { setBrandFilter(e.target.value); setPage(1) }}
              className="text-xs border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-600"
            >
              <option value="">All Brands</option>
              {brands.map(b => <option key={b} value={b}>{b}</option>)}
            </select>

            {/* Clear filters */}
            {(search || siteFilter || brandFilter) && (
              <button onClick={handleClear} className="text-xs text-gray-500 hover:text-gray-700 px-2 py-2">
                Clear filters
              </button>
            )}

            <div className="flex-1" />

            {/* Count + pagination info */}
            <span className="text-xs text-gray-500 tabular-nums">
              {total.toLocaleString()} machines · page {page}/{totalPages}
            </span>

            {/* Refresh */}
            <button
              onClick={() => refetch()}
              disabled={isFetching}
              className="flex items-center gap-1.5 px-3 py-2 text-xs border border-gray-200 rounded-lg hover:bg-gray-50 text-gray-600 transition-colors disabled:opacity-60"
            >
              <svg className={`w-3.5 h-3.5 ${isFetching ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              {isFetching ? 'Refreshing...' : 'Refresh'}
            </button>

            {/* Bulk delete */}
            {selectedIds.length > 0 && (
              <button
                onClick={() => setShowBulkConfirm(true)}
                className="flex items-center gap-1.5 px-3 py-2 text-xs bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
                Delete {selectedIds.length}
              </button>
            )}
          </div>
        </div>

        {/* Table */}
        {isLoading ? (
          <div className="flex justify-center py-20">
            <div className="w-7 h-7 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-gray-100 bg-gray-50/60">
                    <th className="w-8 px-3 py-3">
                      <input type="checkbox" checked={allSelected} onChange={toggleAll}
                        className="rounded border-gray-300 accent-blue-600" />
                    </th>
                    <th className="text-left px-3 py-3 font-semibold text-gray-500 uppercase tracking-wider text-[10px]"></th>
                    <th className="text-left px-3 py-3 font-semibold text-gray-500 uppercase tracking-wider text-[10px]">Machine</th>
                    <th className="text-left px-3 py-3 font-semibold text-gray-500 uppercase tracking-wider text-[10px]">Site</th>
                    <th className="text-left px-3 py-3 font-semibold text-gray-500 uppercase tracking-wider text-[10px]">Brand</th>
                    <th className="text-left px-3 py-3 font-semibold text-gray-500 uppercase tracking-wider text-[10px]">Location</th>
                    <th className="text-left px-3 py-3 font-semibold text-gray-500 uppercase tracking-wider text-[10px]">Price</th>
                    <th className="text-center px-3 py-3 font-semibold text-gray-500 uppercase tracking-wider text-[10px]">Featured</th>
                    <th className="text-center px-3 py-3 font-semibold text-gray-500 uppercase tracking-wider text-[10px]">Link</th>
                    <th className="text-center px-3 py-3 font-semibold text-gray-500 uppercase tracking-wider text-[10px]"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {machines.map(m => (
                    <tr key={m.id} className={`hover:bg-gray-50/80 transition-colors ${selectedIds.includes(m.id) ? 'bg-blue-50/60' : ''}`}>
                      <td className="px-3 py-2.5">
                        <input type="checkbox" checked={selectedIds.includes(m.id)} onChange={() => toggleOne(m.id)}
                          className="rounded border-gray-300 accent-blue-600" />
                      </td>
                      <td className="px-3 py-2.5">
                        <MachineImage url={m.image_url} name={m.name} />
                      </td>
                      <td className="px-3 py-2.5 max-w-[200px]">
                        <p className="font-medium text-gray-800 truncate" title={m.name}>{m.name}</p>
                        <p className="text-gray-400 text-[10px] mt-0.5 font-mono truncate">{m.id.slice(0, 8)}…</p>
                      </td>
                      <td className="px-3 py-2.5">
                        <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-gray-100 text-gray-600 font-medium text-[10px]">
                          {m.site_name || '—'}
                        </span>
                      </td>
                      <td className="px-3 py-2.5 text-gray-600">{m.brand || '—'}</td>
                      <td className="px-3 py-2.5 text-gray-500 max-w-[120px] truncate">{m.location || '—'}</td>
                      <td className="px-3 py-2.5 font-semibold text-gray-800 whitespace-nowrap">{formatPrice(m)}</td>
                      <td className="px-3 py-2.5 text-center">
                        <div className="flex justify-center">
                          <StarButton
                            active={m.is_featured}
                            loading={togglingId === m.id}
                            onClick={() => handleToggleFeatured(m.id, m.is_featured)}
                          />
                        </div>
                      </td>
                      <td className="px-3 py-2.5 text-center">
                        {m.source_url ? (
                          <a
                            href={m.source_url} target="_blank" rel="noreferrer"
                            className="inline-flex items-center justify-center w-7 h-7 rounded-lg border border-gray-200 text-blue-500 hover:bg-blue-50 hover:border-blue-200 transition-colors"
                            title="View source"
                          >
                            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                            </svg>
                          </a>
                        ) : <span className="text-gray-300">—</span>}
                      </td>
                      <td className="px-3 py-2.5 text-center">
                        <button
                          onClick={() => setDeleteTarget(m.id)}
                          className="inline-flex items-center justify-center w-7 h-7 rounded-lg border border-gray-200 text-gray-400 hover:text-red-500 hover:border-red-200 hover:bg-red-50 transition-colors"
                          title="Delete"
                        >
                          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </td>
                    </tr>
                  ))}
                  {machines.length === 0 && (
                    <tr>
                      <td colSpan={10} className="text-center py-16 text-gray-400">
                        <svg className="w-8 h-8 mx-auto mb-2 text-gray-200" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        No machines found
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100">
              <p className="text-xs text-gray-500 tabular-nums">
                {total === 0 ? '0' : `${((page - 1) * PAGE_SIZE) + 1}–${Math.min(page * PAGE_SIZE, total)}`} of {total.toLocaleString()}
              </p>
              <div className="flex items-center gap-1">
                <button onClick={() => setPage(1)} disabled={page <= 1}
                  className="px-2 py-1.5 border border-gray-200 rounded-lg text-xs text-gray-500 hover:bg-gray-50 disabled:opacity-30 transition-colors">«</button>
                <button onClick={() => setPage(p => p - 1)} disabled={page <= 1}
                  className="px-3 py-1.5 border border-gray-200 rounded-lg text-xs text-gray-500 hover:bg-gray-50 disabled:opacity-30 transition-colors">Prev</button>
                {pageButtons().map(pg => (
                  <button key={pg} onClick={() => setPage(pg)}
                    className={`px-3 py-1.5 border rounded-lg text-xs transition-colors ${
                      pg === page
                        ? 'bg-blue-600 text-white border-blue-600'
                        : 'border-gray-200 text-gray-500 hover:bg-gray-50'
                    }`}>
                    {pg}
                  </button>
                ))}
                <button onClick={() => setPage(p => p + 1)} disabled={page >= totalPages}
                  className="px-3 py-1.5 border border-gray-200 rounded-lg text-xs text-gray-500 hover:bg-gray-50 disabled:opacity-30 transition-colors">Next</button>
                <button onClick={() => setPage(totalPages)} disabled={page >= totalPages}
                  className="px-2 py-1.5 border border-gray-200 rounded-lg text-xs text-gray-500 hover:bg-gray-50 disabled:opacity-30 transition-colors">»</button>
              </div>
            </div>
          </div>
        )}
      </div>

      <ConfirmModal
        isOpen={!!deleteTarget}
        title="Delete Machine"
        message="Permanently delete this machine from the database?"
        onConfirm={() => { delOne.mutate(deleteTarget); setDeleteTarget(null) }}
        onCancel={() => setDeleteTarget(null)}
      />

      <ConfirmModal
        isOpen={showBulkConfirm}
        title="Delete Selected"
        message={`Permanently delete ${selectedIds.length} machine(s)? This cannot be undone.`}
        onConfirm={async () => {
          for (const id of selectedIds) await delOne.mutateAsync(id).catch(() => {})
          setSelectedIds([])
          setShowBulkConfirm(false)
          qc.invalidateQueries({ queryKey: ['machines'] })
        }}
        onCancel={() => setShowBulkConfirm(false)}
      />
    </AdminLayout>
  )
}
