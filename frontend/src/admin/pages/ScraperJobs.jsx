import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getJobStatus, getJobHistory, startAll } from '../api/adminClient'
import AdminLayout from '../components/AdminLayout'
import { useToast } from '../components/Toast'

function durationStr(startedAt, finishedAt) {
  if (!startedAt) return '—'
  const end = finishedAt ? new Date(finishedAt) : new Date()
  const diff = Math.floor((end - new Date(startedAt)) / 1000)
  if (diff < 60) return `${diff}s`
  const m = Math.floor(diff / 60)
  const s = diff % 60
  return `${m}m ${s}s`
}

function StatusPill({ status }) {
  const map = {
    running:   'bg-blue-100 text-blue-700',
    completed: 'bg-green-100 text-green-700',
    failed:    'bg-red-100 text-red-700',
    pending:   'bg-yellow-100 text-yellow-700',
    stuck:     'bg-orange-100 text-orange-700',
  }
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${map[status] || 'bg-gray-100 text-gray-600'}`}>
      {status === 'running' && <span className="w-1.5 h-1.5 bg-blue-500 rounded-full mr-1.5 animate-pulse" />}
      {status}
    </span>
  )
}

export default function ScraperJobs() {
  const [page, setPage] = useState(1)
  const [siteFilter, setSiteFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')

  const qc = useQueryClient()
  const toast = useToast()

  const { data: statusData, refetch: refetchStatus } = useQuery({
    queryKey: ['jobStatus'],
    queryFn: getJobStatus,
    refetchInterval: 10_000,
  })

  const { data: histData, isLoading, refetch: refetchHist } = useQuery({
    queryKey: ['jobHistory', page, siteFilter, statusFilter],
    queryFn: () => getJobHistory({
      page,
      limit: 25,
      site: siteFilter || undefined,
      status: statusFilter || undefined,
    }),
  })

  const startAllMut = useMutation({
    mutationFn: startAll,
    onSuccess: d => {
      qc.invalidateQueries({ queryKey: ['jobStatus'] })
      toast(`Started ${d.started?.length || 0} jobs`, 'success')
    },
    onError: e => toast(e.response?.data?.detail || 'Start failed', 'error'),
  })

  const handleRefresh = () => { refetchStatus(); refetchHist() }

  const allJobs = statusData?.jobs || []
  const stuckJobs = allJobs.filter(j => j.status === 'running' && j.started_at && (Date.now() - new Date(j.started_at)) > 60 * 60 * 1000)

  const jobs = histData?.jobs || []
  const total = histData?.total || 0
  const totalPages = Math.max(1, Math.ceil(total / 25))

  const sites = [...new Set(jobs.map(j => j.site_name).filter(Boolean))].sort()

  return (
    <AdminLayout>
      <div className="space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between flex-wrap gap-2">
          <h1 className="text-lg font-bold text-gray-900">Crawl Logs</h1>
          <div className="flex items-center gap-2">
            {stuckJobs.length > 0 && (
              <span className="text-xs bg-orange-100 text-orange-700 px-3 py-1.5 rounded-lg font-medium">
                {stuckJobs.length} stuck job{stuckJobs.length !== 1 ? 's' : ''}
              </span>
            )}
            <button
              onClick={handleRefresh}
              className="px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-700 hover:bg-gray-50 transition-colors">
              ↻ Refresh
            </button>
            <button
              onClick={() => startAllMut.mutate()}
              disabled={startAllMut.isPending}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-60 text-white text-sm font-semibold rounded-lg transition-colors flex items-center gap-2">
              {startAllMut.isPending
                ? <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                : <span>▶</span>}
              Start All
            </button>
          </div>
        </div>

        {/* Active jobs banner */}
        {allJobs.filter(j => j.status === 'running').length > 0 && (
          <div className="bg-blue-50 border border-blue-200 rounded-xl px-4 py-3 flex items-center gap-3">
            <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse flex-shrink-0" />
            <p className="text-sm text-blue-700 font-medium">
              {allJobs.filter(j => j.status === 'running').length} job(s) currently running:&nbsp;
              {allJobs.filter(j => j.status === 'running').map(j => j.site_name).join(', ')}
            </p>
          </div>
        )}

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-2">
          <select value={siteFilter} onChange={e => { setSiteFilter(e.target.value); setPage(1) }}
            className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400">
            <option value="">All Websites</option>
            {sites.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          <select value={statusFilter} onChange={e => { setStatusFilter(e.target.value); setPage(1) }}
            className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400">
            <option value="">All Status</option>
            <option value="running">Running</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
            <option value="pending">Pending</option>
          </select>
          {(siteFilter || statusFilter) && (
            <button onClick={() => { setSiteFilter(''); setStatusFilter(''); setPage(1) }}
              className="px-3 py-2 text-sm text-gray-500 hover:text-gray-700 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
              Clear filters
            </button>
          )}
        </div>

        {/* Table */}
        <div className="bg-white rounded-xl shadow-sm overflow-hidden">
          {isLoading ? (
            <div className="flex justify-center py-16">
              <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-200">
                    <th className="text-left px-4 py-3 font-semibold text-gray-600 text-xs uppercase tracking-wide">Website</th>
                    <th className="text-left px-4 py-3 font-semibold text-gray-600 text-xs uppercase tracking-wide">Type</th>
                    <th className="text-left px-4 py-3 font-semibold text-gray-600 text-xs uppercase tracking-wide">Status</th>
                    <th className="text-right px-4 py-3 font-semibold text-gray-600 text-xs uppercase tracking-wide">Found</th>
                    <th className="text-right px-4 py-3 font-semibold text-gray-600 text-xs uppercase tracking-wide">New</th>
                    <th className="text-right px-4 py-3 font-semibold text-gray-600 text-xs uppercase tracking-wide">Errors</th>
                    <th className="text-left px-4 py-3 font-semibold text-gray-600 text-xs uppercase tracking-wide">Started</th>
                    <th className="text-left px-4 py-3 font-semibold text-gray-600 text-xs uppercase tracking-wide">Duration</th>
                    <th className="text-left px-4 py-3 font-semibold text-gray-600 text-xs uppercase tracking-wide">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {jobs.map(job => (
                    <tr key={job.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3 font-medium text-gray-800">{job.site_name}</td>
                      <td className="px-4 py-3 text-xs text-gray-500">{job.job_type || 'scrape'}</td>
                      <td className="px-4 py-3"><StatusPill status={job.status} /></td>
                      <td className="px-4 py-3 text-right text-gray-700">{job.items_found ?? 0}</td>
                      <td className="px-4 py-3 text-right text-green-600 font-semibold">{job.items_new ?? 0}</td>
                      <td className="px-4 py-3 text-right text-red-500">{job.error_count ?? (job.error_message ? 1 : 0)}</td>
                      <td className="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">
                        {job.started_at ? new Date(job.started_at).toLocaleString() : '—'}
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-600 whitespace-nowrap">
                        {durationStr(job.started_at, job.finished_at)}
                      </td>
                      <td className="px-4 py-3">
                        {job.error_message && (
                          <span title={job.error_message}
                            className="inline-block px-2 py-0.5 bg-red-50 text-red-600 text-xs rounded cursor-help max-w-[120px] truncate">
                            {job.error_message.slice(0, 30)}{job.error_message.length > 30 ? '…' : ''}
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                  {jobs.length === 0 && (
                    <tr>
                      <td colSpan={9} className="text-center py-12 text-gray-400">No crawl logs found</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-5 py-3 border-t border-gray-100">
              <p className="text-sm text-gray-500">{total} total logs · Page {page} of {totalPages}</p>
              <div className="flex gap-1">
                <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}
                  className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-40 transition-colors">← Prev</button>
                <button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}
                  className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-40 transition-colors">Next →</button>
              </div>
            </div>
          )}
        </div>
      </div>
    </AdminLayout>
  )
}
