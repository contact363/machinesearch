import { useState, useEffect } from 'react'
import { NavLink, useNavigate, useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getJobStatus } from '../api/adminClient'

const NAV = [
  { to: '/dashboard', label: 'Dashboard',    icon: '⊞' },
  { to: '/sites',     label: 'Sites',         icon: '🌐' },
  { to: '/jobs',      label: 'Scraper Jobs',  icon: '▶' },
  { to: '/machines',  label: 'Machines',      icon: '⚙' },
  { to: '/analytics', label: 'Analytics',     icon: '📊' },
]

const PAGE_TITLES = {
  '/dashboard': 'Dashboard',
  '/sites':     'Site Configurations',
  '/jobs':      'Scraper Jobs',
  '/machines':  'Machines',
  '/analytics': 'Analytics',
}

export default function AdminLayout({ children }) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const email = localStorage.getItem('admin_email') || 'admin'
  const pageTitle = PAGE_TITLES[location.pathname] || 'Admin'

  const { data: jobStatusData } = useQuery({
    queryKey: ['jobStatus'],
    queryFn: getJobStatus,
    refetchInterval: 10_000,
  })
  const runningCount = jobStatusData?.jobs?.filter(j => j.status === 'running').length || 0

  const handleLogout = () => {
    localStorage.removeItem('admin_token')
    localStorage.removeItem('admin_email')
    navigate('/login')
  }

  // Close sidebar on route change (mobile)
  useEffect(() => { setSidebarOpen(false) }, [location.pathname])

  const Sidebar = () => (
    <div className="flex flex-col h-full" style={{ backgroundColor: '#1e293b' }}>
      {/* Logo */}
      <div className="px-6 py-5 border-b border-slate-700">
        <div className="flex items-center gap-3">
          <span className="text-2xl">⚙</span>
          <span className="text-white text-lg font-semibold tracking-tight">MachineSearch</span>
        </div>
        <p className="text-slate-400 text-xs mt-1">Admin Panel</p>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV.map(({ to, label, icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                isActive
                  ? 'bg-blue-600 text-white font-medium'
                  : 'text-slate-300 hover:bg-slate-700 hover:text-white'
              }`
            }
          >
            <span className="text-base w-5 text-center">{icon}</span>
            {label}
          </NavLink>
        ))}
      </nav>

      {/* User + logout */}
      <div className="px-4 py-4 border-t border-slate-700">
        <p className="text-slate-400 text-xs truncate mb-2">{email}</p>
        <button
          onClick={handleLogout}
          className="w-full text-left px-3 py-2 rounded-lg text-sm text-slate-300 hover:bg-slate-700 hover:text-white transition-colors"
        >
          🚪 Logout
        </button>
      </div>
    </div>
  )

  return (
    <div className="flex h-screen overflow-hidden bg-slate-100">
      {/* Sidebar — desktop */}
      <aside className="hidden md:flex flex-col w-60 flex-shrink-0">
        <Sidebar />
      </aside>

      {/* Sidebar — mobile overlay */}
      {sidebarOpen && (
        <div className="md:hidden fixed inset-0 z-40 flex">
          <div className="w-60 flex flex-col" style={{ backgroundColor: '#1e293b' }}>
            <Sidebar />
          </div>
          <div className="flex-1 bg-black/50" onClick={() => setSidebarOpen(false)} />
        </div>
      )}

      {/* Main */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Topbar */}
        <header className="bg-white shadow-sm px-6 py-4 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-3">
            <button
              className="md:hidden text-gray-600 hover:text-gray-900"
              onClick={() => setSidebarOpen(true)}
            >
              ☰
            </button>
            <h1 className="text-lg font-semibold text-gray-800">{pageTitle}</h1>
          </div>
          {runningCount > 0 && (
            <span className="flex items-center gap-2 bg-orange-100 text-orange-700 text-xs font-medium px-3 py-1.5 rounded-full">
              <span className="w-2 h-2 rounded-full bg-orange-500 animate-pulse inline-block" />
              {runningCount} job{runningCount > 1 ? 's' : ''} running
            </span>
          )}
        </header>

        {/* Content */}
        <main className="flex-1 overflow-auto p-6">
          {children}
        </main>
      </div>
    </div>
  )
}
