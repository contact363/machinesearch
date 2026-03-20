import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useFilters } from '../hooks/useSearch'
import SearchBar from '../components/SearchBar'
import { getSiteName } from '../utils/format'
import { login } from '../admin/api/adminClient'

function LoginModal({ onClose }) {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const data = await login(email, password)
      localStorage.setItem('admin_token', data.access_token)
      localStorage.setItem('admin_email', data.email)
      onClose()
      navigate('/admin/dashboard')
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid email or password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4" onClick={onClose}>
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" />
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-sm p-8" onClick={e => e.stopPropagation()}>
        <button onClick={onClose} className="absolute top-4 right-4 text-gray-300 hover:text-gray-500 transition-colors">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-11 h-11 rounded-full bg-blue-50 mb-3">
            <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
          </div>
          <h2 className="text-lg font-bold text-gray-900">Admin Sign In</h2>
          <p className="text-sm text-gray-400 mt-0.5">MachineSearch dashboard</p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-3">
          <input type="email" value={email} onChange={e => setEmail(e.target.value)} required autoFocus
            placeholder="Email address"
            className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent" />
          <input type="password" value={password} onChange={e => setPassword(e.target.value)} required
            placeholder="Password"
            className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent" />
          {error && <p className="text-red-600 text-sm bg-red-50 rounded-lg px-3 py-2">{error}</p>}
          <button type="submit" disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white font-semibold rounded-xl py-2.5 transition-colors flex items-center justify-center gap-2 mt-1">
            {loading && <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />}
            {loading ? 'Signing in…' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  )
}

const CATEGORIES = [
  { label: 'CNC Machines', q: 'CNC' },
  { label: 'Lathes', q: 'lathe' },
  { label: 'Milling', q: 'milling' },
  { label: 'Grinding', q: 'grinding' },
  { label: 'Drilling', q: 'drilling' },
  { label: 'Presses', q: 'press' },
  { label: 'Turning', q: 'turning' },
  { label: 'Welding', q: 'welding' },
]

export default function Home() {
  const navigate = useNavigate()
  const { data: filters } = useFilters()
  const [showLogin, setShowLogin] = useState(false)
  const isLoggedIn = !!localStorage.getItem('admin_token')

  const totalMachines = filters?.total_machines
  const totalSites = filters?.sites?.length || 8

  const handleSearch = (q) => {
    if (q.trim()) navigate(`/results?q=${encodeURIComponent(q)}`)
    else navigate('/results')
  }

  return (
    <div className="min-h-screen bg-white flex flex-col">
      {/* Nav */}
      <header className="border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center flex-shrink-0">
              <svg className="w-4.5 h-4.5 text-white w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </div>
            <span className="font-bold text-gray-900 text-lg">MachineSearch</span>
          </Link>
          <div className="flex items-center gap-2">
            {isLoggedIn ? (
              <>
                <button onClick={() => navigate('/admin/dashboard')}
                  className="text-sm font-medium text-blue-600 hover:text-blue-700 px-3 py-2 rounded-lg hover:bg-blue-50 transition-colors">
                  Dashboard
                </button>
                <button onClick={() => { localStorage.removeItem('admin_token'); localStorage.removeItem('admin_email'); window.location.reload() }}
                  className="text-sm font-medium text-gray-500 hover:text-gray-700 px-3 py-2 rounded-lg hover:bg-gray-100 transition-colors">
                  Sign Out
                </button>
              </>
            ) : (
              <button onClick={() => setShowLogin(true)}
                className="text-sm font-semibold bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors">
                Sign In
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="bg-gradient-to-b from-slate-50 to-white border-b border-gray-100 py-20 px-4 sm:px-6">
        <div className="max-w-3xl mx-auto text-center">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 bg-blue-50 text-blue-700 text-xs font-semibold px-3 py-1.5 rounded-full mb-6">
            <span className="w-1.5 h-1.5 bg-blue-500 rounded-full" />
            {totalSites} verified industrial suppliers
          </div>

          <h1 className="text-4xl sm:text-5xl font-extrabold text-gray-900 leading-tight tracking-tight mb-4">
            Find Industrial Machines<br className="hidden sm:block" />
            <span className="text-blue-600"> Worldwide</span>
          </h1>
          <p className="text-lg text-gray-500 mb-10 max-w-xl mx-auto">
            Search {totalMachines ? totalMachines.toLocaleString() : '4,700'}+ machines from verified suppliers across 20+ countries
          </p>

          <SearchBar size="large" onSubmit={handleSearch} />

          {/* Category pills */}
          <div className="flex flex-wrap justify-center gap-2 mt-7">
            {CATEGORIES.map(({ label, q }) => (
              <button
                key={q}
                onClick={() => navigate(`/results?q=${encodeURIComponent(q)}`)}
                className="px-4 py-1.5 rounded-full bg-white border border-gray-200 text-gray-600 text-sm hover:border-blue-300 hover:text-blue-700 hover:bg-blue-50 transition-all shadow-sm"
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* Stats row */}
      <section className="py-14 px-4 sm:px-6 bg-white">
        <div className="max-w-5xl mx-auto">
          <div className="grid grid-cols-3 gap-6 mb-14">
            {[
              { value: totalMachines ? totalMachines.toLocaleString() : '4,700+', label: 'Machines Listed', icon: '⚙️' },
              { value: `${totalSites}`, label: 'Verified Suppliers', icon: '🏭' },
              { value: '20+', label: 'Countries', icon: '🌍' },
            ].map(({ value, label, icon }) => (
              <div key={label} className="text-center">
                <div className="text-2xl mb-1">{icon}</div>
                <div className="text-2xl sm:text-3xl font-bold text-gray-900">{value}</div>
                <div className="text-sm text-gray-400 mt-1">{label}</div>
              </div>
            ))}
          </div>

          {/* Source sites */}
          {filters?.sites && filters.sites.length > 0 && (
            <div>
              <p className="text-center text-xs font-semibold text-gray-400 uppercase tracking-widest mb-5">Data sources</p>
              <div className="flex flex-wrap justify-center gap-2">
                {filters.sites.map(s => (
                  <button
                    key={s.site}
                    onClick={() => navigate(`/results?site_name=${s.site}`)}
                    className="flex items-center gap-2 px-3.5 py-2 bg-white rounded-xl border border-gray-200 hover:border-blue-300 hover:shadow-sm transition-all text-sm font-medium text-gray-700"
                  >
                    <span>{getSiteName(s.site)}</span>
                    <span className="text-xs font-normal text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded-md">
                      {s.count.toLocaleString()}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </section>

      {/* How it works */}
      <section className="py-14 px-4 sm:px-6 bg-gray-50 border-t border-gray-100">
        <div className="max-w-4xl mx-auto">
          <p className="text-center text-xs font-semibold text-gray-400 uppercase tracking-widest mb-10">How it works</p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-8">
            {[
              { step: '01', title: 'Search', desc: 'Type what you need — machine name, brand, or type' },
              { step: '02', title: 'Filter', desc: 'Narrow by price, location, supplier, and more' },
              { step: '03', title: 'Connect', desc: 'Click through to the supplier to get a quote' },
            ].map(({ step, title, desc }) => (
              <div key={step} className="flex gap-4">
                <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-blue-600 text-white text-xs font-bold flex items-center justify-center">
                  {step}
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900 mb-1">{title}</h3>
                  <p className="text-sm text-gray-500">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-100 py-6 px-4 text-center text-sm text-gray-400">
        © 2026 MachineSearch · Industrial Equipment Search Engine
      </footer>

      {showLogin && <LoginModal onClose={() => setShowLogin(false)} />}
    </div>
  )
}
