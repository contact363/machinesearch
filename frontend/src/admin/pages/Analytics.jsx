import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getClickAnalytics, getSearchAnalytics, getSiteConfigs } from '../api/adminClient'
import AdminLayout from '../components/AdminLayout'

function exportCsv(rows, filename) {
  if (!rows.length) return
  const keys = Object.keys(rows[0])
  const csv = [keys.join(','), ...rows.map(r =>
    keys.map(k => `"${String(r[k] ?? '').replace(/"/g, '""')}"`).join(',')
  )].join('\n')
  const blob = new Blob([csv], { type: 'text/csv' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = filename
  a.click()
}

function ClicksTab() {
  const [page, setPage] = useState(1)
  const [siteFilter, setSiteFilter] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['clicks', page, siteFilter, dateFrom, dateTo],
    queryFn: () => getClickAnalytics({
      page, limit: 50,
      site: siteFilter || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
    }),
  })

  const { data: configsData } = useQuery({ queryKey: ['configs'], queryFn: getSiteConfigs })
  const sites = configsData?.configs?.map(c => c.name) || []

  const clicks = data?.clicks || []
  const total = data?.total || 0
  const totalPages = Math.ceil(total / 50)

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <select value={siteFilter} onChange={e => { setSiteFilter(e.target.value); setPage(1) }}
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400">
          <option value="">All sites</option>
          {sites.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <input type="date" value={dateFrom} onChange={e => { setDateFrom(e.target.value); setPage(1) }}
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
        <input type="date" value={dateTo} onChange={e => { setDateTo(e.target.value); setPage(1) }}
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
        <span className="text-sm text-gray-500 ml-auto">{total} clicks</span>
        <button
          onClick={() => exportCsv(clicks, 'clicks.csv')}
          className="px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-700 hover:bg-gray-50 transition-colors"
        >⬇ Export CSV</button>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-10">
          <div className="w-7 h-7 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b">
                <th className="text-left px-4 py-3 font-medium text-gray-600">Machine Name</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Site</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Clicked At</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Source URL</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {clicks.map(c => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2 text-gray-800 text-xs max-w-xs truncate">{c.machine_name || '—'}</td>
                  <td className="px-4 py-2"><span className="bg-blue-50 text-blue-700 text-xs px-2 py-0.5 rounded">{c.site_name}</span></td>
                  <td className="px-4 py-2 text-gray-500 text-xs whitespace-nowrap">
                    {c.clicked_at ? new Date(c.clicked_at).toLocaleString() : '—'}
                  </td>
                  <td className="px-4 py-2 text-xs">
                    {c.source_url ? (
                      <a href={c.source_url} target="_blank" rel="noreferrer"
                        className="text-blue-600 hover:underline truncate block max-w-xs">🔗 {c.source_url.slice(0, 40)}…</a>
                    ) : '—'}
                  </td>
                </tr>
              ))}
              {clicks.length === 0 && (
                <tr><td colSpan={4} className="text-center py-8 text-gray-400">No click data yet</td></tr>
              )}
            </tbody>
          </table>

          {totalPages > 1 && (
            <div className="flex items-center justify-between px-5 py-4 border-t">
              <p className="text-sm text-gray-500">Page {page} of {totalPages}</p>
              <div className="flex gap-2">
                <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}
                  className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm disabled:opacity-40 hover:bg-gray-50">← Prev</button>
                <button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}
                  className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm disabled:opacity-40 hover:bg-gray-50">Next →</button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function SearchesTab() {
  const [page, setPage] = useState(1)
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [zeroOnly, setZeroOnly] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['searches', page, dateFrom, dateTo, zeroOnly],
    queryFn: () => getSearchAnalytics({
      page, limit: 50,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
      zero_results_only: zeroOnly || undefined,
    }),
  })

  const searches = data?.searches || []
  const total = data?.total || 0
  const totalPages = Math.ceil(total / 50)

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <input type="date" value={dateFrom} onChange={e => { setDateFrom(e.target.value); setPage(1) }}
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
        <input type="date" value={dateTo} onChange={e => { setDateTo(e.target.value); setPage(1) }}
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400" />
        <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
          <input type="checkbox" checked={zeroOnly} onChange={e => { setZeroOnly(e.target.checked); setPage(1) }}
            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500" />
          Zero results only
        </label>
        <span className="text-sm text-gray-500 ml-auto">{total} searches</span>
        <button
          onClick={() => exportCsv(searches, 'searches.csv')}
          className="px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-700 hover:bg-gray-50 transition-colors"
        >⬇ Export CSV</button>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-10">
          <div className="w-7 h-7 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b">
                <th className="text-left px-4 py-3 font-medium text-gray-600">Query</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Filters Used</th>
                <th className="text-right px-4 py-3 font-medium text-gray-600">Results</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {searches.map(s => (
                <tr key={s.id} className={`hover:bg-gray-50 ${s.results_count === 0 ? 'bg-red-50' : ''}`}>
                  <td className="px-4 py-2 text-gray-800 text-xs">{s.query || <em className="text-gray-400">no query</em>}</td>
                  <td className="px-4 py-2 text-gray-600 text-xs">
                    {s.filters && Object.keys(s.filters).length > 0
                      ? JSON.stringify(s.filters)
                      : '—'}
                  </td>
                  <td className={`px-4 py-2 text-right font-semibold text-xs ${s.results_count === 0 ? 'text-red-600' : 'text-gray-700'}`}>
                    {s.results_count}
                  </td>
                  <td className="px-4 py-2 text-gray-500 text-xs whitespace-nowrap">
                    {s.searched_at ? new Date(s.searched_at).toLocaleString() : '—'}
                  </td>
                </tr>
              ))}
              {searches.length === 0 && (
                <tr><td colSpan={4} className="text-center py-8 text-gray-400">No search data yet</td></tr>
              )}
            </tbody>
          </table>

          {totalPages > 1 && (
            <div className="flex items-center justify-between px-5 py-4 border-t">
              <p className="text-sm text-gray-500">Page {page} of {totalPages}</p>
              <div className="flex gap-2">
                <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}
                  className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm disabled:opacity-40 hover:bg-gray-50">← Prev</button>
                <button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}
                  className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm disabled:opacity-40 hover:bg-gray-50">Next →</button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function Analytics() {
  const [tab, setTab] = useState('clicks')

  return (
    <AdminLayout>
      <div className="space-y-4">
        {/* Tabs */}
        <div className="flex border-b border-gray-200">
          {['clicks', 'searches'].map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-5 py-2.5 text-sm font-medium transition-colors capitalize border-b-2 -mb-px ${
                tab === t
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {t}
            </button>
          ))}
        </div>

        {tab === 'clicks'   && <ClicksTab />}
        {tab === 'searches' && <SearchesTab />}
      </div>
    </AdminLayout>
  )
}
