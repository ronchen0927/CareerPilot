import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { useTheme } from '../hooks/useTheme'
import CVModal from './CVModal'

export default function Layout() {
  const { theme, toggle } = useTheme()
  const [showCV, setShowCV] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)

  function closeSidebar() {
    setSidebarOpen(false)
  }

  return (
    <div className="app-shell">
      {/* Mobile overlay */}
      <div
        className={`sidebar-overlay${sidebarOpen ? ' is-open' : ''}`}
        onClick={closeSidebar}
      />

      {/* Sidebar */}
      <aside className={`sidebar${sidebarOpen ? ' is-open' : ''}`}>
        <div className="sidebar__brand">
          <span className="sidebar__brand-mark">CP</span>
          <span className="sidebar__brand-name">CareerPilot</span>
        </div>

        <nav className="sidebar__nav">
          <div className="sidebar__group">
            <span className="sidebar__group-label">求職</span>
            <NavLink to="/" end className="sidebar__link" onClick={closeSidebar}>
              搜尋職缺
            </NavLink>
            <NavLink to="/dashboard" className="sidebar__link" onClick={closeSidebar}>
              投遞看板
            </NavLink>
            <NavLink to="/alerts" className="sidebar__link" onClick={closeSidebar}>
              職缺提醒
            </NavLink>
            <NavLink to="/smart-match" className="sidebar__link" onClick={closeSidebar}>
              智慧推薦
            </NavLink>
          </div>

          <div className="sidebar__group">
            <span className="sidebar__group-label">AI 工具</span>
            <NavLink to="/evaluate" className="sidebar__link" onClick={closeSidebar}>
              AI 評分
            </NavLink>
            <NavLink to="/history" className="sidebar__link" onClick={closeSidebar}>
              評分歷史
            </NavLink>
            <NavLink to="/cover-letter" className="sidebar__link" onClick={closeSidebar}>
              AI 推薦信
            </NavLink>
            <NavLink to="/cover-letters" className="sidebar__link" onClick={closeSidebar}>
              推薦信歷史
            </NavLink>
            <NavLink to="/resume-rewrite" className="sidebar__link" onClick={closeSidebar}>
              AI 履歷改寫
            </NavLink>
            <NavLink to="/resume-rewrites" className="sidebar__link" onClick={closeSidebar}>
              改寫歷史
            </NavLink>
            <NavLink to="/knowledge-base" className="sidebar__link" onClick={closeSidebar}>
              個人知識庫 (RAG)
            </NavLink>
            <NavLink to="/interview-prep" className="sidebar__link" onClick={closeSidebar}>
              AI 面試與履歷比對
            </NavLink>
            <NavLink to="/resume-match-history" className="sidebar__link" onClick={closeSidebar}>
              履歷解析歷史
            </NavLink>
            <NavLink to="/mock-interviews" className="sidebar__link" onClick={closeSidebar}>
              模擬面試歷史
            </NavLink>
          </div>
        </nav>

        <div className="sidebar__footer">
          <NavLink to="/settings" className="sidebar__link" onClick={closeSidebar}>
            設定
          </NavLink>
          <div className="sidebar__actions">
            <button
              className="sidebar__cv-btn"
              onClick={() => { setShowCV(true); closeSidebar() }}
            >
              設定履歷
            </button>
            <button
              className="sidebar__theme-btn"
              aria-label="切換深色/淺色模式"
              onClick={toggle}
            >
              {theme === 'light' ? '☀' : '◑'}
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="app-main">
        <button
          className="menu-toggle"
          aria-label="開啟選單"
          onClick={() => setSidebarOpen(s => !s)}
        >
          <span />
          <span />
          <span />
        </button>
        <Outlet />
      </div>

      {showCV && <CVModal onClose={() => setShowCV(false)} />}
    </div>
  )
}
