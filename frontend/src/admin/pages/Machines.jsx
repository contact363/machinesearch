import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getMachines, deleteMachine, deleteBySite, getSiteConfigs } from '../api/adminClient'
import AdminLayout from '../components/AdminLayout'
import ConfirmModal from '../components/ConfirmModal'
import { useToast } from '../components/Toast'

function DetailModal({ machine, onClose }) {
  if (!machine) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b sticky top-0 bg-white">
          <h3 className="font-semibold text-gray-800 text-sm truncate mr-4">{machine.name}</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl flex-shrink-0">✕</button>
        </div>
        <div className="p-6 space-y-4">
          {machine.image_url && (
            <img src={machine.image_url} alt="" className="w-32 h-24 object-cover rounded-lg border" onError={e => e.target.style.display='none'} />
          )}
          <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
            {[
              ['ID', machine.id],
              ['Brand', machine.brand],
              ['Price', machine.price ? `${machine.price} ${machine.currency}` : '—'],
              ['Location', machine.location],
              ['Site', machine.site_name],
              ['Language', machine.language],
              ['Views', machine.view_count],
              ['Clicks', machine.click_count],
              ['Created', machine.created_at ? new Date(machine.created_at).toLocaleString() : '—'],
            ].map(([k, v]) => (
              <div key={k}><span className="text-gray-500">{k}:</span> <span className="text-gray-800">{v ?? '—'}</span></div>
            ))}
          </div>
          {machine.description && (
            <div>
              <p className="text-xs font-medium text-gray-500 mb-1">Description</p>
              <p className="text-sm text-gray-700 bg-gray-50 rounded-lg p-3">{machine.description}</p>
            </div>
          )}
          {machine.source_url && (
            <a href={machine.source_url} target="_blank" rel="noreferrer"
              className="inline-flex items-center gap-2 text-blue-600 text-sm hover:underline">
              🔗 View source
            </a>
          )}
          {machine.specs && Object.keys(machine.specs).length > 0 && (
            <div>
              <p className="text-xs font-medium text-gray-500 mb-2">Specs</p>
              <table className="w-full text-xs border border-gray-100 rounded-lg overflow-hidden">
                <tbody>
                  {Object.entries(machine.specs).map(([k, v]) => (
                    <tr key={k} className="border-b border-gray-50">
                      <td className="px-3 py-1.5 bg-gray-50 font-medium text-gray-600 w-1/3">{k}</td>
                      <td className="px-3 py-1.5 text-gray-700">{String(v)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default function Machines() {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [siteFilter, setSiteFilter] = useState('')
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [bulkDeleteSite, setBulkDeleteSite] = useState(null)
  const [detailMachine, setDetailMachine] = useState(null)

  const qc = useQueryClient()
  const toast = useToast()

  // Debounce search
  useEffect(() => {
    const t = setTimeout(() => { setDebouncedSearch(search); setPage(1) }, 400)
    return () => clearTimeout(t)
  }, [search])

  const { data, isLoading } = useQuery({
    queryKey: ['machines', page, debouncedSearch, siteFilter],
    queryFn: () => getMachines({ page, limit: 25, search: debouncedSearch || undefined, site_name: siteFilter || undefined }),
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

  const machines = data?.machines || []
  const total = data?.total || 0
  const totalPages = Math.ceil(total / 25)
  const sites = configsData?.configs?.map(c => c.name) || []

  const formatPrice = (m) => {
    if (!m.price) return '—'
    return `${m.currency || ''} ${m.price.toLocaleString()}`
  }

  return (
    <AdminLayout>
      <div className="space-y-4">
        {/* Top bar */}
        <div className="flex flex-wrap items-center gap-3">
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search name or brand…"
            className="border border-gray-200 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 w-64"
          />
          <select
            value={siteFilter}
            onChange={e => { setSiteFilter(e.target.value); setPage(1) }}
            className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          >
            <option value="">All sites</option>
            {sites.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
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
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Image</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Name</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Brand</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Price</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Location</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Site</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Date</th>
                    <th className="text-right px-4 py-3 font-medium text-gray-600">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {machines.map(m => (
                    <tr key={m.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-2">
                        {m.image_url ? (
                          <img src={m.image_url} alt="" className="w-10 h-10 object-cover rounded border bg-gray-100"
                            onError={e => { e.target.onerror=null; e.target.src=''; e.target.className='w-10 h-10 rounded border bg-gray-100' }} />
                        ) : (
                          <div className="w-10 h-10 rounded border bg-gray-100 flex items-center justify-center text-gray-300 text-xs">?</div>
                        )}
                      </td>
                      <td className="px-4 py-2 max-w-xs">
                        <p className="text-gray-800 truncate text-xs">{m.name}</p>
                      </td>
                      <td className="px-4 py-2 text-gray-600 text-xs">{m.brand || '—'}</td>
                      <td className="px-4 py-2 text-gray-700 text-xs whitespace-nowrap">{formatPrice(m)}</td>
                      <td className="px-4 py-2 text-gray-600 text-xs">{m.location || '—'}</td>
                      <td className="px-4 py-2"><span className="bg-blue-50 text-blue-700 text-xs px-2 py-0.5 rounded">{m.site_name}</span></td>
                      <td className="px-4 py-2 text-gray-500 text-xs whitespace-nowrap">
                        {m.created_at ? new Date(m.created_at).toLocaleDateString() : '—'}
                      </td>
                      <td className="px-4 py-2">
                        <div className="flex items-center justify-end gap-1">
                          <button onClick={() => setDetailMachine(m)}
                            className="p-1.5 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors text-xs">👁</button>
                          <button onClick={() => setDeleteTarget(m.id)}
                            className="p-1.5 text-red-500 hover:bg-red-50 rounded-lg transition-colors text-xs">🗑</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {machines.length === 0 && (
                    <tr><td colSpan={8} className="text-center py-8 text-gray-400">No machines found</td></tr>
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

      <DetailModal machine={detailMachine} onClose={() => setDetailMachine(null)} />

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
