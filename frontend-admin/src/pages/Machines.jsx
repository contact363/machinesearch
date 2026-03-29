import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getMachines, deleteMachine, deleteBySite, getSiteConfigs } from '../api/adminClient'
import AdminLayout from '../components/AdminLayout'
import ConfirmModal from '../components/ConfirmModal'
import { useToast } from '../components/Toast'

export default function Machines() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [model, setModel] = useState('')
  const [debouncedModel, setDebouncedModel] = useState('')
  const [siteFilter, setSiteFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [brandFilter, setBrandFilter] = useState('')
  const [yearSort, setYearSort] = useState('')   // '' | 'asc' | 'desc'
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [bulkDeleteSite, setBulkDeleteSite] = useState(null)

  const qc = useQueryClient()
  const toast = useToast()

  // Debounce model text input
  useEffect(() => {
    const t = setTimeout(() => { setDebouncedModel(model); setPage(1) }, 400)
    return () => clearTimeout(t)
  }, [model])

  const { data, isLoading } = useQuery({
    queryKey: ['machines', page, debouncedModel, siteFilter, typeFilter, brandFilter, yearSort],
    queryFn: () => getMachines({
      page,
      limit: 25,
      model: debouncedModel || undefined,
      site_name: siteFilter || undefined,
      machine_type: typeFilter || undefined,
      brand: brandFilter || undefined,
      year_sort: yearSort || undefined,
    }),
  })

  const { data: configsData } = useQuery({
    queryKey: ['configs'],
    queryFn: getSiteConfigs,
  })

  const delMut = useMutation({
    mutationFn: deleteMachine,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['machines'] }); toast('Machine deleted', 'success') },
    onError: e => toast(e.response?.data?.detail || 'Delete failed', 'error'),
  })

  const bulkMut = useMutation({
    mutationFn: deleteBySite,
    onSuccess: d => { qc.invalidateQueries({ queryKey: ['machines'] }); toast(`Deleted ${d.deleted} machines`, 'success') },
    onError: e => toast(e.response?.data?.detail || 'Bulk delete failed', 'error'),
  })

  const machines        = data?.machines || []
  const total           = data?.total || 0
  const totalPages      = Math.ceil(total / 25)
  const sites           = configsData?.configs?.map(c => c.name) || []
  const availableBrands = data?.available_brands || []
  const availableTypes  = data?.available_types || []

  const clearFilters = () => {
    setModel(''); setDebouncedModel(''); setSiteFilter('')
    setTypeFilter(''); setBrandFilter(''); setYearSort(''); setPage(1)
  }

  const toggleYearSort = () => {
    setYearSort(prev => prev === 'asc' ? 'desc' : prev === 'desc' ? '' : 'asc')
    setPage(1)
  }

  const formatPrice = m => m.price ? `${m.currency || ''} ${m.price.toLocaleString()}` : '—'

  return (
    <AdminLayout>
      <div className="space-y-4">

        {/* ── Filter bar ── */}
        <div className="bg-white rounded-xl shadow-sm px-4 py-3 flex flex-wrap items-center gap-3">

          {/* Website (dropdown) */}
          <select
            value={siteFilter}
            onChange={e => { setSiteFilter(e.target.value); setBrandFilter(''); setTypeFilter(''); setPage(1) }}
            className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          >
            <option value="">All Websites</option>
            {sites.map(s => <option key={s} value={s}>{s}</option>)}
          </select>

          {/* Type (dropdown) */}
          <select
            value={typeFilter}
            onChange={e => { setTypeFilter(e.target.value); setPage(1) }}
            className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          >
            <option value="">All Types</option>
            {availableTypes.map(t => <option key={t} value={t}>{t}</option>)}
          </select>

          {/* Brand (dropdown) */}
          <select
            value={brandFilter}
            onChange={e => { setBrandFilter(e.target.value); setPage(1) }}
            className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          >
            <option value="">All Brands</option>
            {availableBrands.map(b => <option key={b} value={b}>{b}</option>)}
          </select>

          {/* Model (text input — typing) */}
          <input
            value={model}
            onChange={e => setModel(e.target.value)}
            placeholder="Model search…"
            className="border border-gray-200 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 w-48"
          />

          <button onClick={clearFilters} className="text-sm text-gray-500 hover:text-gray-700 underline">
            Clear filters
          </button>

          <span className="text-sm text-gray-500 ml-auto">Total: {total.toLocaleString()} machines</span>
        </div>

        {/* Bulk delete bar */}
        {siteFilter && (
          <div className="flex items-center justify-between bg-orange-50 border border-orange-200 rounded-xl px-4 py-3">
            <span className="text-sm text-orange-700">
              Showing machines from <strong>{siteFilter}</strong>
            </span>
            <button
              onClick={() => setBulkDeleteSite(siteFilter)}
              className="px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white text-xs rounded-lg font-medium transition-colors"
            >
              Delete all from {siteFilter}
            </button>
          </div>
        )}

        {isLoading ? (
          <div className="flex justify-center py-12">
            <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <div className="bg-white rounded-xl shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-100">
                    <th className="text-left px-4 py-3 font-medium text-gray-600 w-10"></th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Machine</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Site</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Brand</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Type</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600 cursor-pointer select-none whitespace-nowrap"
                        onClick={toggleYearSort}>
                      Year&nbsp;
                      <span className="text-gray-400">
                        {yearSort === 'asc' ? '↑' : yearSort === 'desc' ? '↓' : '↕'}
                      </span>
                    </th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Price</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
                    <th className="text-right px-4 py-3 font-medium text-gray-600">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {machines.map(m => (
                    <tr key={m.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-2">
                        {m.image_url ? (
                          <img src={m.image_url} alt="" className="w-10 h-10 object-cover rounded border bg-gray-100"
                            onError={e => { e.target.onerror = null; e.target.className = 'w-10 h-10 rounded border bg-gray-100' }} />
                        ) : (
                          <div className="w-10 h-10 rounded border bg-gray-100 flex items-center justify-center text-gray-300 text-xs">?</div>
                        )}
                      </td>
                      <td className="px-4 py-2 max-w-xs">
                        <p className="text-gray-800 truncate text-xs font-medium">{m.name}</p>
                        {m.catalog_id && <p className="text-gray-400 text-xs">{m.catalog_id}</p>}
                      </td>
                      <td className="px-4 py-2">
                        <span className="bg-blue-50 text-blue-700 text-xs px-2 py-0.5 rounded">{m.site_name}</span>
                      </td>
                      <td className="px-4 py-2 text-gray-600 text-xs">{m.brand || '—'}</td>
                      <td className="px-4 py-2 text-gray-600 text-xs max-w-[140px] truncate">{m.machine_type || '—'}</td>
                      <td className="px-4 py-2 text-gray-700 text-xs">{m.year_of_manufacture || '—'}</td>
                      <td className="px-4 py-2 text-gray-700 text-xs whitespace-nowrap">{formatPrice(m)}</td>
                      <td className="px-4 py-2 text-xs">
                        <span className={`px-2 py-0.5 rounded ${m.condition === 'used' ? 'bg-yellow-50 text-yellow-700' : 'bg-green-50 text-green-700'}`}>
                          {m.condition || 'used'}
                        </span>
                      </td>
                      <td className="px-4 py-2">
                        <div className="flex items-center justify-end gap-1">
                          <button
                            onClick={() => navigate(`/machines/${m.id}`)}
                            className="p-1.5 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors text-xs"
                            title="View / Edit"
                          >✏️</button>
                          <button
                            onClick={() => setDeleteTarget(m.id)}
                            className="p-1.5 text-red-500 hover:bg-red-50 rounded-lg transition-colors text-xs"
                            title="Delete"
                          >🗑</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {machines.length === 0 && (
                    <tr><td colSpan={9} className="text-center py-8 text-gray-400">No machines found</td></tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-5 py-4 border-t border-gray-100">
                <p className="text-sm text-gray-500">Page {page} of {totalPages}</p>
                <div className="flex gap-2">
                  <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}
                    className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm disabled:opacity-40 hover:bg-gray-50 transition-colors">← Prev</button>
                  {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                    const pg = Math.max(1, Math.min(page - 2, totalPages - 4)) + i
                    return (
                      <button key={pg} onClick={() => setPage(pg)}
                        className={`px-3 py-1.5 border rounded-lg text-sm transition-colors ${pg === page ? 'bg-blue-600 text-white border-blue-600' : 'border-gray-200 hover:bg-gray-50'}`}>
                        {pg}
                      </button>
                    )
                  })}
                  <button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}
                    className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm disabled:opacity-40 hover:bg-gray-50 transition-colors">Next →</button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <ConfirmModal
        isOpen={!!deleteTarget}
        title="Delete Machine"
        message="Are you sure you want to delete this machine?"
        onConfirm={() => { delMut.mutate(deleteTarget); setDeleteTarget(null) }}
        onCancel={() => setDeleteTarget(null)}
      />

      <ConfirmModal
        isOpen={!!bulkDeleteSite}
        title="Bulk Delete"
        message={`Delete ALL machines from "${bulkDeleteSite}"? This cannot be undone.`}
        onConfirm={() => { bulkMut.mutate(bulkDeleteSite); setBulkDeleteSite(null); setSiteFilter('') }}
        onCancel={() => setBulkDeleteSite(null)}
      />
    </AdminLayout>
  )
}
