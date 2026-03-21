import { useQuery } from '@tanstack/react-query'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts'
import { getOverview } from '../api/adminClient'
import StatCard from '../components/StatCard'
import AdminLayout from '../components/AdminLayout'

export default function Dashboard() {
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
    </AdminLayout>
  )
}
