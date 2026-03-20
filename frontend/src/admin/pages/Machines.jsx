import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getMachines, deleteMachine, deleteBySite, getSiteConfigs } from '../api/adminClient'
import AdminLayout from '../components/AdminLayout'
import ConfirmModal from '../components/ConfirmModal'
import { useToast } from '../components/Toast'

const PAGE_SIZE = 50

export default function Machines() {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [brandFilter, setBrandFilter] = useState('')
  const [selectedIds, setSelectedIds] = useState([])
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [bulkDeleteSite, setBulkDeleteSite] = useState(null)
  const [showBulkConfirm, setShowBulkConfirm] = useState(false)

  const qc = useQueryClient()
  const toast = useToast()

  useEffect(() => {
    const t = setTimeout(() => { setDebouncedSearch(search); setPage(1) }, 400)
    return () => clearTimeout(t)
  }, [search])

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['machines', page, debouncedSearch, typeFilter, brandFilter],
    queryFn: () => getMachines({
      page,
      limit: PAGE_SIZE,
      search: debouncedSearch || undefined,
      site_name: typeFilter || undefined,
      brand: brandFilter || undefined,
    }),
  })

  const { data: configsData } = useQuery({
    queryKey: ['configs'],
    queryFn: getSiteConfigs,
  })

  const delOne = useMutation({
    mutationFn: deleteMachine,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['machines'] }); toast('Machine deleted', 'success') },
    onError: e => toast(e.response?.data?.detail || 'Delete failed', 'error'),
  })

  const delBySite = useMutation({
    mutationFn: deleteBySite,
    onSuccess: d => { qc.invalidateQueries({ queryKey: ['machines'] }); toast(`Deleted ${d.deleted} machines`, 'success') },
    onError: e => toast(e.response?.data?.detail || 'Bulk delete failed', 'error'),
  })

  const machines = data?.machines || []
  const total = data?.total || 0
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const sites = configsData?.configs?.map(c => c.name) || []
  const brands = [...new Set(machines.map(m => m.brand).filter(Boolean))].sort()

  const allSelected = machines.length > 0 && machines.every(m => selectedIds.includes(m.id))
  const toggleAll = () => setSelectedIds(allSelected ? [] : machines.map(m => m.id))
  const toggleOne = (id) => setSelectedIds(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id])

  const formatPrice = (m) => {
    if (!m.price) return '—'
    return `${m.currency || ''} ${Number(m.price).toLocaleString()}`.trim()
  }

  const handleClear = () => {
    setSearch(''); setTypeFilter(''); setBrandFilter(''); setStatusFilter(''); setPage(1); setSelectedIds([])
  }

  // Page number buttons (show up to 7 around current)
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
        {/* Header row */}
        <div className="flex flex-wrap items-center gap-2 justify-between">
          <h1 className="text-lg font-bold text-gray-900">Machines ({total.toLocaleString()})</h1>
          <div className="flex items-center gap-2 flex-wrap">
            {/* Show per page */}
            <div className="flex items-center gap-1 text-sm text-gray-600">
              <span>Show:</span>
              <span className="font-medium">{PAGE_SIZE}</span>
            </div>
            {/* Page info */}
            <span className="text-sm text-gray-500">Page {page} of {totalPages}</span>
            {/* Prev/Next */}
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1}
              className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-40 transition-colors">
              ← Prev
            </button>
            <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page >= totalPages}
              className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-40 transition-colors">
              Next →
            </button>
            {/* Action buttons */}
            <button className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors text-gray-700">
              Columns
            </button>
            <button className="px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors">
              + Add Machine
            </button>
            <button className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors text-gray-700">
              Fill Types
            </button>
            <button className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors text-gray-700">
              Export
            </button>
            <button onClick={handleClear}
              className="px-3 py-1.5 text-sm border border-red-200 text-red-600 rounded-lg hover:bg-red-50 transition-colors">
              Clear
            </button>
          </div>
        </div>

        {/* Filter row */}
        <div className="flex flex-wrap items-center gap-2">
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search SKU / model…"
            className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 w-52"
          />
          <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
            className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400">
            <option value="">All Status</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
          <select value={typeFilter} onChange={e => { setTypeFilter(e.target.value); setPage(1) }}
            className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400">
            <option value="">All Types</option>
            {sites.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          <select value={brandFilter} onChange={e => { setBrandFilter(e.target.value); setPage(1) }}
            className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400">
            <option value="">All Brands</option>
            {brands.map(b => <option key={b} value={b}>{b}</option>)}
          </select>
          <button onClick={() => refetch()}
            className="px-3 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors text-gray-600 text-sm">
            ↻ Refresh
          </button>
          {selectedIds.length > 0 && (
            <button onClick={() => setShowBulkConfirm(true)}
              className="px-3 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm transition-colors">
              Delete {selectedIds.length} selected
            </button>
          )}
        </div>

        {/* Table */}
        {isLoading ? (
          <div className="flex justify-center py-16">
            <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <div className="bg-white rounded-xl shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-200">
                    <th className="px-3 py-3 w-8">
                      <input type="checkbox" checked={allSelected} onChange={toggleAll}
                        className="rounded border-gray-300" />
                    </th>
                    <th className="text-left px-3 py-3 font-semibold text-gray-600 text-xs uppercase tracking-wide">Image</th>
                    <th className="text-left px-3 py-3 font-semibold text-gray-600 text-xs uppercase tracking-wide">Model</th>
                    <th className="text-left px-3 py-3 font-semibold text-gray-600 text-xs uppercase tracking-wide">Type</th>
                    <th className="text-left px-3 py-3 font-semibold text-gray-600 text-xs uppercase tracking-wide">Brand</th>
                    <th className="text-left px-3 py-3 font-semibold text-gray-600 text-xs uppercase tracking-wide">Location</th>
                    <th className="text-left px-3 py-3 font-semibold text-gray-600 text-xs uppercase tracking-wide">Price</th>
                    <th className="text-left px-3 py-3 font-semibold text-gray-600 text-xs uppercase tracking-wide">Premium</th>
                    <th className="text-left px-3 py-3 font-semibold text-gray-600 text-xs uppercase tracking-wide">Status</th>
                    <th className="text-left px-3 py-3 font-semibold text-gray-600 text-xs uppercase tracking-wide">E-URL</th>
                    <th className="text-left px-3 py-3 font-semibold text-gray-600 text-xs uppercase tracking-wide">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {machines.map(m => (
                    <tr key={m.id} className={`hover:bg-gray-50 transition-colors ${selectedIds.includes(m.id) ? 'bg-blue-50' : ''}`}>
                      <td className="px-3 py-2">
                        <input type="checkbox" checked={selectedIds.includes(m.id)} onChange={() => toggleOne(m.id)}
                          className="rounded border-gray-300" />
                      </td>
                      <td className="px-3 py-2">
                        {m.image_url ? (
                          <img src={m.image_url} alt="" className="w-10 h-10 object-cover rounded border bg-gray-100"
                            onError={e => { e.target.style.display = 'none' }} />
                        ) : (
                          <div className="w-10 h-10 rounded border bg-gray-100 flex items-center justify-center text-gray-300 text-xs">—</div>
                        )}
                      </td>
                      <td className="px-3 py-2 max-w-[200px]">
                        <p className="text-gray-800 truncate text-xs font-medium" title={m.name}>{m.name}</p>
                        <p className="text-gray-400 text-xs">#{m.id}</p>
                      </td>
                      <td className="px-3 py-2 text-xs text-gray-600">{m.site_name || '—'}</td>
                      <td className="px-3 py-2 text-xs text-gray-600">{m.brand || '—'}</td>
                      <td className="px-3 py-2 text-xs text-gray-600">{m.location || '—'}</td>
                      <td className="px-3 py-2 text-xs text-gray-800 whitespace-nowrap font-medium">{formatPrice(m)}</td>
                      <td className="px-3 py-2">
                        <span className="text-xs text-gray-400">No</span>
                      </td>
                      <td className="px-3 py-2">
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">
                          Active
                        </span>
                      </td>
                      <td className="px-3 py-2">
                        {m.source_url ? (
                          <a href={m.source_url} target="_blank" rel="noreferrer"
                            className="inline-flex items-center justify-center w-7 h-7 rounded-lg border border-gray-200 text-blue-500 hover:bg-blue-50 transition-colors"
                            title="View source">
                            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                            </svg>
                          </a>
                        ) : (
                          <span className="text-gray-300 text-xs">—</span>
                        )}
                      </td>
                      <td className="px-3 py-2">
                        <button onClick={() => setDeleteTarget(m.id)}
                          className="inline-flex items-center justify-center w-7 h-7 rounded-lg border border-red-200 text-red-500 hover:bg-red-50 transition-colors"
                          title="Delete">
                          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </td>
                    </tr>
                  ))}
                  {machines.length === 0 && (
                    <tr>
                      <td colSpan={11} className="text-center py-12 text-gray-400">No machines found</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Bottom pagination */}
            <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100">
              <p className="text-sm text-gray-500">
                {((page - 1) * PAGE_SIZE) + 1}–{Math.min(page * PAGE_SIZE, total)} of {total.toLocaleString()} machines
              </p>
              <div className="flex items-center gap-1">
                <button onClick={() => setPage(1)} disabled={page <= 1}
                  className="px-2 py-1.5 border border-gray-200 rounded-lg text-xs text-gray-600 hover:bg-gray-50 disabled:opacity-40 transition-colors">«</button>
                <button onClick={() => setPage(p => p - 1)} disabled={page <= 1}
                  className="px-3 py-1.5 border border-gray-200 rounded-lg text-xs text-gray-600 hover:bg-gray-50 disabled:opacity-40 transition-colors">‹ Prev</button>
                {pageButtons().map(pg => (
                  <button key={pg} onClick={() => setPage(pg)}
                    className={`px-3 py-1.5 border rounded-lg text-xs transition-colors ${pg === page ? 'bg-blue-600 text-white border-blue-600' : 'border-gray-200 text-gray-600 hover:bg-gray-50'}`}>
                    {pg}
                  </button>
                ))}
                <button onClick={() => setPage(p => p + 1)} disabled={page >= totalPages}
                  className="px-3 py-1.5 border border-gray-200 rounded-lg text-xs text-gray-600 hover:bg-gray-50 disabled:opacity-40 transition-colors">Next ›</button>
                <button onClick={() => setPage(totalPages)} disabled={page >= totalPages}
                  className="px-2 py-1.5 border border-gray-200 rounded-lg text-xs text-gray-600 hover:bg-gray-50 disabled:opacity-40 transition-colors">»</button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Single delete confirm */}
      <ConfirmModal
        isOpen={!!deleteTarget}
        title="Delete Machine"
        message="Are you sure you want to permanently delete this machine from the database?"
        onConfirm={() => { delOne.mutate(deleteTarget); setDeleteTarget(null) }}
        onCancel={() => setDeleteTarget(null)}
      />

      {/* Bulk delete confirm */}
      <ConfirmModal
        isOpen={showBulkConfirm}
        title="Delete Selected Machines"
        message={`Permanently delete ${selectedIds.length} selected machine(s) from the database? This cannot be undone.`}
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
