import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getJobStatus, getJobHistory, startAll } from '../api/adminClient'
import AdminLayout from '../components/AdminLayout'
import StatusBadge from '../components/StatusBadge'
import { useToast } from '../components/Toast'

export default function ScraperJobs() {
  const [page, setPage] = useState(1)
  const [siteFilter, setSiteFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  const qc = useQueryClient()
  const toast = useToast()

  const { data: statusData } = useQuery({
    queryKey: ['jobStatus'],
    queryFn: getJobStatus,
    refetchInterval: 10_000,
  })

  const { data: histData, isLoading: histLoading } = useQuery({
    queryKey: ['jobHistory', page, siteFilter, statusFilter, dateFrom, dateTo],
    queryFn: () => getJobHistory({
      page,
      limit: 20,
      site: siteFilter || undefined,
      status: statusFilter || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
    }),
  })

  const startAllMut = useMutation({
    mutationFn: startAll,
    onSuccess: d => { qc.invalidateQueries({ queryKey: ['jobStatus'] }); toast(`Started ${d.started?.length || 0} jobs`, 'success') },
    onError: e => toast(e.response?.data?.detail || 'Start failed', 'error'),
  })

  const activeJobs = statusData?.jobs?.filter(j => j.status === 'running') || []
  const recentJobs = statusData?.jobs?.filter(j => j.status !== 'running') || []

  const jobs = histData?.jobs || []
  const total = histData?.total || 0
  const totalPages = Math.ceil(total / 20)

  const sites = [...new Set(jobs.map(j => j.site_name))].filter(Boolean)

  return (
    <AdminLayout>
      <div className="space-y-6">
        {/* Live status */}
        <div className="bg-white rounded-xl shadow-sm p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-gray-700">Live Status</h2>
            <button
              onClick={() => startAllMut.mutate()}
              disabled={startAllMut.isPending}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-60 text-white text-sm rounded-lg font-medium transition-colors flex items-center gap-2"
            >
              {startAllMut.isPending
                ? <span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                : '▶'
              }
              Start All Sites
            </button>
          </div>

          {activeJobs.length === 0 && recentJobs.length === 0 ? (
            <p className="text-gray-400 text-sm text-center py-6">No jobs running</p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
              {[...activeJobs, ...recentJobs.slice(0, 6)].map(job => (
                <div key={job.job_id} className={`rounded-lg p-4 border ${
                  job.status === 'running' ? 'bg-blue-50 border-blue-200' :
                  job.status === 'failed'  ? 'bg-red-50 border-red-200' :
                                             'bg-gray-50 border-gray-200'
                }`}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium text-sm text-gray-800">{job.site_name}</span>
                    <StatusBadge status={job.status} />
                  </div>
                  <p className="text-xs text-gray-500">
                    Started: {job.started_at ? new Date(job.started_at).toLocaleTimeString() : '—'}
                  </p>
                  {job.items_found > 0 && (
                    <p className="text-xs text-gray-500">Found: {job.items_found} | New: {job.items_new}</p>
                  )}
                  {job.error && <p className="text-xs text-red-600 mt-1 truncate">{job.error}</p>}
                  {job.status === 'running' && (
                    <div className="mt-2 h-1.5 bg-blue-200 rounded-full overflow-hidden">
                      <div className="h-full bg-blue-500 rounded-full animate-pulse w-2/3" />
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Job history */}
        <div className="bg-white rounded-xl shadow-sm">
          <div className="px-5 py-4 border-b border-gray-100">
            <h2 className="text-sm font-semibold text-gray-700 mb-3">Job History</h2>
            {/* Filters */}
            <div className="flex flex-wrap gap-3">
              <select
                value={siteFilter}
                onChange={e => { setSiteFilter(e.target.value); setPage(1) }}
                className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-400"
              >
                <option value="">All sites</option>
                {sites.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
              <select
                value={statusFilter}
                onChange={e => { setStatusFilter(e.target.value); setPage(1) }}
                className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-400"
              >
                <option value="">All statuses</option>
                <option value="completed">Completed</option>
                <option value="running">Running</option>
                <option value="failed">Failed</option>
                <option value="pending">Pending</option>
              </select>
              <input type="date" value={dateFrom} onChange={e => { setDateFrom(e.target.value); setPage(1) }}
                className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-400" />
              <input type="date" value={dateTo} onChange={e => { setDateTo(e.target.value); setPage(1) }}
                className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-400" />
            </div>
          </div>

          {histLoading ? (
            <div className="flex justify-center py-10">
              <div className="w-7 h-7 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-100">
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Site</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Started</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Duration</th>
                    <th className="text-right px-4 py-3 font-medium text-gray-600">Pages</th>
                    <th className="text-right px-4 py-3 font-medium text-gray-600">Found</th>
                    <th className="text-right px-4 py-3 font-medium text-gray-600">New</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Error</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {jobs.map(job => (
                    <tr key={job.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-medium text-gray-800">{job.site_name}</td>
                      <td className="px-4 py-3"><StatusBadge status={job.status} /></td>
                      <td className="px-4 py-3 text-gray-500 text-xs whitespace-nowrap">
                        {job.started_at ? new Date(job.started_at).toLocaleString() : '—'}
                      </td>
                      <td className="px-4 py-3 text-gray-600 text-xs">{job.duration || '—'}</td>
                      <td className="px-4 py-3 text-right text-gray-600">{job.pages_scraped ?? 0}</td>
                      <td className="px-4 py-3 text-right text-gray-600">{job.items_found ?? 0}</td>
                      <td className="px-4 py-3 text-right text-green-600 font-medium">{job.items_new ?? 0}</td>
                      <td className="px-4 py-3 text-red-500 text-xs max-w-xs">
                        {job.error_message ? (
                          <span title={job.error_message} className="cursor-help">
                            {job.error_message.slice(0, 50)}{job.error_message.length > 50 ? '…' : ''}
                          </span>
                        ) : '—'}
                      </td>
                    </tr>
                  ))}
                  {jobs.length === 0 && (
                    <tr><td colSpan={8} className="text-center py-8 text-gray-400">No jobs found</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-5 py-4 border-t border-gray-100">
              <p className="text-sm text-gray-500">Page {page} of {totalPages} ({total} total)</p>
              <div className="flex gap-2">
                <button
                  disabled={page <= 1}
                  onClick={() => setPage(p => p - 1)}
                  className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-40 transition-colors"
                >← Prev</button>
                <button
                  disabled={page >= totalPages}
                  onClick={() => setPage(p => p + 1)}
                  className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-40 transition-colors"
                >Next →</button>
              </div>
            </div>
          )}
        </div>
      </div>
    </AdminLayout>
  )
}
