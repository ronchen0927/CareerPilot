import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import AlertsPage from './pages/AlertsPage'
import DashboardPage from './pages/DashboardPage'
import SearchPage from './pages/SearchPage'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<SearchPage />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="alerts" element={<AlertsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
