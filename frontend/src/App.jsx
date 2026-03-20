import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

// Public pages
import Home from './pages/Home'
import Results from './pages/Results'
import MachineDetail from './pages/MachineDetail'

// Admin pages & components
import { ToastProvider } from './admin/components/Toast'
import AdminLogin from './admin/pages/Login'
import Dashboard from './admin/pages/Dashboard'
import SiteConfigs from './admin/pages/SiteConfigs'
import ScraperJobs from './admin/pages/ScraperJobs'
import Machines from './admin/pages/Machines'
import Analytics from './admin/pages/Analytics'

const qc = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 10_000 } },
})

function ProtectedRoute({ children }) {
  const token = localStorage.getItem('admin_token')
  if (!token) return <Navigate to="/admin/login" replace />
  return children
}

export default function App() {
  return (
    <QueryClientProvider client={qc}>
      <ToastProvider>
        <BrowserRouter>
          <Routes>
            {/* ── Public routes ── */}
            <Route path="/"             element={<Home />} />
            <Route path="/results"      element={<Results />} />
            <Route path="/machine/:id"  element={<MachineDetail />} />

            {/* ── Admin routes ── */}
            <Route path="/admin"           element={<Navigate to="/admin/dashboard" replace />} />
            <Route path="/admin/login"     element={<AdminLogin />} />
            <Route path="/admin/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
            <Route path="/admin/sites"     element={<ProtectedRoute><SiteConfigs /></ProtectedRoute>} />
            <Route path="/admin/jobs"      element={<ProtectedRoute><ScraperJobs /></ProtectedRoute>} />
            <Route path="/admin/machines"  element={<ProtectedRoute><Machines /></ProtectedRoute>} />
            <Route path="/admin/analytics" element={<ProtectedRoute><Analytics /></ProtectedRoute>} />

            {/* Catch-all */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </ToastProvider>
    </QueryClientProvider>
  )
}
