import { useNavigate } from 'react-router-dom'
import { useFilters } from '../hooks/useSearch'
import SearchBar from '../components/SearchBar'
import { getSiteName } from '../utils/format'

const CATEGORIES = [
  { label: 'CNC Machines',      q: 'CNC' },
  { label: 'Lathes',            q: 'lathe' },
  { label: 'Milling Machines',  q: 'milling' },
  { label: 'Grinding Machines', q: 'grinding' },
  { label: 'Drilling Machines', q: 'drilling' },
  { label: 'Presses',           q: 'press' },
]

function StatCard({ icon, value, label }) {
  return (
    <div className="flex flex-col items-center text-center p-6 bg-white rounded-2xl shadow-sm border border-gray-100">
      <div className="text-3xl mb-2">{icon}</div>
      <div className="text-2xl font-bold text-gray-900">{value}</div>
      <div className="text-sm text-gray-500 mt-1">{label}</div>
    </div>
  )
}

export default function Home() {
  const navigate = useNavigate()
  const { data: filters } = useFilters()

  const totalMachines = filters?.total_machines
  const totalSites = filters?.sites?.length || 8

  const handleSearch = (q) => {
    if (q.trim()) navigate(`/results?q=${encodeURIComponent(q)}`)
    else navigate('/results')
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* Hero */}
      <div className="bg-gradient-to-br from-slate-900 via-slate-800 to-blue-950 flex-1 flex flex-col">
        {/* Navbar in hero */}
        <nav className="max-w-7xl mx-auto w-full px-4 sm:px-6 py-6 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <svg className="w-8 h-8 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            <span className="text-white font-bold text-xl">MachineSearch</span>
          </div>
        </nav>

        {/* Hero content */}
        <div className="flex-1 flex items-center justify-center px-4 sm:px-6 pb-20 pt-10">
          <div className="w-full max-w-2xl text-center">
            <h1 className="text-4xl sm:text-5xl font-extrabold text-white leading-tight mb-4">
              Find Industrial Machines<br className="hidden sm:block" /> Worldwide
            </h1>
            <p className="text-lg text-slate-300 mb-10">
              Search {totalMachines ? totalMachines.toLocaleString() : '4,700'}+ machines from verified suppliers
            </p>

            <SearchBar size="large" onSubmit={handleSearch} />

            {/* Categories */}
            <div className="flex flex-wrap justify-center gap-2 mt-8">
              {CATEGORIES.map(({ label, q }) => (
                <button
                  key={q}
                  onClick={() => navigate(`/results?q=${encodeURIComponent(q)}`)}
                  className="px-4 py-2 rounded-full bg-white/10 text-white text-sm hover:bg-white/20 transition-colors border border-white/20"
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Stats + sites section */}
      <div className="bg-gray-50 py-16 px-4 sm:px-6">
        <div className="max-w-5xl mx-auto">
          {/* Stats */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 mb-16">
            <StatCard
              icon="⚙️"
              value={totalMachines ? totalMachines.toLocaleString() : '4,700+'}
              label="Machines Listed"
            />
            <StatCard
              icon="🌐"
              value={`${totalSites} Suppliers`}
              label="Verified Sources"
            />
            <StatCard
              icon="🌍"
              value="20+ Countries"
              label="Global Coverage"
            />
          </div>

          {/* Source sites */}
          {filters?.sites && filters.sites.length > 0 && (
            <div>
              <h2 className="text-center text-xl font-bold text-gray-900 mb-8">Our Data Sources</h2>
              <div className="flex flex-wrap justify-center gap-3">
                {filters.sites.map(s => (
                  <button
                    key={s.site}
                    onClick={() => navigate(`/results?site_name=${s.site}`)}
                    className="px-4 py-2 bg-white rounded-xl border border-gray-200 shadow-sm hover:border-blue-300 hover:shadow-md transition-all text-sm font-medium text-gray-700"
                  >
                    {getSiteName(s.site)}
                    <span className="ml-2 text-xs text-gray-400">{s.count.toLocaleString()}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-100 py-6 text-center text-sm text-gray-400">
        © 2026 MachineSearch · Industrial Equipment Search Engine
      </footer>
    </div>
  )
}
