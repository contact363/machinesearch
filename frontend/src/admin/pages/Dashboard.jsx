import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import {
  getOverview, clearAllMachines, getSchedulerStatus,
  getJobHistory, startAll, getSiteConfigs,
} from '../api/adminClient'
import AdminLayout from '../components/AdminLayout'
import ConfirmModal from '../components/ConfirmModal'
import { useToast } from '../components/Toast'

function MetricCard({ label, value, sub, accent }) {
  const colors = {
    blue:   'bg-blue-600',
    green:  'bg-emerald-500',
    violet: 'bg-violet-600',
    amber:  'bg-amber-500',
  }
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 flex flex-col gap-3">
      <div className={`w-8 h-1 rounded-full ${colors[accent] || colors.blue}`} />
      <div>
        <p className="text-[13px] text-gray-500 font-medium">{label}</p>
        <p className="text-3xl font-bold text-gray-900 mt-0.5 tabular-nums">{value ?? '—'}</p>
        {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
      </div>
    </div>
  )
}

function formatNextRun(isoStr) {
  if (!isoStr) return 'Unknown'
  const d = new Date(isoStr)
  const now = new Date()
  const diffMs = d - now
  if (diffMs < 0) return 'Running soon'
  const mins = Math.round(diffMs / 60000)
  if (mins < 60) return `in ${mins}m`
  const hrs = Math.floor(mins / 60)
  const rem = mins % 60
  return `in ${hrs}h ${rem > 0 ? ` ${rem}m` : ''}`
}

export default function Dashboard() {
  const [showClearConfirm, setShowClearConfirm] = useState(false)
  const qc = useQueryClient()
  const toast = useToast()
  const navigate = useNavigate()

  const clearMut = useMutation({
    mutationFn: clearAllMachines,
    onSuccess: d => {
      qc.invalidateQueries()
      toast(`Cleared ${d.machines_removed.toLocaleString()} machines`, 'success')
    },
    onError: e => toast(e.response?.data?.detail || 'Clear failed', 'error'),
  })

  const startAllMut = useMutation({
    mutationFn: startAll,
    onSuccess: d => {
      qc.invalidateQueries(['overview'])
      toast(`Scrape started for ${d.started?.length ?? 0} sites`, 'success')
      navigate('/admin/jobs')
    },
    onError: e => toast(e.response?.data?.detail || 'Failed to start', 'error'),
  })

  const { data, isLoading } = useQuery({
    queryKey: ['overview'],
    queryFn: getOverview,
    refetchInterval: 30_000,
  })

  const { data: sched } = useQuery({
    queryKey: ['scheduler'],
    queryFn: getSchedulerStatus,
    refetchInterval: 60_000,
  })

  const { data: recentJobs } = useQuery({
    queryKey: ['recentJobs'],
    queryFn: () => getJobHistory({ limit: 6 }),
    refetchInterval: 30_000,
  })

  const { data: configsData } = useQuery({
    queryKey: ['configs'],
    queryFn: getSiteConfigs,
  })

  const d = data || {}
  const siteMap = {}
  ;(d.top_sites || []).forEach(s => { siteMap[s.site] = s.count })
  const configs = configsData?.configs || []

  if (isLoading) return (
    <AdminLayout>
      <div className="flex items-center justify-center h-64">
        <div className="w-7 h-7 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
      </div>
    </AdminLayout>
  )

  return (
    <AdminLayout>
      <div className="space-y-5">

        {/* Top actions */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-gray-800">Overview</h2>
            <p className="text-xs text-gray-400 mt-0.5">Real-time stats across all data sources</p>
          </div>
          <button
            onClick={() => setShowClearConfirm(true)}
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-red-600 border border-red-200 rounded-lg hover:bg-red-50 transition-colors"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
            Clear all data
          </button>
        </div>

        {/* Metric cards */}
        <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
          <MetricCard
            label="Total Machines"
            value={d.total_machines?.toLocaleString()}
            sub="across all sources"
            accent="blue"
          />
          <MetricCard
            label="Active Sites"
            value={configs.filter(c => c.is_active).length}
            sub={`${configs.length} configured`}
            accent="green"
          />
          <MetricCard
            label="Searches Today"
            value={d.searches_today?.toLocaleString()}
            sub="user queries"
            accent="violet"
          />
          <MetricCard
            label="Clicks Today"
            value={d.clicks_today?.toLocaleString()}
            sub="machine detail views"
            accent="amber"
          />
        </div>

        {/* Auto-scrape + Run All */}
        <div className="bg-white rounded-xl border border-gray-200 px-5 py-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-9 h-9 rounded-lg bg-gray-50 border border-gray-200 flex items-center justify-center flex-shrink-0">
              <svg className="w-4.5 h-4.5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" style={{width:'18px',height:'18px'}}>
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-800">Scheduled Auto-Scrape</p>
              <p className="text-xs text-gray-500">
                Runs every 2 hours &mdash; next:{' '}
                <span className="font-medium text-blue-600">{formatNextRun(sched?.next_run)}</span>
                {sched?.next_run && (
                  <span className="text-gray-400 ml-1.5">
                    ({new Date(sched.next_run).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })})
                  </span>
                )}
              </p>
            </div>
          </div>
          <button
            onClick={() => startAllMut.mutate()}
            disabled={startAllMut.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white text-xs font-semibold rounded-lg transition-colors whitespace-nowrap"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {startAllMut.isPending ? 'Starting...' : 'Run All Now'}
          </button>
        </div>

        {/* Two columns: Sites + Recent Jobs */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">

          {/* Sites overview */}
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-gray-800">Data Sources</h3>
                <p className="text-xs text-gray-400 mt-0.5">Machine count per site</p>
              </div>
              <button
                onClick={() => navigate('/admin/sites')}
                className="text-xs text-blue-600 hover:text-blue-800 font-medium"
              >
                Manage →
              </button>
            </div>
            <div className="divide-y divide-gray-50">
              {configs.length === 0 ? (
                <p className="text-center text-gray-400 text-sm py-8">No sites configured</p>
              ) : configs.slice(0, 8).map(cfg => {
                const count = siteMap[cfg.name] || 0
                const maxCount = Math.max(...Object.values(siteMap), 1)
                const pct = Math.round((count / maxCount) * 100)
                return (
                  <div key={cfg.name} className="px-5 py-3 flex items-center gap-3">
                    <div className={`w-2 h-2 rounded-full flex-shrink-0 ${cfg.is_active ? 'bg-emerald-400' : 'bg-gray-300'}`} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-medium text-gray-700 truncate">{cfg.display_name || cfg.name}</span>
                        <span className="text-xs font-semibold text-gray-600 ml-2 tabular-nums">{count.toLocaleString()}</span>
                      </div>
                      <div className="w-full bg-gray-100 rounded-full h-1">
                        <div className="bg-blue-500 h-1 rounded-full transition-all" style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Recent scrape jobs */}
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-gray-800">Recent Jobs</h3>
                <p className="text-xs text-gray-400 mt-0.5">Last scraping activity</p>
              </div>
              <button
                onClick={() => navigate('/admin/jobs')}
                className="text-xs text-blue-600 hover:text-blue-800 font-medium"
              >
                View all →
              </button>
            </div>
            <div className="divide-y divide-gray-50">
              {recentJobs?.jobs?.length ? recentJobs.jobs.slice(0, 6).map(job => (
                <div key={job.id} className="px-5 py-3 flex items-center gap-3">
                  <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
                    job.status === 'completed' ? 'bg-emerald-400' :
                    job.status === 'failed' ? 'bg-red-400' :
                    job.status === 'running' ? 'bg-blue-400 animate-pulse' :
                    'bg-gray-300'
                  }`} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium text-gray-700 truncate">{job.site_name}</span>
                      <span className={`text-[11px] font-semibold ml-2 ${
                        job.status === 'completed' ? 'text-emerald-600' :
                        job.status === 'failed' ? 'text-red-500' :
                        'text-blue-600'
                      }`}>
                        {job.status === 'completed' ? `+${job.items_new ?? 0} new` : job.status}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-[11px] text-gray-400">
                        {job.items_found ?? 0} found &middot; {job.duration ?? '—'}
                      </span>
                      {job.started_at && (
                        <span className="text-[11px] text-gray-300">
                          {new Date(job.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              )) : (
                <div className="px-5 py-10 text-center">
                  <p className="text-sm text-gray-400">No scrape jobs yet</p>
                  <p className="text-xs text-gray-300 mt-1">Run a scrape to see results here</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Zero-result searches */}
        {d.zero_result_searches?.length > 0 && (
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-100">
              <h3 className="text-sm font-semibold text-gray-800">Zero-Result Searches</h3>
              <p className="text-xs text-gray-400 mt-0.5">Queries returning no machines — content gaps to address</p>
            </div>
            <div className="divide-y divide-gray-50">
              {d.zero_result_searches.map((row, i) => (
                <div key={i} className="flex items-center justify-between px-5 py-3">
                  <span className="text-xs text-gray-700 font-medium">"{row.query}"</span>
                  <span className="text-xs font-semibold text-red-500 ml-4">{row.count}×</span>
                </div>
              ))}
            </div>
          </div>
        )}

      </div>

      <ConfirmModal
        isOpen={showClearConfirm}
        title="Clear All Data"
        message="This will permanently delete ALL machines and scrape history. Cannot be undone."
        onConfirm={() => { clearMut.mutate(); setShowClearConfirm(false) }}
        onCancel={() => setShowClearConfirm(false)}
      />
    </AdminLayout>
  )
}
