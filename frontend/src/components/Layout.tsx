import { useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { useTheme } from '../hooks/useTheme'
import CVModal from './CVModal'

export default function Layout() {
  const { theme, toggle } = useTheme()
  const { pathname } = useLocation()
  const [showCV, setShowCV] = useState(false)

  return (
    <>
      <button className="theme-toggle" aria-label="切換深色/淺色模式" onClick={toggle}>
        <span className="theme-toggle__icon">{theme === 'light' ? '☀️' : '🌙'}</span>
      </button>

      <nav className="quick-nav">
        <NavLink to="/alerts" className="quick-nav__link" title="職缺提醒">
          🔔
        </NavLink>
        <NavLink to="/dashboard" className="quick-nav__link" title="投遞看板">
          📋
        </NavLink>
        {pathname === '/' && (
          <button
            className="quick-nav__link"
            title="設定履歷（AI 評分用）"
            onClick={() => setShowCV(true)}
          >
            👤
          </button>
        )}
      </nav>

      <div className="bg-glow bg-glow--1" />
      <div className="bg-glow bg-glow--2" />

      <Outlet />

      {showCV && <CVModal onClose={() => setShowCV(false)} />}
    </>
  )
}
