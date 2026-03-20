import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts'
import { getOverview, clearAllMachines } from '../api/adminClient'
import StatCard from '../components/StatCard'
import AdminLayout from '../components/AdminLayout'
import ConfirmModal from '../components/ConfirmModal'
import { useToast } from '../components/Toast'

export default function Dashboard() {
  const [showClearConfirm, setShowClearConfirm] = useState(false)
  const qc = useQueryClient()
  const toast = useToast()

  const clearMut = useMutation({
    mutationFn: clearAllMachines,
    onSuccess: (d) => {
      qc.invalidateQueries()
      toast(`Cleared ${d.machines_removed.toLocaleString()} machines from database`, 'success')
    },
    onError: e => toast(e.response?.data?.detail || 'Clear failed', 'error'),
  })

  const { data, isLoading, error } = useQuery({
    queryKey: ['overview'],
    queryFn: getOverview,
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
