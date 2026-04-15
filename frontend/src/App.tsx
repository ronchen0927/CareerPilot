import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import AlertsPage from './pages/AlertsPage'
import CoverLetterDetailPage from './pages/CoverLetterDetailPage'
import CoverLetterHistoryPage from './pages/CoverLetterHistoryPage'
import CoverLetterPage from './pages/CoverLetterPage'
import DashboardPage from './pages/DashboardPage'
import EvaluatePage from './pages/EvaluatePage'
import HistoryDetailPage from './pages/HistoryDetailPage'
import HistoryPage from './pages/HistoryPage'
import SearchPage from './pages/SearchPage'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<SearchPage />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="alerts" element={<AlertsPage />} />
        <Route path="evaluate" element={<EvaluatePage />} />
        <Route path="history" element={<HistoryPage />} />
        <Route path="history/:id" element={<HistoryDetailPage />} />
        <Route path="cover-letter" element={<CoverLetterPage />} />
        <Route path="cover-letters" element={<CoverLetterHistoryPage />} />
        <Route path="cover-letters/:id" element={<CoverLetterDetailPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
