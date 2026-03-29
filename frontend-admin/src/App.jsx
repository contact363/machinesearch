import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ToastProvider } from './components/Toast'

import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import SiteConfigs from './pages/SiteConfigs'
import ScraperJobs from './pages/ScraperJobs'
import Machines from './pages/Machines'
import MachineDetail from './pages/MachineDetail'
import Analytics from './pages/Analytics'

const qc = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 10_000 } },
})

function ProtectedRoute({ children }) {
  const token = localStorage.getItem('admin_token')
  if (!token) return <Navigate to="/login" replace />
  return children
}

export default function App() {
  return (
    <QueryClientProvider client={qc}>
      <ToastProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login"     element={<Login />} />
            <Route path="/"          element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
            <Route path="/sites"     element={<ProtectedRoute><SiteConfigs /></ProtectedRoute>} />
            <Route path="/jobs"      element={<ProtectedRoute><ScraperJobs /></ProtectedRoute>} />
            <Route path="/machines"  element={<ProtectedRoute><Machines /></ProtectedRoute>} />
            <Route path="/machines/:id" element={<ProtectedRoute><MachineDetail /></ProtectedRoute>} />
            <Route path="/analytics" element={<ProtectedRoute><Analytics /></ProtectedRoute>} />
          </Routes>
        </BrowserRouter>
      </ToastProvider>
    </QueryClientProvider>
  )
}
