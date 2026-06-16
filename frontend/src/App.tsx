import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import Layout from './components/layout/Layout'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import DashboardPage from './pages/DashboardPage'
import SyllabiListPage from './pages/SyllabiListPage'
import SyllabusDetailPage from './pages/SyllabusDetailPage'
import SyllabusFormPage from './pages/SyllabusFormPage'
import SubjectGridPage from './pages/SubjectGridPage'
import AdminPanelPage from './pages/AdminPanelPage'
import VersionHistoryPage from './pages/VersionHistoryPage'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((s) => s.user)
  const token = localStorage.getItem('access_token')
  if (!token && !user) return <Navigate to="/login" replace />
  return <>{children}</>
}

function RequireAdmin({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((s) => s.user)
  if (user && user.role !== 'admin') return <Navigate to="/" replace />
  return <>{children}</>
}

export default function App() {
  const fetchMe = useAuthStore((s) => s.fetchMe)

  useEffect(() => { fetchMe() }, [])

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/" element={<RequireAuth><Layout /></RequireAuth>}>
          <Route index element={<DashboardPage />} />
          <Route path="syllabi" element={<SyllabiListPage />} />
          <Route path="syllabi/new" element={<SyllabusFormPage />} />
          <Route path="syllabi/:id" element={<SyllabusDetailPage />} />
          <Route path="syllabi/:id/edit" element={<SyllabusFormPage />} />
          <Route path="syllabi/:id/history" element={<VersionHistoryPage />} />
          <Route path="grid" element={<SubjectGridPage />} />
          <Route path="admin" element={<RequireAdmin><AdminPanelPage /></RequireAdmin>} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
