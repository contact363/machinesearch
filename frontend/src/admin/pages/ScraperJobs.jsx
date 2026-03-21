import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getJobStatus, getJobHistory, startAll, deleteJob, getSiteConfigs } from '../api/adminClient'
import AdminLayout from '../components/AdminLayout'
import { useToast } from '../components/Toast'

function duration(startedAt, finishedAt) {
  if (!startedAt) return '—'
  const end = finishedAt ? new Date(finishedAt) : new Date()
  const secs = Math.floor((end - new Date(startedAt)) / 1000)
  if (secs < 60) return `${secs}s`
  const m = Math.floor(secs / 60)
  const s = secs % 60
  return `${m}m ${s > 0 ? ` ${s}s` : ''}`
}

function StatusBadge({ status }) {
  const styles = {
    running:   'bg-blue-50 text-blue-700 border-blue-100',
    completed: 'bg-emerald-50 text-emerald-700 border-emerald-100',
    failed:    'bg-red-50 text-red-600 border-red-100',
    pending:   'bg-amber-50 text-amber-700 border-amber-100',
  }
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-semibold border ${styles[status] || 'bg-gray-50 text-gray-600 border-gray-100'}`}>
      {status === 'running' && <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />}
      {status === 'completed' && <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />}
      {status === 'failed' && <span className="w-1.5 h-1.5 rounded-full bg-red-500" />}
      {status}
    </span>
  )
}

function ErrorCell({ msg }) {
  const [expanded, setExpanded] = useState(false)
  if (!msg) return <span className="text-gray-300 text-xs">—</span>
  const short = msg.length > 55 ? msg.slice(0, 55) + '…' : msg
  return (
    <div className="max-w-[280px]">
      <p className="text-xs text-red-500 leading-snug cursor-pointer" onClick={() => setExpanded(e => !e)} title="Click to expand">
        {expanded ? msg : short}
      </p>
      {msg.length > 55 && (
        <button onClick={() => setExpanded(e => !e)} className="text-[10px] text-red-400 hover:text-red-600 mt-0.5">
          {expanded ? 'Show less' : 'Show more'}
        </button>
      )}
    </div>
  )
}

export default function ScraperJobs() {
  const [page, setPage] = useState(1)
  const [siteFilter, setSiteFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')

  const qc = useQueryClient()
  const toast = useToast()

  const { data: statusData, refetch: refetchStatus, isFetching: fetchingStatus } = useQuery({
    queryKey: ['jobStatus'],
    queryFn: getJobStatus,
    refetchInterval: 8_000,
  })

  const { data: configsData } = useQuery({
    queryKey: ['configs'],
    queryFn: getSiteConfigs,
  })

  const hasRunning = (statusData?.jobs || []).some(j => j.status === 'running')

  const { data: histData, isLoading, isFetching: fetchingHist, refetch: refetchHist } = useQuery({
    queryKey: ['jobHistory', page, siteFilter, statusFilter],
    queryFn: () => getJobHistory({
      page,
      limit: 25,
      site: siteFilter || undefined,
      status: statusFilter || undefined,
    }),
    refetchInterval: hasRunning ? 5_000 : false,
  })

  const startAllMut = useMutation({
    mutationFn: startAll,
    onSuccess: d => {
      qc.invalidateQueries({ queryKey: ['jobStatus'] })
      toast(`Started scrape for ${d.started?.length || 0} sites`, 'success')
    },
    onError: e => toast(e.response?.data?.detail || 'Start failed', 'error'),
  })

  const deleteJobMut = useMutation({
    mutationFn: deleteJob,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['jobHistory'] })
      toast('Log entry deleted', 'success')
    },
    onError: e => toast(e.response?.data?.detail || 'Delete failed', 'error'),
  })

  const isRefreshing = fetchingStatus || fetchingHist
  const handleRefresh = () => { refetchStatus(); refetchHist() }

  const runningJobs = (statusData?.jobs || []).filter(j => j.status === 'running')
  const jobs = histData?.jobs || []
  const total = histData?.total || 0
  const totalPages = Math.max(1, Math.ceil(total / 25))
  const sites = configsData?.configs?.map(c => c.name) || []

  return (
    <AdminLayout>
      <div className="space-y-4">

        {/* Header */}
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <div>
            <p className="text-xs text-gray-400 mt-0.5">{total.toLocaleString()} total log entries</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleRefresh}
              disabled={isRefreshing}
              className="flex items-center gap-1.5 px-3 py-2 border border-gray-200 rounded-lg text-xs text-gray-600 hover:bg-gray-50 disabled:opacity-60 transition-colors bg-white"
            >
              <svg className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              {isRefreshing ? 'Refreshing…' : 'Refresh'}
            </button>
            <button
              onClick={() => startAllMut.mutate()}
              disabled={startAllMut.isPending}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white text-xs font-semibold rounded-lg transition-colors"
            >
              {startAllMut.isPending ? (
                <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
              ) : (
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              )}
              {startAllMut.isPending ? 'Starting…' : 'Run All Sites'}
            </button>
          </div>
        </div>

        {/* Running banner */}
        {runningJobs.length > 0 && (
          <div className="bg-blue-50 border border-blue-100 rounded-xl px-4 py-3 flex items-center gap-3">
            <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse flex-shrink-0" />
            <p className="text-xs text-blue-700 font-medium">
              {runningJobs.length} scrape{runningJobs.length > 1 ? 's' : ''} in progress:&nbsp;
              <span className="font-semibold">{runningJobs.map(j => j.site_name).join(', ')}</span>
            </p>
          </div>
        )}

        {/* Filters + table */}
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">

          {/* Filter bar */}
          <div className="px-4 py-3 border-b border-gray-100 flex items-center gap-2 flex-wrap">
            <select
              value={siteFilter}
              onChange={e => { setSiteFilter(e.target.value); setPage(1) }}
              className="text-xs border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-600"
            >
              <option value="">All Sites</option>
              {sites.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
            <select
              value={statusFilter}
              onChange={e => { setStatusFilter(e.target.value); setPage(1) }}
              className="text-xs border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-600"
            >
              <option value="">All Status</option>
              <option value="running">Running</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
            </select>
            {(siteFilter || statusFilter) && (
              <button
                onClick={() => { setSiteFilter(''); setStatusFilter(''); setPage(1) }}
                className="text-xs text-gray-400 hover:text-gray-600 px-2 py-2"
              >
                Clear
              </button>
            )}
          </div>

          {/* Table */}
          {isLoading ? (
            <div className="flex justify-center py-16">
              <div className="w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-gray-100 bg-gray-50/60">
                    <th className="text-left px-4 py-3 font-semibold text-gray-500 uppercase tracking-wider text-[10px]">Site</th>
                    <th className="text-left px-4 py-3 font-semibold text-gray-500 uppercase tracking-wider text-[10px]">Status</th>
                    <th className="text-right px-4 py-3 font-semibold text-gray-500 uppercase tracking-wider text-[10px]">Found</th>
                    <th className="text-right px-4 py-3 font-semibold text-gray-500 uppercase tracking-wider text-[10px]">New</th>
                    <th className="text-left px-4 py-3 font-semibold text-gray-500 uppercase tracking-wider text-[10px]">Started</th>
                    <th className="text-left px-4 py-3 font-semibold text-gray-500 uppercase tracking-wider text-[10px]">Duration</th>
                    <th className="text-left px-4 py-3 font-semibold text-gray-500 uppercase tracking-wider text-[10px]">Error</th>
                    <th className="w-10 px-4 py-3" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {jobs.map(job => (
                    <tr key={job.id} className="hover:bg-gray-50/60 transition-colors">
                      <td className="px-4 py-3 font-medium text-gray-800">{job.site_name}</td>
                      <td className="px-4 py-3"><StatusBadge status={job.status} /></td>
                      <td className="px-4 py-3 text-right text-gray-600 tabular-nums">{job.items_found ?? 0}</td>
                      <td className="px-4 py-3 text-right font-semibold text-emerald-600 tabular-nums">{job.items_new ?? 0}</td>
                      <td className="px-4 py-3 text-gray-500 whitespace-nowrap">
                        {job.started_at
                          ? new Date(job.started_at).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
                          : '—'}
                      </td>
                      <td className="px-4 py-3 text-gray-500 tabular-nums">{duration(job.started_at, job.finished_at)}</td>
                      <td className="px-4 py-3"><ErrorCell msg={job.error_message} /></td>
                      <td className="px-4 py-3">
                        {job.status !== 'running' && (
                          <button
                            onClick={() => deleteJobMut.mutate(job.id)}
                            disabled={deleteJobMut.isPending}
                            className="w-7 h-7 flex items-center justify-center rounded-lg border border-gray-200 text-gray-400 hover:text-red-500 hover:border-red-200 hover:bg-red-50 transition-colors disabled:opacity-40"
                            title="Delete log"
                          >
                            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                  {jobs.length === 0 && (
                    <tr>
                      <td colSpan={8} className="text-center py-16">
                        <svg className="w-8 h-8 mx-auto mb-2 text-gray-200" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                        </svg>
                        <p className="text-gray-400 text-sm">No scrape jobs yet</p>
                        <p className="text-gray-300 text-xs mt-1">Click "Run All Sites" to start</p>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100">
              <p className="text-xs text-gray-500">{total} logs · page {page} of {totalPages}</p>
              <div className="flex gap-1">
                <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}
                  className="px-3 py-1.5 border border-gray-200 rounded-lg text-xs text-gray-500 hover:bg-gray-50 disabled:opacity-40 transition-colors">Prev</button>
                <button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}
                  className="px-3 py-1.5 border border-gray-200 rounded-lg text-xs text-gray-500 hover:bg-gray-50 disabled:opacity-40 transition-colors">Next</button>
              </div>
            </div>
          )}
        </div>
      </div>
    </AdminLayout>
  )
}
