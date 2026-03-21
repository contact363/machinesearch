import { useState, useEffect } from 'react'
import { NavLink, useNavigate, useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getJobStatus } from '../api/adminClient'

const NAV = [
  {
    to: '/admin/dashboard',
    label: 'Dashboard',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
      </svg>
    ),
  },
  {
    to: '/admin/sites',
    label: 'Sites',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
      </svg>
    ),
  },
  {
    to: '/admin/jobs',
    label: 'Scraper Jobs',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
      </svg>
    ),
  },
  {
    to: '/admin/machines',
    label: 'Machines',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
    ),
  },
  {
    to: '/admin/analytics',
    label: 'Analytics',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
  },
]

const PAGE_TITLES = {
  '/admin/dashboard': 'Dashboard',
  '/admin/sites':     'Sites',
  '/admin/jobs':      'Scraper Jobs',
  '/admin/machines':  'Machines',
  '/admin/analytics': 'Analytics',
}

export default function AdminLayout({ children }) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const email = localStorage.getItem('admin_email') || 'admin'
  const initials = email.slice(0, 2).toUpperCase()
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
    navigate('/admin/login')
  }

  useEffect(() => { setSidebarOpen(false) }, [location.pathname])

  const SidebarContent = () => (
    <div className="flex flex-col h-full bg-gray-950">
      {/* Brand */}
      <div className="px-5 py-5">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-blue-600 flex items-center justify-center flex-shrink-0">
            <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
          <span className="text-white font-semibold text-[15px] tracking-tight">MachineSearch</span>
        </div>
      </div>

      <div className="mx-4 border-t border-white/5 mb-4" />

      {/* Nav */}
      <nav className="flex-1 px-3 space-y-0.5">
        {NAV.map(({ to, label, icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-[13.5px] font-medium transition-all ${
                isActive
                  ? 'bg-white/10 text-white'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-white/5'
              }`
            }
          >
            {icon}
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="mx-4 border-t border-white/5 mt-4" />
      <div className="px-3 py-4 space-y-1">
        <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg">
          <div className="w-7 h-7 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0">
            <span className="text-white text-xs font-semibold">{initials}</span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-gray-200 text-xs font-medium truncate">{email}</p>
            <p className="text-gray-500 text-[11px]">Administrator</p>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-[13.5px] font-medium text-gray-400 hover:text-gray-200 hover:bg-white/5 transition-all"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
          </svg>
          Sign out
        </button>
      </div>
    </div>
  )

  return (
    <div className="flex h-screen overflow-hidden" style={{ backgroundColor: '#f4f5f7' }}>
      {/* Desktop sidebar */}
      <aside className="hidden md:flex flex-col w-56 flex-shrink-0">
        <SidebarContent />
      </aside>

      {/* Mobile overlay */}
      {sidebarOpen && (
        <div className="md:hidden fixed inset-0 z-40 flex">
          <div className="w-56 flex flex-col">
            <SidebarContent />
          </div>
          <div className="flex-1 bg-black/60" onClick={() => setSidebarOpen(false)} />
        </div>
      )}

      {/* Main */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <header className="bg-white border-b border-gray-200 px-6 h-14 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-3">
            <button
              className="md:hidden text-gray-500 hover:text-gray-700"
              onClick={() => setSidebarOpen(true)}
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <h1 className="text-[15px] font-semibold text-gray-800">{pageTitle}</h1>
          </div>
          {runningCount > 0 && (
            <span className="flex items-center gap-1.5 bg-blue-50 text-blue-700 text-xs font-medium px-3 py-1.5 rounded-full border border-blue-100">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
              {runningCount} scrape{runningCount > 1 ? 's' : ''} running
            </span>
          )}
        </header>

        <main className="flex-1 overflow-auto p-6">
          {children}
        </main>
      </div>
    </div>
  )
}
