import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts'
import { getOverview, clearAllMachines, getSchedulerStatus, getJobHistory, startAll } from '../api/adminClient'
import { useNavigate } from 'react-router-dom'
import StatCard from '../components/StatCard'
import AdminLayout from '../components/AdminLayout'
import ConfirmModal from '../components/ConfirmModal'
import { useToast } from '../components/Toast'

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
  return `in ${hrs}h ${rem}m`
}

export default function Dashboard() {
  const [showClearConfirm, setShowClearConfirm] = useState(false)
  const qc = useQueryClient()
  const toast = useToast()
  const navigate = useNavigate()

  const clearMut = useMutation({
    mutationFn: clearAllMachines,
    onSuccess: (d) => {
      qc.invalidateQueries()
      toast(`Cleared ${d.machines_removed.toLocaleString()} machines from database`, 'success')
    },
    onError: e => toast(e.response?.data?.detail || 'Clear failed', 'error'),
  })

  const startAllMut = useMutation({
    mutationFn: startAll,
    onSuccess: (d) => {
      qc.invalidateQueries(['overview'])
      toast(`Started scrape for ${d.started?.length ?? 0} sites`, 'success')
      navigate('/admin/jobs')
    },
    onError: e => toast(e.response?.data?.detail || 'Failed to start', 'error'),
  })

  const { data, isLoading, error } = useQuery({
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
    queryFn: () => getJobHistory({ limit: 5 }),
    refetchInterval: 30_000,
  })

  if (isLoading) return (
    <AdminLayout>
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    </AdminLayout>
  )

  if (error) return (
    <AdminLayout>
      <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl p-4">
        Failed to load overview: {error.message}
      </div>
    </AdminLayout>
  )

  const d = data || {}

  return (
    <AdminLayout>
      <div className="space-y-6">
        {/* Danger zone */}
        <div className="flex justify-end">
          <button
            onClick={() => setShowClearConfirm(true)}
            className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-semibold rounded-lg transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
            Clear All Data
          </button>
        </div>

        {/* Stat cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          <StatCard title="Total Machines"  value={d.total_machines?.toLocaleString()} icon="🗄" color="blue" />
          <StatCard title="Clicks Today"    value={d.clicks_today?.toLocaleString()}   icon="👆" color="green" />
          <StatCard title="Searches Today"  value={d.searches_today?.toLocaleString()} icon="🔍" color="purple" />
          <StatCard
            title="Active Jobs"
            value={d.active_jobs ?? 0}
            icon="⚡"
            color="orange"
            pulse={d.active_jobs > 0}
          />
        </div>

        {/* Auto-scrape scheduler banner */}
        <div className="bg-white rounded-xl shadow-sm p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-indigo-50 flex items-center justify-center text-lg">⏱</div>
            <div>
              <p className="text-sm font-semibold text-gray-800">Auto-Scrape (every 2 hours)</p>
              <p className="text-xs text-gray-500">
                Next run: <span className="font-medium text-indigo-600">{formatNextRun(sched?.next_run)}</span>
                {sched?.next_run && (
                  <span className="ml-2 text-gray-400">
                    ({new Date(sched.next_run).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })})
                  </span>
                )}
              </p>
            </div>
          </div>
          <button
            onClick={() => startAllMut.mutate()}
            disabled={startAllMut.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white text-sm font-semibold rounded-lg transition-colors"
          >
            {startAllMut.isPending ? 'Starting...' : 'Run All Now'}
          </button>
        </div>

        {/* Charts */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          <div className="bg-white rounded-xl shadow-sm p-5">
            <h2 className="text-sm font-semibold text-gray-700 mb-4">Top Sites by Machine Count</h2>
            {d.top_sites?.length ? (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={d.top_sites} margin={{ top: 0, right: 10, bottom: 40, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="site" tick={{ fontSize: 11 }} angle={-30} textAnchor="end" />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : <p className="text-gray-400 text-sm text-center py-8">No data</p>}
          </div>

          <div className="bg-white rounded-xl shadow-sm p-5">
            <h2 className="text-sm font-semibold text-gray-700 mb-4">Top Clicked Machines</h2>
            {d.top_clicked?.length ? (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={d.top_clicked} margin={{ top: 0, right: 10, bottom: 40, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} angle={-30} textAnchor="end" />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="clicks" fill="#10b981" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : <p className="text-gray-400 text-sm text-center py-8">No click data yet</p>}
          </div>
        </div>

        {/* Recent Scrape Jobs */}
        <div className="bg-white rounded-xl shadow-sm">
          <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-gray-700">Recent Scrape Jobs</h2>
              <p className="text-xs text-gray-400 mt-0.5">Last 5 scraping runs across all sites</p>
            </div>
            <button
              onClick={() => navigate('/admin/jobs')}
              className="text-xs text-indigo-600 hover:text-indigo-800 font-medium"
            >
              View all →
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-gray-500 uppercase tracking-wide border-b border-gray-100">
                  <th className="px-5 py-3 text-left">Site</th>
                  <th className="px-5 py-3 text-left">Status</th>
                  <th className="px-5 py-3 text-right">Found</th>
                  <th className="px-5 py-3 text-right">New</th>
                  <th className="px-5 py-3 text-right">Duration</th>
                  <th className="px-5 py-3 text-right">Started</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {recentJobs?.jobs?.length ? recentJobs.jobs.map(job => (
                  <tr key={job.id} className="hover:bg-gray-50">
                    <td className="px-5 py-3 font-medium text-gray-800">{job.site_name}</td>
                    <td className="px-5 py-3">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                        job.status === 'completed' ? 'bg-green-100 text-green-700' :
                        job.status === 'failed' ? 'bg-red-100 text-red-700' :
                        job.status === 'running' ? 'bg-blue-100 text-blue-700' :
                        'bg-gray-100 text-gray-600'
                      }`}>
                        {job.status === 'running' && <span className="w-1.5 h-1.5 bg-blue-500 rounded-full mr-1 animate-pulse" />}
                        {job.status}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-right text-gray-600">{job.items_found ?? '—'}</td>
                    <td className="px-5 py-3 text-right text-green-600 font-medium">{job.items_new ?? '—'}</td>
                    <td className="px-5 py-3 text-right text-gray-500">{job.duration ?? '—'}</td>
                    <td className="px-5 py-3 text-right text-gray-400 text-xs">
                      {job.started_at ? new Date(job.started_at).toLocaleString([], { month:'short', day:'numeric', hour:'2-digit', minute:'2-digit' }) : '—'}
                    </td>
                  </tr>
                )) : (
                  <tr><td colSpan={6} className="px-5 py-8 text-center text-gray-400 text-sm">No scrape jobs yet</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Tables */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          {/* Zero result searches */}
          <div className="bg-white rounded-xl shadow-sm">
            <div className="px-5 py-4 border-b border-gray-100">
              <h2 className="text-sm font-semibold text-gray-700">Zero Result Searches</h2>
              <p className="text-xs text-red-500 mt-0.5">Queries with no results — content gaps</p>
            </div>
            <div className="divide-y divide-gray-50">
              {d.zero_result_searches?.length ? d.zero_result_searches.map((row, i) => (
                <div key={i} className="flex justify-between items-center px-5 py-3 bg-red-50/40 hover:bg-red-50">
                  <span className="text-sm text-gray-800 truncate flex-1 mr-4">"{row.query}"</span>
                  <span className="text-sm font-semibold text-red-600 flex-shrink-0">{row.count}x</span>
                </div>
              )) : (
                <p className="text-gray-400 text-sm text-center py-6">No zero-result searches 🎉</p>
              )}
            </div>
          </div>

          {/* Top clicked sites */}
          <div className="bg-white rounded-xl shadow-sm">
            <div className="px-5 py-4 border-b border-gray-100">
              <h2 className="text-sm font-semibold text-gray-700">Top Clicked Sites</h2>
            </div>
            <div className="divide-y divide-gray-50">
              {d.top_clicked_sites?.length ? d.top_clicked_sites.map((row, i) => (
                <div key={i} className="flex justify-between items-center px-5 py-3 hover:bg-gray-50">
                  <span className="text-sm text-gray-800">{row.site}</span>
                  <span className="text-sm font-semibold text-blue-600">{row.clicks} clicks</span>
                </div>
              )) : (
                <p className="text-gray-400 text-sm text-center py-6">No click data yet</p>
              )}
            </div>
          </div>
        </div>
      </div>

      <ConfirmModal
        isOpen={showClearConfirm}
        title="Clear All Data"
        message="This will permanently delete ALL machines and ALL scrape job history from the database. This cannot be undone. Are you sure?"
        onConfirm={() => { clearMut.mutate(); setShowClearConfirm(false) }}
        onCancel={() => setShowClearConfirm(false)}
      />
    </AdminLayout>
  )
}
